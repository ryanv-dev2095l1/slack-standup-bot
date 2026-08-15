import datetime as dt
from typing import Any, Dict, List, Optional


def _format_sections(parsed: Dict[str, str], fallback_raw: str) -> str:
    if not parsed or "general" in parsed and len(parsed) == 1:
        return fallback_raw

    lines = []
    for header in ("yesterday", "today", "blockers"):
        val = parsed.get(header)
        if not val:
            continue
        title = header.capitalize()
        if header == "blockers":
            title = ":warning: Blockers"
        lines.append(f"*{title}*\n{val}")

    # Any extra custom headers they typed
    for k, v in parsed.items():
        if k not in ("yesterday", "today", "blockers", "raw") and v:
            lines.append(f"*{k.capitalize()}*\n{v}")

    return "\n\n".join(lines) if lines else fallback_raw


def _format_prs(prs: List[Dict[str, Any]]) -> str:
    if not prs:
        return ""
    items = []
    for pr in prs:
        repo = pr.get("repo", "").split("/")[-1]
        title = pr.get("title", "").strip()
        url = pr.get("url", "")
        state = pr.get("state", "open")
        # Mark merged with a little check
        icon = ":white_check_mark:" if state == "merged" else ":git-pull-request:"
        if url:
            items.append(f"{icon} [{repo}] <{url}|{title}>")
        else:
            items.append(f"{icon} [{repo}] {title}")
    return "\n".join(items)


def format_digest_blocks(
    report_date: dt.date,
    entries: List[Dict[str, Any]],
    team_map: Dict[str, Dict[str, str]],  # slack_id -> member meta
    github_activity: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    missing_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Builds Slack mrkdwn blocks for the daily team standup dump."""
    date_str = report_date.strftime("%A, %b %d")
    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Team Standup - {date_str}",
            },
        },
        {"type": "divider"},
    ]

    github_activity = github_activity or {}
    active_entries = [e for e in entries if e.get("status") != "skipped"]
    skipped_entries = [e for e in entries if e.get("status") == "skipped"]

    if not entries and not missing_ids:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No updates submitted today._",
            },
        })
        return blocks

    for entry in active_entries:
        slack_id = entry["slack_id"]
        meta = team_map.get(slack_id, {})
        name = meta.get("name", f"<@{slack_id}>")
        parsed = entry.get("parsed_sections") or {}
        body = _format_sections(parsed, entry.get("raw_text", ""))

        # Append GitHub activity if we tracked any for their handle
        gh_user = meta.get("github_user")
        if gh_user and gh_user in github_activity:
            pr_text = _format_prs(github_activity[gh_user])
            if pr_text:
                body += f"\n\n*GitHub Activity*\n{pr_text}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{name}*\n{body}",
            },
        })

    if skipped_entries:
        skip_names = []
        for entry in skipped_entries:
            meta = team_map.get(entry["slack_id"], {})
            skip_names.append(meta.get("name", f"<@{entry['slack_id']}>"))
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":palm_tree: *Out today:* {', '.join(skip_names)}",
                }
            ],
        })

    if missing_ids:
        missing_names = []
        for sid in missing_ids:
            meta = team_map.get(sid, {})
            missing_names.append(meta.get("name", f"<@{sid}>"))
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":hourglass: *No update yet:* {', '.join(missing_names)}",
                }
            ],
        })

    return blocks
