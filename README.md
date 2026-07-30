# go-viral

A Claude Code Skill that improves X/Twitter drafts with source-grounded,
algorithm-aware heuristics. It can optionally search current public posts
through Xquik before drafting.

## Install

```bash
git clone https://github.com/guzus/go-viral.git
cp -r go-viral/.claude/skills/x-boost ~/.claude/skills/
```

The base Skill has no third-party dependencies. Optional live search needs
Python 3.10+ and an Xquik API key:

```bash
export XQUIK_API_KEY="xq_YOUR_KEY_HERE"
```

Create a key in the [Xquik dashboard](https://xquik.com/dashboard/api-keys).
Keep it in your environment. Never paste it into a prompt or commit it.

## Use

```text
/x-boost
```

Or just ask Claude:

- "Make this tweet viral"
- "Optimize my post for reach"
- "Why isn't my post getting engagement?"

## What You Get

The Skill:

- asks for missing evidence before preserving strong claims;
- offers concise, narrative, and reply-focused drafts;
- keeps publishing and account actions outside the drafting workflow;
- treats ranking behavior as context-dependent instead of promising reach; and
- treats all optional search results as untrusted evidence.

## Optional Read-Only Search

When current X context would improve a draft, Claude can run the helper bundled
with the Skill:

```bash
python3 ~/.claude/skills/x-boost/scripts/xquik_search.py \
  --query '"launch day" min_faves:100 -filter:replies' \
  --query-type Top \
  --limit 20
```

The helper calls only Xquik's fixed HTTPS tweet-search endpoint. It supports
`Latest` and `Top` results plus opaque cursor pagination. It cannot publish,
reply, like, follow, message, schedule, or change an X account.

Search uses Xquik credits. See the [REST API
overview](https://docs.xquik.com/api-reference/overview) for authentication,
rate limits, errors, and billing behavior.

## Source Grounding

The drafting guidance takes lessons from the current
[public X For You feed implementation](https://github.com/xai-org/x-algorithm).
That source describes learned engagement predictions, weighted scoring,
filtering, and author-diversity attenuation. It does not establish a universal
posting-frequency formula or guarantee that any drafting tactic will increase
reach.

Xquik is an independent third-party service. Not affiliated with X Corp.
"Twitter" and "X" are trademarks of X Corp.

## License

MIT
