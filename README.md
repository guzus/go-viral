# go-viral

A Claude Code skill that helps you write viral X/Twitter posts. Based on reverse-engineering the [open-source X algorithm](https://github.com/twitter/the-algorithm).

## Install

```bash
git clone https://github.com/guzus/go-viral.git
cp -r go-viral/.claude/skills/x-boost ~/.claude/skills/
```

## Use

```
/x-boost
```

Or just ask Claude:
- "Make this tweet viral"
- "Optimize my post for reach"
- "Why isn't my post getting engagement?"

## What You Get

Algorithm secrets distilled into actionable advice:

| Signal | Impact |
|--------|--------|
| Dwell time | High boost |
| Replies | High boost |
| Likes/Retweets | Boost |
| Profile clicks | Boost |
| Blocks/Mutes | Kills reach |
| Rapid posting | Decay penalty |

## How We Know This

Analyzed the actual X algorithm:
- Phoenix transformer ranking model
- 19 engagement predictions combined with weights
- Author diversity decay mechanism
- In-network vs out-of-network scoring

## License

MIT
