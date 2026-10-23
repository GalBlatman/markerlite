"""User-requested release check. Importing this module makes no request."""

from __future__ import annotations

import http.client
import json
import re
from dataclasses import dataclass
from urllib.parse import quote

from . import __version__

RELEASES_URL = "https://github.com/GalBlatman/markerlite/releases"


@dataclass(frozen=True)
class UpdateResult:
    message: str
    url: str | None = None


def version_key(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value)
    if not match:
        raise ValueError("invalid release version")
    return tuple(int(part) for part in match.groups())


def latest_release():
    """Exactly one HTTPS GET, no redirect following or retry, ten-second timeout."""
    connection = http.client.HTTPSConnection("api.github.com", timeout=10)
    try:
        connection.request(
            "GET",
            "/repos/GalBlatman/markerlite/releases/latest",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "markerlite",
            },
        )
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        body = response.read(1048577)
        if len(body) > 1048576:
            raise ValueError("release response too large")
        return json.loads(body)
    finally:
        connection.close()


def check_for_updates(current=__version__, fetch=latest_release) -> UpdateResult:
    try:
        data = fetch()
        tag = data["tag_name"]
        latest = version_key(tag)
        if latest <= version_key(current):
            return UpdateResult("You're up to date")
        return UpdateResult(
            f"{tag} is available", RELEASES_URL + "/tag/" + quote(tag, safe="")
        )
    except Exception:
        return UpdateResult("Couldn't check; open the Releases page?", RELEASES_URL)
