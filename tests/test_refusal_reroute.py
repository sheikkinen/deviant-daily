"""Tests: FR-891 refusal re-routing and honoured operator pin.

The seam is the resume path discarding live inputs: accumulated refusal
evidence (generate) and the operator's dispatch choice (draw). Every
test here is offline — the provider and git runner are stubs.
"""

import json
from types import SimpleNamespace

import pytest

from tools import steps
from tools.failures import prompt_sha
from tools.ledger import LedgerCommitError
from tools.roster import validate_roster

CORPUS_ROWS = [
    {
        "prompt": "a calm forest",
        "source_file": "001",
        "content": {"sexual": "safe", "gore": "safe"},
    },
    {
        "prompt": "a spicy scene",
        "source_file": "002",
        "content": {"sexual": "mature", "gore": "safe"},
    },
]
SPICY_PROMPT = CORPUS_ROWS[1]["prompt"]


class Runner:
    """Records git side effects; can fail the Nth commit."""

    def __init__(self, fail_commit_on=None):
        self.commits = []
        self.fail_commit_on = fail_commit_on

    def __call__(self, cmd, **kwargs):
        if cmd[:2] == ["git", "commit"]:
            self.commits.append(cmd[-1])
            if self.fail_commit_on == len(self.commits):
                return SimpleNamespace(returncode=1, stderr="boom", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")


class Provider:
    """Stub generate_image: named models refuse, the rest succeed."""

    def __init__(self, refusing, order):
        self.refusing = set(refusing)
        self.order = order

    def __call__(self, prompt, config, output_path):
        name = config["slug"]
        self.order.append(f"generate:{name}")
        if name in self.refusing:
            raise RuntimeError("The input or output was flagged as sensitive. (E005)")
        return str(output_path)


def _refusal(model, prompt):
    return {"model": model, "prompt_sha": prompt_sha(prompt), "error_class": "refusal"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "LEDGER", tmp_path / "state" / "published.jsonl")
    monkeypatch.setattr(steps, "FAILURES", tmp_path / "state" / "failures.jsonl")
    monkeypatch.setattr(steps, "CORPUS", tmp_path / "corpus.jsonl")
    (tmp_path / "state").mkdir()
    (tmp_path / "corpus.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in CORPUS_ROWS)
    )
    return tmp_path


def _rows(tmp_path, name):
    p = tmp_path / "state" / name
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def _ledger(tmp_path):
    return _rows(tmp_path, "published.jsonl")


def _failures(tmp_path):
    return _rows(tmp_path, "failures.jsonl")


def _seed_drawn(tmp_path, model, status="drawn"):
    (tmp_path / "state" / "published.jsonl").write_text(
        json.dumps(
            {
                "date": "2026-09-08",
                "slot": 0,
                "status": status,
                "prompt": SPICY_PROMPT,
                "source_file": "002",
                "model": model,
            }
        )
        + "\n"
    )


def _slugs():
    return {name: cfg["slug"] for name, cfg in validate_roster().items()}


def _names():
    return sorted(_slugs())


def _generate(tmp_path, model, runner, **kw):
    return steps.generate_step(
        SPICY_PROMPT,
        "2026-09-08",
        model=model,
        source_file="002",
        slot=0,
        runner=runner,
        out_path=str(tmp_path / "img.png"),
        **kw,
    )


# --- AC-01 / AC-05 -----------------------------------------------------


@pytest.mark.req("REQ-DD-118")
def test_refusal_reroutes_to_next_eligible_model(env, monkeypatch):
    """AC-01/AC-05: the refused binding is abandoned mid-run; the returned
    model_name is the model that actually produced the image."""
    tmp_path = env
    slugs, names = _slugs(), _names()
    first, second = names[0], names[1]
    _seed_drawn(tmp_path, first)
    order = []
    monkeypatch.setattr(steps, "generate_image", Provider([slugs[first]], order))

    result = _generate(tmp_path, first, Runner())

    assert result["model_name"] == second
    assert order == [f"generate:{slugs[first]}", f"generate:{slugs[second]}"]
    assert len(_failures(tmp_path)) == 1


@pytest.mark.req("REQ-DD-121")
def test_transport_failure_does_not_reroute(env, monkeypatch):
    """AC-01: only refusals are content evidence; a blip stays resumable."""
    tmp_path = env
    slugs = _slugs()
    first = _names()[0]
    _seed_drawn(tmp_path, first)
    order = []

    def boom(prompt, config, output_path):
        order.append(f"generate:{config['slug']}")
        raise ConnectionError("connection reset")

    monkeypatch.setattr(steps, "generate_image", boom)
    with pytest.raises(ConnectionError):
        _generate(tmp_path, first, Runner())

    assert order == [f"generate:{slugs[first]}"]
    assert [r["error_class"] for r in _failures(tmp_path)] == ["transport"]
    assert [r["status"] for r in _ledger(tmp_path)] == ["drawn"]


@pytest.mark.req("REQ-DD-121")
def test_user_path_refusal_does_not_reroute(env, monkeypatch):
    """AC-12: FR-889 keeps its contract — the operator is the authority."""
    tmp_path = env
    slugs = _slugs()
    first = _names()[0]
    order = []
    monkeypatch.setattr(steps, "generate_image", Provider([slugs[first]], order))

    with pytest.raises(RuntimeError):
        steps.generate_step(
            SPICY_PROMPT,
            "2026-09-08",
            model=first,
            run_source="user",
            runner=Runner(),
            out_path=str(tmp_path / "img.png"),
        )

    assert order == [f"generate:{slugs[first]}"]
    assert _ledger(tmp_path) == []


# --- AC-02 -------------------------------------------------------------


@pytest.mark.req("REQ-DD-119")
def test_failure_ledger_commit_failure_blocks_reroute(env, monkeypatch):
    """AC-02: FR-887 two-error semantics precede any retry."""
    tmp_path = env
    slugs = _slugs()
    first = _names()[0]
    _seed_drawn(tmp_path, first)
    order = []
    monkeypatch.setattr(steps, "generate_image", Provider([slugs[first]], order))

    with pytest.raises(RuntimeError) as exc:
        _generate(tmp_path, first, Runner(fail_commit_on=1))

    assert "flagged as sensitive" in str(exc.value)
    assert isinstance(exc.value.__cause__, LedgerCommitError)
    assert order == [f"generate:{slugs[first]}"]


# --- AC-03 -------------------------------------------------------------


@pytest.mark.req("REQ-DD-118")
def test_reroute_skips_models_with_prior_and_fresh_evidence(env, monkeypatch):
    """AC-03: evidence loaded after the commit; prior rows exclude too."""
    tmp_path = env
    slugs, names = _slugs(), _names()
    first, skipped, expected = names[0], names[1], names[2]
    _seed_drawn(tmp_path, first)
    (tmp_path / "state" / "failures.jsonl").write_text(
        json.dumps(_refusal(skipped, SPICY_PROMPT)) + "\n"
    )
    order = []
    monkeypatch.setattr(steps, "generate_image", Provider([slugs[first]], order))

    result = _generate(tmp_path, first, Runner())

    assert result["model_name"] == expected
    assert f"generate:{slugs[skipped]}" not in order


@pytest.mark.req("REQ-DD-118")
def test_reroute_is_deterministic_without_rng(env, monkeypatch):
    """AC-03: eligible_models is sorted; route()'s RNG is not consulted."""
    tmp_path = env
    slugs, names = _slugs(), _names()
    picks = set()
    for _ in range(4):
        _seed_drawn(tmp_path, names[0])
        (tmp_path / "state" / "failures.jsonl").unlink(missing_ok=True)
        monkeypatch.setattr(steps, "generate_image", Provider([slugs[names[0]]], []))
        picks.add(_generate(tmp_path, names[0], Runner())["model_name"])
    assert picks == {names[1]}


# --- AC-04 -------------------------------------------------------------


@pytest.mark.req("REQ-DD-120")
def test_retry_binding_committed_before_retry_call(env, monkeypatch):
    """AC-04: no provider call behind an uncommitted binding (R-3)."""
    tmp_path = env
    slugs, names = _slugs(), _names()
    first, second = names[0], names[1]
    _seed_drawn(tmp_path, first)
    order = []

    class OrderedRunner(Runner):
        def __call__(self, cmd, **kwargs):
            if cmd[:2] == ["git", "commit"]:
                order.append(f"commit:{cmd[-1]}")
            return super().__call__(cmd, **kwargs)

    monkeypatch.setattr(steps, "generate_image", Provider([slugs[first]], order))
    _generate(tmp_path, first, OrderedRunner())

    ledger_commits = [i for i, e in enumerate(order) if e.startswith("commit:ledger")]
    retry_call = order.index(f"generate:{slugs[second]}")
    assert ledger_commits and max(ledger_commits) < retry_call

    rebound = [r for r in _ledger(tmp_path) if r["status"] == "drawn"]
    assert [r["model"] for r in rebound] == [first, second]
    assert {r["prompt"] for r in rebound} == {SPICY_PROMPT}
    assert {r["source_file"] for r in rebound} == {"002"}
    assert {r["slot"] for r in rebound} == {0}


@pytest.mark.req("REQ-DD-120")
def test_retry_binding_commit_failure_aborts_before_call(env, monkeypatch):
    """AC-04: a failed binding commit stops the run before the retry."""
    tmp_path = env
    slugs, names = _slugs(), _names()
    first, second = names[0], names[1]
    _seed_drawn(tmp_path, first)
    order = []
    monkeypatch.setattr(steps, "generate_image", Provider([slugs[first]], order))

    with pytest.raises(LedgerCommitError):
        _generate(tmp_path, first, Runner(fail_commit_on=2))

    assert f"generate:{slugs[second]}" not in order


# --- AC-06 / AC-07 -----------------------------------------------------


@pytest.mark.req("REQ-DD-122")
def test_exhaustion_terminalizes_slot_and_stays_red(env, monkeypatch):
    """AC-06: every model refuses -> skipped + red; next run draws fresh."""
    tmp_path = env
    slugs = _slugs()
    first = _names()[0]
    _seed_drawn(tmp_path, first)
    order = []
    monkeypatch.setattr(steps, "generate_image", Provider(set(slugs.values()), order))

    with pytest.raises(RuntimeError):
        _generate(tmp_path, first, Runner())

    assert len(order) == len(slugs)
    last = _ledger(tmp_path)[-1]
    assert last["status"] == "skipped"
    assert last["reason"] == "unroutable: every roster model refused"
    assert (last["date"], last["slot"], last["source_file"]) == (
        "2026-09-08",
        0,
        "002",
    )

    monkeypatch.setattr(steps, "generate_image", Provider([], []))
    drawn = steps.draw_step(date="2026-09-08", runner=Runner())
    assert drawn["resumed"] is False
    assert drawn["slot"] == 1
    assert drawn["source_file"] != "002"


@pytest.mark.req("REQ-DD-122")
def test_exhaustion_commit_failure_does_not_claim_terminal(env, monkeypatch):
    """AC-07: the skip is never reported as durable. record_transition
    appends before it commits, so the local row proves nothing — the
    witness is that the commit failure propagates and carries the
    provider refusal as its context."""
    tmp_path = env
    slugs = _slugs()
    first = _names()[0]
    _seed_drawn(tmp_path, first)
    monkeypatch.setattr(steps, "generate_image", Provider(set(slugs.values()), []))

    runner = Runner(fail_commit_on=2 * len(slugs))
    with pytest.raises(LedgerCommitError) as exc:
        _generate(tmp_path, first, runner)

    assert "skipped" in runner.commits[-1]
    assert isinstance(exc.value.__context__, RuntimeError)
    assert "flagged as sensitive" in str(exc.value.__context__)


# --- AC-08 / AC-09 -----------------------------------------------------


@pytest.mark.req("REQ-DD-123")
def test_pin_rebinds_a_resumed_drawn_slot(env):
    """AC-08: the manual lever works on a poisoned slot."""
    tmp_path = env
    names = _names()
    _seed_drawn(tmp_path, names[0])

    out = steps.draw_step(date="2026-09-08", model=names[1], runner=Runner())

    assert out["resumed"] is True
    assert out["model"] == names[1]
    assert out["prompt"] == SPICY_PROMPT
    assert out["slot"] == 0
    rows = _ledger(tmp_path)
    assert rows[-1]["status"] == "drawn"
    assert rows[-1]["model"] == names[1]
    assert rows[-1]["source_file"] == "002"


@pytest.mark.req("REQ-DD-123")
def test_matching_pin_on_resume_writes_no_transition(env):
    """AC-08: re-binding to the same model is not a transition."""
    tmp_path = env
    names = _names()
    _seed_drawn(tmp_path, names[0])

    out = steps.draw_step(date="2026-09-08", model=names[0], runner=Runner())

    assert out["model"] == names[0]
    assert len(_ledger(tmp_path)) == 1


@pytest.mark.req("REQ-DD-123")
def test_pin_after_side_effect_boundary_raises(env):
    """AC-09: never re-bind past a transition guarding a DA call."""
    tmp_path = env
    names = _names()
    _seed_drawn(tmp_path, names[0], status="submitted")

    with pytest.raises(steps.UnsafeRebind) as exc:
        steps.draw_step(date="2026-09-08", model=names[1], runner=Runner())

    assert "submitted" in str(exc.value)
    assert names[0] in str(exc.value) and names[1] in str(exc.value)
    assert len(_ledger(tmp_path)) == 1


# --- AC-10 -------------------------------------------------------------


@pytest.mark.req("REQ-DD-118")
def test_replay_of_2026_09_08_escapes_the_loop(env, monkeypatch):
    """AC-10: the witnessed incident, offline. grok refuses five times in
    the committed evidence; the run must still produce an image."""
    tmp_path = env
    slugs = _slugs()
    _seed_drawn(tmp_path, "grok")
    (tmp_path / "state" / "failures.jsonl").write_text(
        "".join(json.dumps(_refusal("grok", SPICY_PROMPT)) + "\n" for _ in range(5))
    )
    order = []
    monkeypatch.setattr(steps, "generate_image", Provider([slugs["grok"]], order))

    result = _generate(tmp_path, "grok", Runner())

    assert result["model_name"] != "grok"
    assert result["image_path"]
    assert order.count(f"generate:{slugs['grok']}") == 1
