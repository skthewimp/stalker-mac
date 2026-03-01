# I Came Home From a Party Not Knowing Who Anyone Was

Last weekend I was at a party - the kind where you end up in half a dozen interesting conversations and come away with a head full of fragments. Someone was pivoting careers after years in one industry. Another person was doing something vague but important-sounding in the infrastructure space. A woman mentioned she was between roles, figuring out what came next. A man talked enthusiastically about something in the health space, or maybe it was logistics - I genuinely couldn't tell. By the time I got home, all I had was a soup of first names, faces, and half-remembered details.

The obvious thing - the thing I'd done for years - is to open LinkedIn, type in what I remember, and hope for the best. Which works, sometimes. But it's slow and fiddly, and if you only caught the first name, or you're not sure if they said Bangalore or Bombay, you're already stuck.

So I built something to fix this. I'm calling it Stalker (yes, I know - but it's a personal tool, and I'm not submitting it to the App Store anytime soon).

The basic idea is simple. You open the app and describe the person the way you'd describe them to a friend - "older guy, soft-spoken, seemed very senior, said he was doing something in energy or infrastructure" or "woman in her 40s, sharp, works in strategy, mentioned Bangalore". Just talk. No dropdowns, no required fields. The app takes that natural language description, sends it to [Claude](https://anthropic.com) with web search enabled, and Claude does what you'd do if you Googled for an hour: finds their LinkedIn, their company page, their conference talks, their published articles, whatever they've chosen to make public.

It comes back in 15-30 seconds with a profile - professional summary, career background, links to their public profiles, and a confidence level (High / Medium / Low) that tells you how certain it is this is the right person.

On the Mac, I use [Wispr Flow](https://wispr.ai) to dictate the description - hold a key, speak for 30 seconds, and the transcription appears in the text box. No typing required. Just talking the way I'd describe someone over the phone.

Building this was instructive in a few ways. The first version got refused. Claude, quite reasonably, said it couldn't help identify private individuals. Fair enough - except that's not what I was trying to do. I was trying to find someone who had given me their name and told me where they work. After a networking event. Like you do. The fix was reframing the whole thing: you're a professional networking assistant, this is public professional information, this is exactly what anyone would do by Googling a new contact. That worked, and the results got noticeably better too - because framing the task correctly also changes how Claude approaches the search.

The other thing that went wrong: the app appeared to go into an infinite loop on the first real test. It wasn't actually looping - it was crashing quietly every time and re-rendering. Five minutes of reading the code and it was obvious what had gone wrong. (The lesson here is that the framework's error handling can be confusing when something fails silently inside a loading spinner - the spinner just keeps spinning rather than showing you the error.)

Every search gets logged locally - the description I typed, what it found, which social links it surfaced, how confident it was. There's a feedback widget at the bottom: was this the right person? Yes / Partially / No. The idea is to build up enough rated examples that I can improve the search prompts over time. The log stays on my machine and never goes to GitHub - it has descriptions of real people, and that's not the kind of thing that should be floating around publicly.

The code is [on GitHub](https://github.com/skthewimp/stalker-mac) if you want to use it or adapt it. You'll need an Anthropic API key - each search costs somewhere between $0.13 and $0.50 depending on which model you use. For most lookups the faster, cheaper option is fine. The slower one is there for harder cases where someone has a common name or minimal web presence.

There's an iOS version half-built too, with voice input using Apple's speech recogniser. That's for another post.
