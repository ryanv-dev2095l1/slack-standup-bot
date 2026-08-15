import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        os.environ.setdefault(key, val)


@dataclass
class Config:
    slack_bot_token: str
    slack_channel: str
    github_token: str
    github_org: str
    data_dir: Path
    github_repos: list[str] = field(default_factory=list)
    alertmanager_url: str = ""
    standup_time: str = "10:00"
    reminder_time: str = "09:00"
    user_map_file: Path = Path("users.json")


def load_config() -> Config:
    _load_dotenv()

    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise ValueError("SLACK_BOT_TOKEN is required")

    channel = os.getenv("SLACK_CHANNEL", "#dev-standup")
    gh_token = os.getenv("GITHUB_TOKEN", "")
    gh_org = os.getenv("GITHUB_ORG", "")
    alertmanager = os.getenv("ALERTMANAGER_URL", "").rstrip("/")

    raw_repos = os.getenv("GITHUB_REPOS", "")
    repos = [r.strip() for r in raw_repos.split(",") if r.strip()]

    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    user_map = Path(os.getenv("USER_MAP_FILE", "users.json"))

    return Config(
        slack_bot_token=token,
        slack_channel=channel,
        github_token=gh_token,
        github_org=gh_org,
        github_repos=repos,
        alertmanager_url=alertmanager,
        data_dir=data_dir,
        standup_time=os.getenv("STANDUP_TIME", "10:00"),
        reminder_time=os.getenv("REMINDER_TIME", "09:00"),
        user_map_file=user_map,
    )
