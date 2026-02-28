# Stalker — Mac Research App

Describe someone you met. Claude searches the web and finds them.

---

## What it does

You type (or dictate via Wispr Flow) a natural language description of someone you met at an event — their name, what they do, where they work, what you talked about. Claude uses web search to find their public professional presence: LinkedIn, Twitter/X, company pages, articles, conference talks.

Every search is logged locally to `search_log.jsonl` with a feedback loop (correct / partial / wrong) so you can iterate on the prompts over time.

---

## Setup

**Requirements:** Python 3.9+, an [Anthropic API key](https://console.anthropic.com).

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```

Or enter the API key in the sidebar instead of setting the environment variable.

---

## Using it

1. Type (or dictate) a description of who you met in the text box — anything you remember: name, role, company, city, what you talked about
2. Click **Research This Person**
3. Claude searches the web for ~15–30 seconds
4. Profile appears with social links and a summary
5. Rate the result (correct / partial / wrong) — logged for future prompt improvement

**Voice input tip:** [Wispr Flow](https://www.wispr.ai) works system-wide on Mac. Activate it with your shortcut (default: hold **Fn** or **Right ⌥**), speak, and the transcription appears in the text box.

---

## Models

| Model | Speed | Est. cost/search |
|---|---|---|
| Haiku 4.5 | Fast | ~$0.13 |
| Sonnet 4.6 | Better | ~$0.50 |

Haiku is the default — good enough for most lookups. Switch to Sonnet for harder cases.

---

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI + all app logic |
| `test_api.py` | Standalone API test (no Streamlit) |
| `requirements.txt` | Python dependencies |
| `search_log.jsonl` | Local log of searches + feedback (gitignored) |

---

## Related

- `../stalker/` — iOS version (SwiftUI + SwiftData, voice input via SFSpeechRecognizer)
