"""Release checks with injected replies; tests make no network requests."""

import pytest

from markerlite.gui_updates import check_for_updates, version_key


def test_numeric_version_order():
    assert version_key("v0.1.10") > version_key("0.1.9")
    assert version_key("1.0.0") > version_key("0.99.99")
    assert version_key("0.2.0") > version_key("0.1.18")


@pytest.mark.parametrize("tag", ["v0.1.18", "v0.1.17"])
def test_current_or_older(tag):
    result = check_for_updates("0.1.18", lambda: {"tag_name": tag})
    assert result.message == "You're up to date" and result.url is None


def test_new_release_link_is_derived_from_validated_tag():
    result = check_for_updates(
        "0.1.18", lambda: {"tag_name": "v0.2.0", "html_url": "http://untrusted.invalid"}
    )
    assert result.message == "v0.2.0 is available"
    assert result.url == "https://github.com/GalBlatman/markerlite/releases/tag/v0.2.0"


@pytest.mark.parametrize(
    "reply",
    [None, {}, [], {"tag_name": None}, {"tag_name": "bad"}, {"tag_name": "v01.2.3"}],
)
def test_malformed_reply_offers_releases(reply):
    result = check_for_updates(fetch=lambda: reply)
    assert result.message == "Couldn't check; open the Releases page?"
    assert result.url.endswith("/releases")


@pytest.mark.parametrize(
    "error", [TimeoutError(), OSError("offline"), ValueError("HTTP 403")]
)
def test_transport_errors(error):
    def fetch():
        raise error

    assert check_for_updates(fetch=fetch).message.startswith("Couldn't check")


def test_exactly_one_get_and_timeout(monkeypatch):
    from markerlite import gui_updates

    calls = []

    class Response:
        status = 200

        def read(self, size):
            return b'{"tag_name":"v0.1.18"}'

    class Connection:
        def __init__(self, host, timeout):
            calls.append((host, timeout))

        def request(self, method, path, headers):
            calls.append((method, path, headers))

        def getresponse(self):
            return Response()

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(gui_updates.http.client, "HTTPSConnection", Connection)
    assert gui_updates.latest_release()["tag_name"] == "v0.1.18"
    assert calls[0] == ("api.github.com", 10)
    assert calls[1][0:2] == ("GET", "/repos/GalBlatman/markerlite/releases/latest")
    assert len(calls) == 3 and calls[-1] == "closed"
