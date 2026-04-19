import pytest
from acetalk.core.prompt_linter import PromptLinter, LintResult


def lint(tags="", lyrics=""):
    return PromptLinter().lint(tags, lyrics)


def severities(results):
    return [r.severity for r in results]


def fields(results):
    return [r.field for r in results]


# ── Tags: token count ─────────────────────────────────────────────────────────

def test_tags_too_few_tokens():
    results = lint(tags="ambient, slow")
    assert any(r.field == "tags" and r.severity == "tip" and "2" in r.message for r in results)


def test_tags_ok_count_no_warning():
    tags = "psytrance, 140 BPM, driving, synth bass, female vocal, melodic"
    results = lint(tags=tags)
    count_issues = [r for r in results if r.field == "tags" and "token" in r.message.lower()]
    assert not count_issues


def test_tags_above_12_warning():
    tags = ", ".join([f"tok{i}" for i in range(13)])
    results = lint(tags=tags)
    assert any(r.field == "tags" and r.severity == "warning" and "13" in r.message for r in results)


def test_tags_above_15_error():
    tags = ", ".join([f"tok{i}" for i in range(16)])
    results = lint(tags=tags)
    # Should get error not just warning when > 15
    assert any(r.field == "tags" and r.severity == "error" for r in results)


# ── Tags: brackets ────────────────────────────────────────────────────────────

def test_tags_brackets_error():
    results = lint(tags="ambient, [Guitar Solo], slow")
    assert any(r.field == "tags" and r.severity == "error" and "racket" in r.message for r in results)


def test_tags_no_brackets_ok():
    results = lint(tags="ambient, slow, guitar")
    assert not any(r.field == "tags" and "racket" in r.message for r in results)


# ── Tags: section keywords ────────────────────────────────────────────────────

def test_tags_section_keyword_error():
    results = lint(tags="ambient, chorus, slow")
    assert any(r.field == "tags" and r.severity == "error" and "chorus" in r.message.lower() for r in results)


def test_tags_solo_keyword_error():
    results = lint(tags="guitar, solo, ambient")
    assert any(r.field == "tags" and r.severity == "error" for r in results)


# ── Tags: parentheses ─────────────────────────────────────────────────────────

def test_tags_parentheses_error():
    results = lint(tags="ambient, (harmony), slow")
    assert any(r.field == "tags" and r.severity == "error" and "arenthes" in r.message for r in results)


# ── Tags: duplicates ──────────────────────────────────────────────────────────

def test_tags_duplicate_warning():
    results = lint(tags="ambient, slow, ambient")
    assert any(r.field == "tags" and r.severity == "warning" and "ambient" in r.message.lower() for r in results)


def test_tags_case_insensitive_duplicate():
    results = lint(tags="Ambient, ambient")
    assert any(r.field == "tags" and r.severity == "warning" for r in results)


# ── Tags: conflicting tempo ───────────────────────────────────────────────────

def test_tags_conflicting_tempo_warning():
    results = lint(tags="slow, driving, guitar")
    assert any(r.field == "tags" and r.severity == "warning" and "empo" in r.message for r in results)


def test_tags_single_tempo_ok():
    results = lint(tags="slow, ambient, guitar")
    assert not any(r.field == "tags" and "empo" in r.message for r in results)


def test_tags_introverted_not_section_keyword():
    results = lint(tags="introverted, guitar, ambient")
    assert not any(r.field == "tags" and r.severity == "error" and "keyword" in r.message.lower() for r in results)


def test_tags_slowcore_not_tempo_conflict():
    results = lint(tags="slowcore, guitar, electric")
    assert not any(r.field == "tags" and "empo" in r.message for r in results)


# ── Lyrics: no structural brackets ───────────────────────────────────────────

def test_lyrics_no_brackets_tip():
    results = lint(lyrics="some lyrics here with no brackets")
    assert any(r.field == "lyrics" and r.severity == "tip" and "structural" in r.message.lower() for r in results)


def test_lyrics_has_brackets_no_tip():
    results = lint(lyrics="[Verse]\nhello world")
    assert not any(r.field == "lyrics" and "structural" in r.message.lower() for r in results)


def test_lyrics_empty_no_tip():
    results = lint(lyrics="")
    assert not any(r.field == "lyrics" and "structural" in r.message.lower() for r in results)


# ── Lyrics: nested brackets ───────────────────────────────────────────────────

