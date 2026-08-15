import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)


class SlackClient:
    """Thin async client over Slack Web API with rate-limit retry."""

    BASE_URL = "https://slack.com/api"

    def __init__(self, token: str):
        self.token = token
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        )

    async def close(self):
        await self._client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        # Slack returns 429 or ok:false with error ratelimited
        for attempt in range(4):
            res = await self._client.request(method, endpoint, **kwargs)
            if res.status_code == 429:
                retry_after = int(res.headers.get("Retry-After", 2))
                logger.warning("slack rate limit on %s, sleeping %ds", endpoint, retry_after)
                await asyncio.sleep(retry_after)
                continue

            res.raise_for_status()
            data = res.json()

            if not data.get("ok"):
                err = data.get("error", "unknown")
                if err == "ratelimited" and attempt < 3:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"Slack error on {endpoint}: {err}")

            return data

        raise RuntimeError(f"Slack request failed after retries: {endpoint}")

    async def post_message(self, channel: str, text: str, mrkdwn: bool = True) -> dict:
        payload = {"channel": channel, "text": text, "mrkdwn": mrkdwn}
        # print(f"DEBUG slack post to {channel}: {text[:40]}")
        return await self._request("POST", "chat.postMessage", json=payload)

    async def open_dm(self, user_id: str) -> str:
        res = await self._request("POST", "conversations.open", json={"users": user_id})
        return res["channel"]["id"]

    async def get_channel_history(self, channel_id: str, oldest: float) -> list[dict]:
        messages: list[dict] = []
        cursor = None

        while True:
            params: dict[str, str | int] = {
                "channel": channel_id,
                "oldest": str(oldest),
                "limit": 100,
            }
            if cursor:
                params["cursor"] = cursor

            res = await self._request("GET", "conversations.history", params=params)
            messages.extend(res.get("messages", []))

            cursor = res.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return messages

    async def list_users(self) -> list[dict]:
        # TODO: cache user list to disk so morning run doesn't hit this every single time
        users: list[dict] = []
        cursor = None
        while True:
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            res = await self._request("GET", "users.list", params=params)
            for member in res.get("members", []):
                if not member.get("deleted") and not member.get("is_bot"):
                    users.append(member)
            cursor = res.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return users
