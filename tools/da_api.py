"""DeviantArt API client (FR-826 step 5; contracts frozen by FR-822).

refresh (rotates!) -> persist secret -> placebo -> stash/submit ->
stash/publish. UA header mandatory, timeouts everywhere, 429
exponential backoff, error_code 9 = already published = idempotent
success. Both AI flags (`is_ai_generated`, `noai`) on BOTH submit and
publish calls.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

TOKEN_URL = "https://www.deviantart.com/oauth2/token"
API = "https://www.deviantart.com/api/v1/oauth2"
UA = {"User-Agent": "deviant-daily/1.0 (+https://github.com/sheikkinen/deviant-daily)"}
TIMEOUT = 180
MAX_RETRIES = 4
ERROR_ALREADY_PUBLISHED = 9


class TokenPersistError(RuntimeError):
    """Rotated refresh token could not be persisted — abort before publish."""


class DAApiError(RuntimeError):
    pass


def _post(url: str, *, headers: dict, session=requests, **kwargs) -> requests.Response:
    """POST with 429 exponential backoff."""
    delay = 2.0
    for attempt in range(MAX_RETRIES):
        r = session.post(url, headers=headers, timeout=TIMEOUT, **kwargs)
        if r.status_code != 429:
            return r
        logger.warning("429 from %s, backoff %.0fs (attempt %d)", url, delay, attempt)
        time.sleep(delay)
        delay *= 2
    raise DAApiError(f"still 429 after {MAX_RETRIES} attempts: {url}")


def refresh_token(
    client_id: str, client_secret: str, refresh: str, session=requests
) -> dict:
    """Exchange refresh token; returns dict incl. NEW rotated refresh_token."""
    r = _post(
        TOKEN_URL,
        headers=UA,
        session=session,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
        },
    )
    if r.status_code != 200:
        raise DAApiError(f"token refresh failed: HTTP {r.status_code}")
    return r.json()


def persist_refresh_secret(
    new_refresh: str, repo: str, gh_pat: str, runner=subprocess.run
) -> None:
    """Write rotated token back to the repo secret via gh (GH_PAT).

    MUST succeed before any publish side effect (persist-before-publish,
    FR-826 rotation contract). Token passed via stdin, never argv/env dump.
    """
    result = runner(
        ["gh", "secret", "set", "DA_REFRESH_TOKEN", "--repo", repo],
        input=new_refresh,
        text=True,
        capture_output=True,
        env={"GH_TOKEN": gh_pat, "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    if result.returncode != 0:
        raise TokenPersistError(
            "gh secret set DA_REFRESH_TOKEN failed — aborting before publish"
        )


def placebo(access_token: str, session=requests) -> None:
    headers = {**UA, "Authorization": f"Bearer {access_token}"}
    r = _post(f"{API}/placebo", headers=headers, session=session)
    if r.status_code != 200 or r.json().get("status") != "success":
        raise DAApiError(f"placebo failed: HTTP {r.status_code}")


def stash_submit(
    access_token: str,
    image_path: str | Path,
    title: str,
    artist_comments: str,
    tags: list[str],
    session=requests,
) -> int:
    """Upload to sta.sh; returns itemid. Both AI flags set."""
    headers = {**UA, "Authorization": f"Bearer {access_token}"}
    data = [
        ("title", title),
        ("artist_comments", artist_comments),
        ("is_ai_generated", "true"),
        ("noai", "true"),
    ] + [(f"tags[{i}]", t) for i, t in enumerate(tags)]
    from tools.vision import detect_media_type

    media_type = detect_media_type(Path(image_path).read_bytes()[:16])
    with open(image_path, "rb") as f:
        r = _post(
            f"{API}/stash/submit",
            headers=headers,
            session=session,
            data=data,
            files={"file": (Path(image_path).name, f, media_type)},
        )
    body = r.json()
    if r.status_code != 200 or "itemid" not in body:
        raise DAApiError(f"stash/submit failed: HTTP {r.status_code} {body}")
    return body["itemid"]


def stash_publish(
    access_token: str,
    itemid: int,
    mature: bool,
    mature_level: str | None = None,
    mature_classification: list[str] | None = None,
    session=requests,
) -> dict:
    """Publish stash item; returns {url, ...}. error_code 9 = idempotent OK."""
    headers = {**UA, "Authorization": f"Bearer {access_token}"}
    data: list[tuple[str, str]] = [
        ("itemid", str(itemid)),
        ("is_mature", "true" if mature else "false"),
        ("is_ai_generated", "true"),
        ("noai", "true"),
    ]
    if mature:
        data.append(("mature_level", mature_level or ""))
        for c in mature_classification or []:
            data.append(("mature_classification[]", c))
    r = _post(f"{API}/stash/publish", headers=headers, session=session, data=data)
    body = r.json()
    if r.status_code == 200 and body.get("status") == "success":
        return body
    if body.get("error_code") == ERROR_ALREADY_PUBLISHED:
        logger.info("stash/publish: error_code 9 — already published, idempotent OK")
        return {"status": "success", "already_published": True, "url": body.get("url")}
    raise DAApiError(f"stash/publish failed: HTTP {r.status_code} {body}")
