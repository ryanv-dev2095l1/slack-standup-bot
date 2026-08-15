from standupbot.storage import Database

def test_init_creates_tables(temp_db):
    tables = temp_db.get_table_names()
    assert "prompt_history" in tables
    assert "standup_replies" in tables

def test_record_prompt_idempotent(temp_db):
    # recording prompt sent for same date should not duplicate key error
    temp_db.record_prompt("U100", "D999", "2024-04-10", "1700000000.000100")
    temp_db.record_prompt("U100", "D999", "2024-04-10", "1700000000.000100")
    
    prompts = temp_db.get_pending_prompts("2024-04-10")
    assert len(prompts) == 1
    assert prompts[0]["slack_id"] == "U100"
    assert prompts[0]["dm_channel"] == "D999"

def test_save_and_fetch_reply(temp_db):
    date_str = "2024-04-10"
    temp_db.record_prompt("U100", "D999", date_str, "1700000000.000100")
    
    raw_body = "yesterday: auth\ntoday: tests\nblockers: none"
    temp_db.save_reply(
        slack_id="U100",
        date=date_str,
        raw_text=raw_body,
        yesterday_text="auth",
        today_text="tests",
        blockers_text="none",
        reply_ts="1700000050.000200"
    )
    
    replies = temp_db.get_replies_for_date(date_str)
    assert len(replies) == 1
    r = replies[0]
    assert r["slack_id"] == "U100"
    assert r["today_text"] == "tests"
    assert r["blockers_text"] == "none"

def test_get_replies_empty_for_missing_date(temp_db):
    res = temp_db.get_replies_for_date("1999-01-01")
    assert res == []
