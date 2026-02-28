"""Standalone API test — no Streamlit dependency."""
import anthropic, os, re, sys

MODEL = "claude-haiku-4-5-20251001"  # Higher rate limit at Tier 1 (50k vs 30k TPM)

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

def build_prompt(narrative):
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

narrative = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else """
Met someone at an event. Works in tech, senior role, based in Bangalore.
"""

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit("ANTHROPIC_API_KEY not set")

print(f"Narrative:\n{narrative.strip()}\n")
print("Calling Claude with web search...\n")

client = anthropic.Anthropic(api_key=api_key)
message = client.messages.create(
    model=MODEL,
    max_tokens=4096,
    system=SYSTEM_PROMPT,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    messages=[{"role": "user", "content": build_prompt(narrative)}],
    extra_headers={"anthropic-beta": "web-search-2025-03-05"},
)

text = "\n".join(b.text for b in message.content if hasattr(b, "text") and b.text)
print(text)
print(f"\nTokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out")
