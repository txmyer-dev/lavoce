"""Unit tests for the intelligence-extraction pipeline (parse + sinks).

These cover the pure logic — LLM-reply parsing, note rendering, and the
Todoist dry-run — without needing torch, the LLM, or a running server.
"""

import os

from backend.services.extraction import ExtractionResult, parse_extraction
from backend.services.sinks import vault as vault_sink
from backend.services.sinks import todoist as todoist_sink


def test_parse_clean_json():
    raw = (
        '{"summary": "Errands and an idea.", '
        '"action_items": ["Call the dentist", "Pay the electric bill"], '
        '"ideas": ["Lazy-load avatars"], "tags": ["errands", "perf"]}'
    )
    r = parse_extraction(raw)
    assert r.summary == "Errands and an idea."
    assert r.action_items == ["Call the dentist", "Pay the electric bill"]
    assert r.ideas == ["Lazy-load avatars"]
    assert r.tags == ["errands", "perf"]


def test_parse_fenced_json_with_prose():
    raw = 'Sure! Here is the JSON:\n```json\n{"summary": "hi", "action_items": [], "ideas": [], "tags": ["x"]}\n```'
    r = parse_extraction(raw)
    assert r.summary == "hi"
    assert r.tags == ["x"]


def test_parse_strips_hash_and_bullets():
    raw = '{"summary": "s", "action_items": ["- do a thing"], "ideas": [], "tags": ["#Foo", "BAR"]}'
    r = parse_extraction(raw)
    assert r.action_items == ["do a thing"]
    assert r.tags == ["foo", "bar"]


def test_parse_non_json_falls_back_to_summary():
    r = parse_extraction("the model just rambled without any json")
    assert "rambled" in r.summary
    assert r.action_items == []


def test_parse_coerces_string_field_to_list():
    raw = '{"summary": "s", "action_items": "single task", "ideas": [], "tags": []}'
    r = parse_extraction(raw)
    assert r.action_items == ["single task"]


def test_build_note_has_frontmatter_and_sections():
    r = ExtractionResult(
        summary="A test capture.",
        action_items=["Do X", "Do Y"],
        ideas=["Idea one"],
        tags=["testing", "voice"],
    )
    filename, body = vault_sink.build_note(
        r,
        transcript="raw words here",
        capture_id="abc-123",
        source="dictation",
        stt_model="turbo",
        llm_model="freellmapi-remote",
    )
    assert filename.endswith(".md")
    assert body.startswith("---\n")
    assert "type: voice-capture" in body
    assert "capture_id: abc-123" in body
    assert "- [ ] Do X" in body  # checkbox for Todoist reconciliation
    assert "- Idea one" in body
    assert "raw words here" in body
    assert "  - testing" in body


def test_write_note_lands_in_configured_inbox(tmp_path):
    os.environ["VOICEBOX_VAULT_INBOX"] = str(tmp_path)
    try:
        r = ExtractionResult(summary="s", action_items=["t"], ideas=[], tags=["a"])
        path = vault_sink.write_note(
            r, transcript="hello", capture_id="cap1", source="file"
        )
        assert path.exists()
        assert path.parent == tmp_path
        assert "cap1" in path.read_text()
    finally:
        del os.environ["VOICEBOX_VAULT_INBOX"]


def test_todoist_dry_run_prepares_but_does_not_dispatch():
    r = ExtractionResult(summary="s", action_items=["Call bob", "Ship it"])
    payloads = todoist_sink.prepare_tasks(r, capture_id="cap1")
    assert [p["content"] for p in payloads] == ["Call bob", "Ship it"]

    out = todoist_sink.dispatch_tasks(payloads, dry_run=True)
    assert out["dispatched"] is False
    assert out["created"] == []
    assert out["prepared"] == payloads


def test_todoist_normalize_matches_sync_script():
    # Mirrors sync_todoist_tasks.normalize_text so shadow-map keys line up.
    assert todoist_sink.normalize_text("**Call** [Bob](http://x)") == "call bob"
