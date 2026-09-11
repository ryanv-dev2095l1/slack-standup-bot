# slack-standup-bot

I got tired of commercial standup bots that cost $3/user/month just to ping people on Slack and post three lines into a channel. Also tired of typing out Jira tickets and PR numbers that git already knows about.

This runs as a lightweight process on a VM or cron box. It opens DMs with configured users at a set time, gathers their answers (yesterday / today / blockers), checks GitHub for merged PRs in the last 24h, and posts a compiled thread to `#team-dev`.

## Requirements

- Python 3.11+
- Slack bot token with `chat:write`, `im:history`, `im:write`, `users:read`
- GitHub personal access token (optional, for auto-filling PR activity)
- SQLite3 (uses local file db)

## Install

```bash
git clone https://github.com/yourname/slack-standup-bot
cd slack-standup-bot
python -m venv .venv
source .venv/bin/activate
pip install .
```

## Configuration

Set environment variables or drop them in a `.env` file:

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
GITHUB_TOKEN=ghp_...
GITHUB_ORG=mycompany
STANDUP_USERS=U01AAA:alice,U02BBB:bob,U03CCC:charlie
STANDUP_CRON="0 9 * * 1-5"
DIGEST_CRON="0 10 * * 1-5"
DB_PATH=./standup.db
```

## Running

Run the scheduler daemon:

```bash
standupbot run
```

Or trigger stages manually (handy for testing or running via external cron):

```bash
# Send morning DMs
standupbot prompt

# Compile answers and post summary to main channel
standupbot digest

# Inspect current day status
standupbot status
```

## License

MIT

<!-- checked: 2026-09-11 -->
