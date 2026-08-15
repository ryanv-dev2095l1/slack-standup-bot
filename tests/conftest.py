import pytest
import os
import tempfile
import json
import httpx
from standupbot.config import BotConfig, UserMapping
from standupbot.storage import Database

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    db = Database(path)
    db.init_schema()
    yield db
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def sample_config():
    return BotConfig(
        slack_token="xoxb-fake-token-123",
        github_token="ghp_fake_gh_secret",
        team_channel="C12345678",
        github_org="internal-corp",
        users=[
            UserMapping(slack_id="U100", gh_username="alice_dev", name="Alice"),
            UserMapping(slack_id="U200", gh_username="bob_ops", name="Bob"),
        ],
        db_path=":memory:",
        prompt_time="09:00",
        digest_time="10:00"
    )

@pytest.fixture
def fake_slack_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "conversations.open" in url:
            return httpx.Response(200, json={"ok": True, "channel": {"id": "D999"}})
        if "chat.postMessage" in url:
            return httpx.Response(200, json={"ok": True, "ts": "1700000000.000100"})
        if "conversations.history" in url:
            # returns canned answer from user
            return httpx.Response(200, json={
                "ok": True,
                "messages": [
                    {
                        "user": "U100",
                        "text": "1. finished auth refactor\n2. starting payment webhooks\n3. no blockers",
                        "ts": "1700000050.000200"
                    },
                    {
                        "user": "BOT1",
                        "text": "Morning! What are you working on today?",
                        "ts": "1700000000.000100"
                    }
                ]
            })
        return httpx.Response(404, json={"ok": False, "error": "not_found"})
    
    return httpx.MockTransport(handler)

@pytest.fixture
def fake_gh_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        if "search/issues" in str(request.url):
            items = [
                {
                    "html_url": "https://github.com/internal-corp/api/pull/42",
                    "title": "Add idempotency keys to payments",
                    "user": {"login": "alice_dev"},
                    "state": "open",
                    "pull_request": {}
                }
            ]
            return httpx.Response(200, json={"total_count": 1, "items": items})
        return httpx.Response(200, json=[])
    
    return httpx.MockTransport(handler)
