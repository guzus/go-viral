# X Boost Skill for Claude Code

A Claude Code skill that helps optimize X/Twitter posts for maximum reach, based on analysis of the [open-source X recommendation algorithm](https://github.com/twitter/the-algorithm).

## Installation

Copy the `.claude/skills/x-boost` folder to your project or personal Claude directory:

```bash
# Project-level (for one repo)
cp -r .claude/skills/x-boost /path/to/your/project/.claude/skills/

# Personal (for all projects)
cp -r .claude/skills/x-boost ~/.claude/skills/
```

## Usage

Once installed, Claude Code automatically applies this skill when relevant. You can also invoke it directly:

```
/x-boost
```

**Example prompts:**
- "Optimize this tweet for engagement"
- "Why isn't my post getting reach?"
- "Write a thread about [topic] optimized for X"
- "Review my draft post"

## What's Inside

Key algorithm insights distilled into actionable advice:

| Factor | Impact |
|--------|--------|
| Dwell time | High positive |
| Replies | High positive |
| Likes/Retweets | Positive |
| Profile clicks | Positive |
| Blocks/Mutes | Heavy negative |
| Rapid posting | Decay penalty |

## Algorithm Source

Based on analysis of:
- Phoenix ranking model (transformer-based)
- Weighted scorer combining 19 engagement predictions
- Author diversity penalty mechanism
- In-network vs out-of-network scoring

## License

MIT