def test_lyrics_nested_brackets_error():
    results = lint(lyrics="[[Verse]]\nhello")
    assert any(r.field == "lyrics" and r.severity == "error" and "ested" in r.message.lower() for r in results)


# ── Lyrics: unclosed brackets ─────────────────────────────────────────────────

def test_lyrics_unclosed_bracket_error():
    results = lint(lyrics="[Verse\nhello")
    assert any(r.field == "lyrics" and r.severity == "error" and "mismatched" in r.message.lower() for r in results)


def test_lyrics_matched_brackets_ok():
    results = lint(lyrics="[Verse]\nhello [world]")
    assert not any(r.field == "lyrics" and "mismatched" in r.message.lower() for r in results)


# ── Lyrics: empty brackets ────────────────────────────────────────────────────

def test_lyrics_empty_brackets_warning():
    results = lint(lyrics="[Verse]\nhello\n[]")
    assert any(r.field == "lyrics" and r.severity == "warning" and "empty" in r.message.lower() for r in results)


# ── Lyrics: bare [Solo] ───────────────────────────────────────────────────────

def test_lyrics_bare_solo_tip():
    results = lint(lyrics="[Verse]\nhello\n[Solo]")
    assert any(r.field == "lyrics" and r.severity == "tip" and "instrument" in r.suggestion.lower() for r in results)


def test_lyrics_named_solo_no_tip():
    results = lint(lyrics="[Verse]\nhello\n[Guitar Solo]")
    assert not any(r.field == "lyrics" and r.severity == "tip" and "instrument" in r.suggestion.lower() for r in results)


# ── Lyrics: language codes ────────────────────────────────────────────────────

def test_lyrics_invalid_lang_code_warning():
    results = lint(lyrics="[Verse]\n[xx]\nhello")
    assert any(r.field == "lyrics" and r.severity == "warning" and "xx" in r.message for r in results)


def test_lyrics_valid_lang_code_ok():
    results = lint(lyrics="[Verse]\n[zh]\nhello")
    assert not any(r.field == "lyrics" and r.severity == "warning" and "zh" in r.message for r in results)


# ── Lyrics: content after [Outro] ─────────────────────────────────────────────

def test_lyrics_content_after_outro_warning():
    results = lint(lyrics="[Verse]\nhello\n[Outro]\nbye\n[Bridge]\nextra")
    assert any(r.field == "lyrics" and r.severity == "warning" and "utro" in r.message for r in results)


def test_lyrics_outro_is_last_ok():
    results = lint(lyrics="[Verse]\nhello\n[Chorus]\nyes\n[Outro]\nbye")
    assert not any(r.field == "lyrics" and "utro" in r.message for r in results)


# ── Lyrics: all-caps line ─────────────────────────────────────────────────────

def test_lyrics_all_caps_line_tip():
    results = lint(lyrics="[Verse]\nTHIS IS THE VERSE LINE RIGHT HERE")
    assert any(r.field == "lyrics" and r.severity == "tip" and "caps" in r.message.lower() for r in results)


def test_lyrics_single_caps_word_ok():
    results = lint(lyrics="[Verse]\nhello WORLD today")
    assert not any(r.field == "lyrics" and "caps" in r.message.lower() for r in results)


# ── Combined rules ────────────────────────────────────────────────────────────

def test_combined_sparse_tags_rich_lyrics_warning():
    lyrics = "[Intro]\na\n[Verse]\nb\n[Chorus]\nc\n[Bridge]\nd\n[Outro]\ne"
    results = lint(tags="slow, guitar", lyrics=lyrics)
    assert any(r.field == "combined" and r.severity == "warning" and "sparse" in r.message.lower() for r in results)


def test_combined_brackets_no_content_warning():
    results = lint(tags="ambient", lyrics="[Verse][Chorus][Outro]")
    assert any(r.field == "combined" and r.severity == "warning" and "no content" in r.message.lower() for r in results)


def test_combined_ok_when_content_present():
    results = lint(tags="ambient, slow, guitar", lyrics="[Verse]\nhello world\n[Chorus]\nyes")
    assert not any(r.field == "combined" and "no content" in r.message.lower() for r in results)


# ── LintResult dataclass ──────────────────────────────────────────────────────

def test_lint_result_fields():
    r = LintResult(severity="error", field="tags", message="test msg", suggestion="fix it")
    assert r.severity == "error"
    assert r.field == "tags"
    assert r.message == "test msg"
    assert r.suggestion == "fix it"
