import argparse
import sys
import os
import time
import logging
from standupbot.config import load_config
from standupbot.storage import Database
from standupbot.collector import send_prompts, poll_replies
from standupbot.digest import build_and_post_digest

log = logging.getLogger("standupbot")

def run_daemon(cfg, db):
    log.info("Starting daemon loop, checking schedule every 30s")
    while True:
        # quick and dirty scheduler, systemd timer or cron is better but keeping this for local testing
        now = time.strftime("%H:%M")
        if now == cfg.prompt_time:
            log.info("Triggering morning prompts at %s", now)
            send_prompts(cfg, db)
            time.sleep(65)
        elif now == cfg.digest_time:
            log.info("Collating and publishing digest at %s", now)
            poll_replies(cfg, db)
            build_and_post_digest(cfg, db)
            time.sleep(65)
        time.sleep(25)

def main():
    parser = argparse.ArgumentParser(prog="standupbot", description="Morning standup collector and digest poster.")
    parser.add_argument("-c", "--config", default=os.getenv("STANDUP_CONFIG", "config.json"), help="Path to json config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Collect and print digest to stdout without posting to Slack")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("prompt", help="Send standup questions to all active team members via Slack DM")
    subparsers.add_parser("poll", help="Check DM channels for pending answers")
    digest_p = subparsers.add_parser("digest", help="Generate markdown summary and post to team channel")
    digest_p.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to today")
    subparsers.add_parser("daemon", help="Run polling and scheduler in foreground")
    
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    cfg = load_config(args.config)
    db = Database(cfg.db_path)
    db.init_schema()
    
    if args.command == "prompt":
        count = send_prompts(cfg, db)
        print(f"Sent prompts to {count} users.")
    elif args.command == "poll":
        got = poll_replies(cfg, db)
        print(f"Collected {got} new responses.")
    elif args.command == "digest":
        # sync any last-minute replies before writing summary
        poll_replies(cfg, db)
        target_date = getattr(args, "date", None)
        build_and_post_digest(cfg, db, target_date=target_date, dry_run=args.dry_run)
    elif args.command == "daemon":
        try:
            run_daemon(cfg, db)
        except KeyboardInterrupt:
            log.info("Stopping daemon")
            sys.exit(0)

if __name__ == "__main__":
    main()
