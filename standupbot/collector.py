import datetime as dt
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from standupbot.config import Settings
from standupbot.slack import SlackClient
from standupbot.storage import Storage

log = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "Morning! Drop your standup update here when you're online.\n"
    "Format isn't strict, but yesterday / today / blockers works best."
)

# quick words indicating someone is away so we don't nag or mark them missing
SKIP_KEYWORDS = {"pto", "vacation", "off", "sick", "afk", "ooo", "holiday"}


class StandupCollector:
    """Coordinates sending morning prompts and polling DM replies."""

    def __init__(self, cfg: Settings, slack: SlackClient, db: Storage):
        self.cfg = cfg
        self.slack = slack
        self.db = db

    def send_prompts(self, target_date: Optional[dt.date] = None) -> int:
        day = target_date or dt.date.today()
        sent = 0
        for member in self.cfg.team_members:
            existing = self.db.get_prompt(member.slack_id, day)
            if existing:
                continue

            dm_channel = self.slack.open_dm(member.slack_id)
            if not dm_channel:
                log.warning("could not open dm with %s (%s)", member.name, member.slack_id)
                continue

            ts = self.slack.post_message(dm_channel, DEFAULT_PROMPT)
            if ts:
                self.db.save_prompt(member.slack_id, dm_channel, ts, day)
                sent += 1
        return sent

    def parse_response(self, text: str) -> Tuple[str, Dict[str, str]]:
        clean = text.strip()
        lower = clean.lower()

        # Single line skip check
        first_line_words = set(re.findall(r"\b\w+\b", lower.split("\n")[0]))
        if first_line_words & SKIP_KEYWORDS and len(clean.splitlines()) <= 2:
            return "skipped", {"raw": clean}

        sections: Dict[str, str] = {}
        current_key = "general"
        current_lines: List[str] = []

        # Loose section header regex: "yesterday:", "[today]", "*blockers*", etc.
        header_re = re.compile(
            r"^(?:\*|_|~)?\s*(yesterday|today|blockers?|notes?|tasks?)\s*(?:\*|_|~)?\s*[:-]?\s*$",
            re.IGNORECASE,
        )

        for line in clean.splitlines():
            m = header_re.match(line.strip())
            if m:
                if current_lines:
                    sections[current_key] = "\n".join(current_lines).strip()
                    current_lines = []
                raw_key = m.group(1).lower()
                if "yesterday" in raw_key:
                    current_key = "yesterday"
                elif "today" in raw_key:
                    current_key = "today"
                elif "block" in raw_key:
                    current_key = "blockers"
                else:
                    current_key = raw_key
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_key] = "\n".join(current_lines).strip()

        return "active", sections

    def collect_replies(self, target_date: Optional[dt.date] = None) -> int:
        day = target_date or dt.date.today()
        prompts = self.db.list_prompts_for_date(day)
        collected = 0

        for p in prompts:
            # Slack timestamps are unix epoch strings with decimal points
            messages = self.slack.get_conversation_history(
                channel=p["channel_id"],
                oldest=p["prompt_ts"],
            )
            # Oldest-first so the conversation reads chronologically
            messages = sorted(messages, key=lambda m: float(m.get("ts", 0)))

            user_msgs = [
                m for m in messages
                if m.get("user") == p["slack_id"]
                and not m.get("subtype")  # ignore join messages or bot updates
            ]
            if not user_msgs:
                continue

            raw_text = "\n".join(m.get("text", "").strip() for m in user_msgs if m.get("text"))
            if not raw_text:
                continue

            status, parsed = self.parse_response(raw_text)
            # print(f"DEBUG: {p['slack_id']} -> {status} sections={list(parsed.keys())}")
            self.db.save_entry(
                slack_id=p["slack_id"],
                standup_date=day,
                raw_text=raw_text,
                parsed_sections=parsed,
                status=status,
            )
            collected += 1

        return collected
