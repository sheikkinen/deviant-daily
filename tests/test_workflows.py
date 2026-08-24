"""Tests: workflow shape (FR-862 AC-02, AC-03, AC-04).

The shared concurrency group is load-bearing: two overlapping runs both
call refresh_token, DA rotates on every refresh, and the second run
authenticates with an already-invalidated token while the secret write
races. Drift between the two callers is therefore a test failure, not a
review note.
"""

from pathlib import Path

import pytest
import yaml

from tools.roster import ACTIVE_MODELS

WF = Path(__file__).parent.parent / ".github" / "workflows"
PIPELINE = "./.github/workflows/_pipeline.yml"


def load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text())


def triggers(wf: dict) -> dict:
    """YAML 1.1 parses a bare `on:` key as the boolean True."""
    return wf.get("on", wf.get(True))


@pytest.mark.parametrize("name", ["_pipeline.yml", "daily.yml", "publish-now.yml"])
def test_workflow_exists(name):
    assert (WF / name).is_file()


def test_both_callers_share_one_concurrency_group():
    daily, now = load("daily.yml"), load("publish-now.yml")
    assert (
        daily["concurrency"]["group"] == now["concurrency"]["group"] == "daily-publish"
    )
    assert daily["concurrency"]["cancel-in-progress"] is False
    assert now["concurrency"]["cancel-in-progress"] is False


def test_both_callers_use_the_reusable_body():
    for name in ("daily.yml", "publish-now.yml"):
        jobs = load(name)["jobs"]
        assert [j["uses"] for j in jobs.values()] == [PIPELINE]


def test_pipeline_is_callable_only():
    assert "workflow_call" in triggers(load("_pipeline.yml"))


def test_daily_keeps_the_schedule():
    on = triggers(load("daily.yml"))
    assert on["schedule"] == [{"cron": "0 7 * * *"}]


def test_daily_passes_no_overrides():
    """AC-04: the scheduled path stays what it was."""
    job = next(iter(load("daily.yml")["jobs"].values()))
    assert not job.get("with"), "cron must not pin model/force/dry_run/date"


def test_publish_now_input_shape():
    inputs = triggers(load("publish-now.yml"))["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"model", "date"}, "no guard flags — running it publishes"
    assert inputs["date"]["type"] == "string" and inputs["date"]["default"] == ""
    assert inputs["model"]["type"] == "choice"
    assert inputs["model"]["default"] == "random"
    assert inputs["model"]["options"] == ["random", *sorted(ACTIVE_MODELS)]


def test_callers_declare_the_write_ceiling():
    """A called workflow cannot escalate beyond its caller (startup_failure)."""
    for name in ("daily.yml", "publish-now.yml"):
        assert load(name)["permissions"]["contents"] == "write"


def test_no_guard_flags_survive_anywhere():
    """dry_run/force were paternalistic ceremony — they must not creep back."""
    for name in ("_pipeline.yml", "daily.yml", "publish-now.yml"):
        text = (WF / name).read_text()
        assert "dry_run" not in text and "force" not in text


def test_secrets_are_not_inlined_in_the_callers():
    for name in ("daily.yml", "publish-now.yml"):
        assert "secrets." not in (WF / name).read_text()
