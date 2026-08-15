import pytest
from standupbot.collector import parse_standup_text, send_prompts, poll_replies
import httpx

def test_parse_numbered_list():
    text = """1. Reviewed PR 104 and merged migration
2. Writing webhook receivers
3. None right now"""
    parsed = parse_standup_text(text)
    assert "Reviewed PR 104" in parsed["yesterday"]
    assert "Writing webhook receivers" in parsed["today"]
    assert parsed["blockers"] == "None right now"

def test_parse_section_headers():
    text = """Yesterday: fixed redis memory leak on worker-02
Today: profiling queries on user service
Blockers: waiting on devops for aws perms"""
    parsed = parse_standup_text(text)
    assert "fixed redis memory leak" in parsed["yesterday"]
    assert "profiling queries" in parsed["today"]
    assert "waiting on devops" in parsed["blockers"]

def test_parse_unstructured_fallback():
    # if someone just writes a single blob, dump it into today
    text = "Working on tickets 404 and 501 all day, got delayed by dns issues."
    parsed = parse_standup_text(text)
    assert parsed["yesterday"] == ""
    assert parsed["today"] == text
    assert parsed["blockers"] == ""

def test_send_prompts_with_transport(sample_config, temp_db, fake_slack_transport):
    client = httpx.Client(transport=fake_slack_transport)
    count = send_prompts(sample_config, temp_db, client=client, target_date="2024-04-10")
    assert count == 2
    
    pending = temp_db.get_pending_prompts("2024-04-10")
    assert len(pending) == 2

def test_poll_replies_finds_answers(sample_config, temp_db, fake_slack_transport):
    client = httpx.Client(transport=fake_slack_transport)
    # seed prompt history
    temp_db.record_prompt("U100", "D999", "2024-04-10", "1700000000.000100")
    
    collected = poll_replies(sample_config, temp_db, client=client, target_date="2024-04-10")
    assert collected == 1
    
    saved = temp_db.get_replies_for_date("2024-04-10")
    assert len(saved) == 1
    assert saved[0]["slack_id"] == "U100"
