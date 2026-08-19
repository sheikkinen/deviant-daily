"""Tests: publish_step ordering — rotation persist BEFORE any DA side
effect (AC-08), committed transitions around submit/publish (AC-12),
RECOVERY_REQUIRED on post-publish commit failure (R-3)."""

import json
from types import SimpleNamespace

import pytest

from tools import steps
from tools.da_api import TokenPersistError
from tools.ledger import LedgerCommitError, RecoveryRequired

POST = {
    "title": "T",
    "paragraphs": ["p1", "p2"],
    "quote": None,
    "tags": ["aiart"],
    "confidence": "high",
    "mature": False,
    "mature_level": None,
    "mature_classification": [],
}


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class Recorder:
    """Session + runner recording global side-effect order."""

    def __init__(self, fail_gh=False, fail_git_on_call=None):
        self.order = []
        self.fail_gh = fail_gh
        self.fail_git_on_call = fail_git_on_call
        self.git_transitions = 0

    def post(self, url, **kwargs):
        name = url.rsplit("/", 1)[-1]
        self.order.append(f"http:{name}")
        bodies = {
            "token": {"access_token": "AT", "refresh_token": "NEW"},
            "placebo": {"status": "success"},
            "submit": {"status": "success", "itemid": 7},
            "publish": {"status": "success", "url": "https://da/dev"},
        }
        return FakeResponse(200, bodies[name])

    def run(self, cmd, **kwargs):
        joined = " ".join(cmd)
        if cmd[0] == "gh":
            self.order.append("gh:secret-set")
            return SimpleNamespace(returncode=1 if self.fail_gh else 0,
                                   stderr="", stdout="")
        if "git commit" in joined:
            self.git_transitions += 1
            self.order.append(f"git:commit-{self.git_transitions}")
            if self.fail_git_on_call == self.git_transitions:
                return SimpleNamespace(returncode=1, stderr="boom", stdout="")
        return SimpleNamespace(returncode=0, stderr="", stdout="")


@pytest.fixture
def env(monkeypatch, tmp_path):
    for k in ("DA_CLIENT_ID", "DA_CLIENT_SECRET", "DA_REFRESH_TOKEN", "GH_PAT"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(steps, "REPO_DIR", tmp_path)
    monkeypatch.setattr(steps, "LEDGER", tmp_path / "state" / "published.jsonl")
    (tmp_path / "state").mkdir()
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    return tmp_path, str(img)


def test_persist_before_any_da_side_effect(env):
    _tmp_path, img = env
    rec = Recorder()
    steps.publish_step(POST, img, "2026-08-19", "prompt", "s1", "z-image",
                       runner=rec.run, session=rec)
    o = rec.order
    assert o.index("gh:secret-set") < o.index("http:submit")
    assert o.index("gh:secret-set") < o.index("http:publish")
    # submitted transition committed BEFORE submit call
    assert o.index("git:commit-1") < o.index("http:submit")
    # published transition committed after publish
    assert o.index("http:publish") < o.index("git:commit-2")


def test_persist_failure_aborts_before_submit(env):
    _tmp_path, img = env
    rec = Recorder(fail_gh=True)
    with pytest.raises(TokenPersistError):
        steps.publish_step(POST, img, "2026-08-19", "p", "s1", "m",
                           runner=rec.run, session=rec)
    assert not any(x in rec.order for x in ("http:submit", "http:publish"))


def test_submitted_commit_failure_blocks_submit(env):
    _tmp_path, img = env
    rec = Recorder(fail_git_on_call=1)
    with pytest.raises(LedgerCommitError):
        steps.publish_step(POST, img, "2026-08-19", "p", "s1", "m",
                           runner=rec.run, session=rec)
    assert "http:submit" not in rec.order


def test_post_publish_commit_failure_is_recovery_required(env):
    _tmp_path, img = env
    rec = Recorder(fail_git_on_call=2)
    with pytest.raises(RecoveryRequired) as exc:
        steps.publish_step(POST, img, "2026-08-19", "p", "s1", "m",
                           runner=rec.run, session=rec)
    assert "itemid=7" in str(exc.value)
    assert "https://da/dev" in str(exc.value)


def test_publish_writes_post_md_without_image(env):
    tmp_path, img = env
    rec = Recorder()
    result = steps.publish_step(POST, img, "2026-08-19", "the prompt", "s1",
                                "z-image", runner=rec.run, session=rec)
    assert result["url"] == "https://da/dev"
    md = (tmp_path / "posts" / "2026-08-19.md").read_text()
    assert md.startswith("# T")
    assert "the prompt" in md
    assert not list((tmp_path / "posts").glob("*.png"))


def test_gate_skip_committed_before_green(env, monkeypatch):
    tmp_path, _ = env
    rec = Recorder()
    result = steps.gate_step({**POST, "confidence": "low"}, "2026-08-19",
                             "p", "s1", runner=rec.run)
    assert result["publish"] is False
    ledger = (tmp_path / "state" / "published.jsonl").read_text()
    entry = json.loads(ledger.splitlines()[-1])
    assert entry["status"] == "skipped"
    assert "confidence" in entry["reason"]
    assert rec.git_transitions == 1
