from datetime import datetime, timezone
import httpx


class GitHubClient:
    """Pulls authored PRs and merged work for standup enrichment."""

    def __init__(self, token: str, org: str | None = None):
        self.token = token
        self.org = org
        self.base_url = "https://api.github.com"
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
        )

    def close(self):
        self._client.close()

    def get_recent_prs(self, username: str, since: datetime) -> list[dict]:
        # GitHub search syntax wants iso8601 without microsecond noise
        since_str = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        query = f"author:{username} type:pr updated:>={since_str}"
        if self.org:
            query += f" org:{self.org}"

        # print(f"debug search: {query}")
        prs = []
        page = 1

        while True:
            res = self._client.get(
                f"{self.base_url}/search/issues",
                params={
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": 50,
                    "page": page,
                },
            )
            if res.status_code == 403 or res.status_code == 429:
                # rate limit hit - don't crash standup generation, return what we got
                break
            if res.status_code != 200:
                break

            data = res.json()
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                # draft PRs don't have draft key directly on search results,
                # but draft state can be inferred or checked in state_reason
                prs.append({
                    "title": item["title"],
                    "url": item["html_url"],
                    "state": "draft" if item.get("draft") else item["state"],
                    "merged": bool(item.get("pull_request", {}).get("merged_at")),
                    "repo": item["repository_url"].split("/")[-1],
                    "comments": item.get("comments", 0),
                })

            if len(prs) >= data.get("total_count", 0) or page >= 3:
                # 3 pages is 150 PRs, more than enough for a 24h standup window
                break
            page += 1

        # TODO(alex): graphql search would cut multiple rest calls down to 1 if we add commit queries
        return prs

    def get_user_commit_count(self, username: str, repo: str, since: datetime) -> int:
        since_str = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = self._client.get(
            f"{self.base_url}/repos/{self.org}/{repo}/commits",
            params={"author": username, "since": since_str, "per_page": 100},
        )
        if res.status_code != 200:
            return 0
        return len(res.json())
