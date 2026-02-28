"""
Stalker — Mac research app
Describe someone you met. Claude searches the web and finds them.

Run with:  streamlit run app.py
"""

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import anthropic
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────

LOG_FILE = Path(__file__).parent / "search_log.jsonl"
MODELS = {
    "Haiku 4.5  (fast, ~$0.13/search)":  "claude-haiku-4-5-20251001",
    "Sonnet 4.6 (better, ~$0.50/search)": "claude-sonnet-4-6",
}
DEFAULT_MODEL  = "Haiku 4.5  (fast, ~$0.13/search)"
PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """\
You are a professional networking assistant. The user meets people at conferences, \
events, and social gatherings and wants help finding their publicly available \
professional information so they can follow up and stay in touch.

Your job is to find whatever the person has chosen to make public: their LinkedIn \
profile, company page, Twitter/X, published articles, conference talks, news \
mentions, and similar. You surface only information the person has voluntarily \
published — you do not aggregate private details.

This is the same kind of research anyone would do by Googling a new contact's name \
after a networking event. Treat it accordingly: helpful, factual, focused on \
professional and public-facing information.\
"""

# ── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Stalker", page_icon="🔍", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 2rem; }
  .stTextArea textarea { font-size: 1rem; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────

for key, default in [
    ("result",     None),
    ("search_id",  None),
    ("narrative",  ""),
    ("fb_saved",   False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helpers ───────────────────────────────────────────────────────────────────

def build_prompt(narrative: str) -> str:
    return f"""I met someone at an event and want to find their public professional \
profiles so I can follow up with them. Here are my notes from our conversation:

---
{narrative}
---

Please search for this person's publicly available professional information. \
Use whatever clues are in my notes — name, employer, city, industry, role — \
to find the right person. If a few people match, lead with the most likely one.

Return in this exact format:

## Most Likely Contact
[Name and one-line description — who you think this is and why]

## Professional Summary
[2–3 sentences: current role, company, what they're known for]

## Career Background
[Previous roles, companies, notable projects or achievements]

## Public Profiles & Links
- LinkedIn: [full URL or "not found"]
- Twitter/X: [full URL or "not found"]
- Company / personal site: [full URL or "not found"]
- Other: [conference talks, articles, news mentions, etc.]

## Additional Public Info
[Anything else they've published publicly — interviews, articles, awards, etc.]

## Confidence
[High / Medium / Low — one sentence on why]

## Extracted Name
[Their most likely full name, one line only]
"""


def extract_links(text: str) -> dict:
    """Pull social media URLs from Claude's formatted response."""
    links = {}
    for line in text.splitlines():
        lower = line.lower()
        url   = _first_url(line)
        if not url:
            continue
        if "linkedin" in lower and "linkedin:" in lower:
            links["LinkedIn"] = url
        elif ("twitter" in lower or "twitter/x" in lower) and ("twitter:" in lower or "twitter/x:" in lower):
            links["Twitter / X"] = url
        elif "instagram" in lower and "instagram:" in lower:
            links["Instagram"] = url
        elif "facebook" in lower and "facebook:" in lower:
            links["Facebook"] = url
        elif "other:" in lower:
            links["Other"] = url
    return links


def _first_url(line: str) -> str | None:
    m = re.search(r'https?://[^\s\)>"\]\',]+', line)
    if m:
        url = m.group(0).rstrip(".,;)")
        return url if "." in url else None
    return None


def extract_display_name(text: str) -> str | None:
    found = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("## extracted name"):
            found = True
            continue
        if found and stripped and not stripped.startswith("#"):
            return stripped
    return None


def extract_confidence(text: str) -> str | None:
    found = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("## confidence"):
            found = True
            continue
        if found and stripped and not stripped.startswith("#"):
            first_word = stripped.split()[0].rstrip(".,;:")
            if first_word in ("Low", "Medium", "High"):
                return first_word
            return stripped[:80]
    return None


def extract_display_name_v2(text: str) -> str | None:
    """Handles both 'Extracted Name' (v2) and legacy section names."""
    found = False
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("## extracted name") or lower.startswith("## most likely contact"):
            found = True
            continue
        if found and stripped and not stripped.startswith("#"):
            # Strip leading "Name: " or similar prefixes if present
            for prefix in ("name:", "contact:"):
                if stripped.lower().startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            return stripped.split("—")[0].split("-")[0].strip()
    return None


def run_research(narrative: str, api_key: str, model: str = MODELS[DEFAULT_MODEL]) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_prompt(narrative)

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "web-search-2025-03-05"},
    )

    text = "\n".join(
        block.text for block in message.content
        if hasattr(block, "text") and block.text
    )

    return {
        "profile":     text,
        "links":       extract_links(text),
        "name":        extract_display_name_v2(text),
        "confidence":  extract_confidence(text),
        "input_tokens":  getattr(message.usage, "input_tokens",  None),
        "output_tokens": getattr(message.usage, "output_tokens", None),
    }


def log_search(search_id: str, narrative: str, result: dict, model: str = "") -> None:
    entry = {
        "type":           "search",
        "id":             search_id,
        "timestamp":      datetime.now().isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model":          model,
        "narrative":      narrative,
        "extracted_name": result.get("name"),
        "confidence":     result.get("confidence"),
        "links_found":    list(result.get("links", {}).keys()),
        "input_tokens":   result.get("input_tokens"),
        "output_tokens":  result.get("output_tokens"),
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_feedback(search_id: str, correct: str, comment: str) -> None:
    entry = {
        "type":      "feedback",
        "search_id": search_id,
        "timestamp": datetime.now().isoformat(),
        "correct":   correct,   # "yes" | "partial" | "no"
        "comment":   comment,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_log() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    entries = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def compute_stats(entries: list[dict]) -> dict:
    searches  = [e for e in entries if e["type"] == "search"]
    feedbacks = [e for e in entries if e["type"] == "feedback"]
    fb_by_id  = {e["search_id"]: e for e in feedbacks}

    rated = [s for s in searches if s["id"] in fb_by_id]
    correct  = sum(1 for s in rated if fb_by_id[s["id"]]["correct"] == "yes")
    partial  = sum(1 for s in rated if fb_by_id[s["id"]]["correct"] == "partial")
    wrong    = sum(1 for s in rated if fb_by_id[s["id"]]["correct"] == "no")

    return {
        "total":   len(searches),
        "rated":   len(rated),
        "correct": correct,
        "partial": partial,
        "wrong":   wrong,
    }

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Settings")

    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        api_key = env_key
        st.success("API key from environment ✓")
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-api03-…",
            help="Get one at console.anthropic.com",
        )

    st.divider()

    model_label = st.selectbox("Model", list(MODELS.keys()), index=0)
    selected_model = MODELS[model_label]

    st.divider()

    st.subheader("🎤 Voice input tip")
    st.caption(
        "Wispr Flow works system-wide on Mac. Activate it with your shortcut "
        "(default: hold **Fn** or **Right ⌥**), speak, and the transcription "
        "appears wherever your cursor is — including the text box below."
    )

    st.divider()

    # Stats from log
    entries = load_log()
    stats   = compute_stats(entries)

    st.subheader("📊 Session stats")
    col_a, col_b = st.columns(2)
    col_a.metric("Searches", stats["total"])
    col_b.metric("Rated",    stats["rated"])

    if stats["rated"] > 0:
        col_c, col_d, col_e = st.columns(3)
        col_c.metric("✓",  stats["correct"])
        col_d.metric("~",  stats["partial"])
        col_e.metric("✗",  stats["wrong"])

    # Recent searches
    searches = [e for e in entries if e["type"] == "search"]
    if searches:
        st.divider()
        st.subheader("🕑 Recent searches")
        feedbacks = {e["search_id"]: e for e in entries if e["type"] == "feedback"}
        for s in reversed(searches[-8:]):
            fb = feedbacks.get(s["id"], {})
            badge = {"yes": "✓", "partial": "~", "no": "✗"}.get(fb.get("correct", ""), "·")
            name  = s.get("extracted_name") or s["narrative"][:30] + "…"
            conf  = s.get("confidence", "?")
            st.caption(f"{badge} **{name}** — {conf} confidence")

# ── Main ──────────────────────────────────────────────────────────────────────

st.title("🔍 Stalker")
st.caption("Describe someone you met. Claude searches the web and finds them.")

narrative = st.text_area(
    "Who did you meet?",
    height=180,
    placeholder=(
        'Example: "Met an older guy called Rangaraj at a conference in Bangalore. '
        'Grey hair, very senior-looking. Said he recently shut down a company and '
        'now runs two — one in the semiconductor space, one in skilling for '
        'high-tech workers in India."'
    ),
)

col1, col2 = st.columns([2, 5])
with col1:
    go = st.button("🔍  Research This Person", type="primary", use_container_width=True)
with col2:
    show_prompt = st.checkbox("Show prompt sent to Claude")

if show_prompt and narrative.strip():
    with st.expander("Prompt"):
        st.code(build_prompt(narrative.strip()), language="text")

# ── Run research ──────────────────────────────────────────────────────────────

if go:
    if not api_key:
        st.error("Enter your Anthropic API key in the sidebar first.")
    elif not narrative.strip():
        st.warning("Describe who you met in the box above.")
    else:
        with st.spinner("Claude is searching the web… (usually 15–30 seconds)"):
            try:
                result    = run_research(narrative.strip(), api_key, selected_model)
                search_id = str(uuid.uuid4())
                log_search(search_id, narrative.strip(), result, selected_model)

                st.session_state.result    = result
                st.session_state.search_id = search_id
                st.session_state.fb_saved  = False
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Check the key in the sidebar.")
            except anthropic.RateLimitError:
                st.error("Rate limit hit. Wait a moment and try again.")
            except Exception as e:
                st.error(f"Error: {e}")

# ── Display results ───────────────────────────────────────────────────────────

if st.session_state.result:
    result = st.session_state.result

    # Header row
    conf_colour = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(
        result.get("confidence", ""), "⚪"
    )
    name_display = result.get("name") or "Unknown"
    st.divider()
    head_col1, head_col2 = st.columns([4, 1])
    head_col1.subheader(f"📋 {name_display}")
    head_col2.markdown(
        f"**Confidence:** {conf_colour} {result.get('confidence', '?')}",
        help="How confident Claude is that this is the right person.",
    )

    # Social links
    links = result.get("links", {})
    if links:
        st.write("**Profiles found:**")
        link_cols = st.columns(len(links))
        for i, (platform, url) in enumerate(links.items()):
            link_cols[i].link_button(platform, url, use_container_width=True)
        st.write("")

    # Full profile text
    with st.container():
        st.markdown(result["profile"])

    # Token cost (Haiku: $0.80/$4 per M; Sonnet: $3/$15 per M)
    inp = result.get("input_tokens")
    out = result.get("output_tokens")
    if inp and out:
        if "haiku" in selected_model:
            cost_usd = (inp * 0.80 + out * 4) / 1_000_000
        else:
            cost_usd = (inp * 3 + out * 15) / 1_000_000
        st.caption(f"Tokens: {inp:,} in / {out:,} out — est. cost: ${cost_usd:.3f}")

    # ── Feedback ──────────────────────────────────────────────────────────────

    st.divider()
    st.subheader("📝 Feedback  *(helps improve future searches)*")

    if st.session_state.fb_saved:
        st.success("Feedback saved — thank you!")
    else:
        correct = st.radio(
            "Was this the right person?",
            ["Yes — correct", "Partially — close but wrong details", "No — wrong person"],
            horizontal=True,
            index=None,
        )
        comment = st.text_input(
            "What worked or didn't?",
            placeholder="e.g. LinkedIn URL was wrong / found the right company / confused two people with similar names",
        )
        if st.button("Save feedback", disabled=(correct is None)):
            fb_value = {"Yes — correct": "yes", "Partially — close but wrong details": "partial",
                        "No — wrong person": "no"}[correct]
            log_feedback(st.session_state.search_id, fb_value, comment)
            st.session_state.fb_saved = True
            st.rerun()
