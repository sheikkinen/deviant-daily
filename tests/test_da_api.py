"""Tests: DA API request construction vs FR-822 recorded shapes (AC-11)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import tools.da_api as da


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_refresh_returns_rotated_token():
    s = FakeSession(
        [
            FakeResponse(
                200,
                {"access_token": "AT", "refresh_token": "NEW_RT", "expires_in": 3600},
            )
        ]
    )
    tok = da.refresh_token("cid", "sec", "OLD_RT", session=s)
    assert tok["refresh_token"] == "NEW_RT"
    url, kw = s.calls[0]
    assert url == da.TOKEN_URL
    assert kw["data"]["refresh_token"] == "OLD_RT"
    assert kw["headers"]["User-Agent"]  # UA mandatory


def test_refresh_failure_raises():
    s = FakeSession([FakeResponse(401, {"error": "invalid_grant"})])
    with pytest.raises(da.DAApiError):
        da.refresh_token("cid", "sec", "RT", session=s)


def test_429_backoff_then_success(monkeypatch):
    monkeypatch.setattr(da.time, "sleep", lambda s: None)
    s = FakeSession(
        [FakeResponse(429), FakeResponse(429), FakeResponse(200, {"status": "success"})]
    )
    da.placebo("AT", session=s)
    assert len(s.calls) == 3


def test_429_exhaustion_raises(monkeypatch):
    monkeypatch.setattr(da.time, "sleep", lambda s: None)
    s = FakeSession([FakeResponse(429)] * da.MAX_RETRIES)
    with pytest.raises(da.DAApiError):
        da.placebo("AT", session=s)


def test_submit_shape(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    s = FakeSession([FakeResponse(200, {"status": "success", "itemid": 42})])
    itemid = da.stash_submit(
        "AT", img, "Title", "c1\n\nc2", ["gothic", "aiart"], session=s
    )
    assert itemid == 42
    url, kw = s.calls[0]
    assert url.endswith("/stash/submit")
    data = dict(kw["data"])
    assert data["is_ai_generated"] == "true"
    assert data["noai"] == "true"
    assert data["tags[0]"] == "gothic"
    assert data["tags[1]"] == "aiart"
    assert "file" in kw["files"]
    assert kw["headers"]["Authorization"] == "Bearer AT"


def test_publish_shape_non_mature():
    s = FakeSession([FakeResponse(200, {"status": "success", "url": "https://da/x"})])
    result = da.stash_publish("AT", 42, mature=False, session=s)
    assert result["url"] == "https://da/x"
    data = dict(s.calls[0][1]["data"])
    assert data["is_mature"] == "false"
    assert data["is_ai_generated"] == "true"  # both AI flags on publish too
    assert data["noai"] == "true"
    assert "mature_level" not in data


def test_publish_shape_mature():
    s = FakeSession([FakeResponse(200, {"status": "success", "url": "u"})])
    da.stash_publish(
        "AT",
        42,
        mature=True,
        mature_level="moderate",
        mature_classification=["nudity", "sexual"],
        session=s,
    )
    _url, kw = s.calls[0]
    data = kw["data"]
    assert ("is_mature", "true") in data
    assert ("mature_level", "moderate") in data
    assert ("mature_classification[]", "nudity") in data
    assert ("mature_classification[]", "sexual") in data


def test_error_code_9_idempotent():
    s = FakeSession([FakeResponse(400, {"error_code": 9, "url": "u"})])
    result = da.stash_publish("AT", 42, mature=False, session=s)
    assert result["already_published"] is True


def test_other_error_raises():
    s = FakeSession([FakeResponse(400, {"error_code": 1, "error": "tos"})])
    with pytest.raises(da.DAApiError):
        da.stash_publish("AT", 42, mature=False, session=s)


def test_persist_secret_via_stdin():
    runner = MagicMock(return_value=SimpleNamespace(returncode=0))
    da.persist_refresh_secret("NEW_RT", "o/r", "PAT", runner=runner)
    args, kwargs = runner.call_args
    assert args[0][:3] == ["gh", "secret", "set"]
    assert kwargs["input"] == "NEW_RT"
    assert "NEW_RT" not in " ".join(args[0])  # never on argv
    assert kwargs["env"]["GH_TOKEN"] == "PAT"


def test_persist_secret_failure_raises():
    runner = MagicMock(return_value=SimpleNamespace(returncode=1))
    with pytest.raises(da.TokenPersistError):
        da.persist_refresh_secret("RT", "o/r", "PAT", runner=runner)
