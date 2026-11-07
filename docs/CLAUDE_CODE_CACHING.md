# Claude Code prompt caching: 1-hour window

A note on changing Claude Code's prompt cache from the default 5 minutes to 1 hour. This is about Claude Code itself, not Ghost Texter. The app's Ollama calls do not use it.

## Why

Claude Code resends the whole conversation on every request: system prompt, `CLAUDE.md`, tool list, and everything said so far. Prompt caching lets the unchanged start of that request be read from a cache instead of processed again, which costs less and is faster. By default the cache expires after 5 minutes without use, so a longer pause means the whole conversation is processed again. A 1-hour window keeps the cache alive through longer pauses.

## How it was enabled

Set the environment variable in the terminal, then start Claude Code from that same terminal:

```sh
export ENABLE_PROMPT_CACHING_1H=1
claude
```

The variable only affects programs started from that terminal afterward. An already running session, including one in the VS Code extension, is not changed.

## How it was checked

A one-off request that prints the raw token breakdown:

```sh
claude -p "hello" --output-format json
```

The `usage` section of the output showed:

```json
"cache_creation": {
  "ephemeral_1h_input_tokens": 15758,
  "ephemeral_5m_input_tokens": 0
}
```

All 15,758 tokens written to the cache went to the 1-hour cache and none to the 5-minute cache. That shows the setting took effect. Without it, the same tokens would appear under `ephemeral_5m_input_tokens`.

Overall usage was also checked with `/usage` inside Claude Code.

## Not tested

- **Making it permanent.** The `export` line lasts only for that terminal. Putting it in `~/.zshrc`, or in an `env` block in `~/.claude/settings.json`, should make it permanent, but this was not tried here.
- **Cost.** Writing to a 1-hour cache is likely to cost more per token than writing to a 5-minute one, so it should pay off mainly when there are gaps of more than 5 minutes between messages. This was not measured.
- **Savings.** No before-and-after comparison of usage was made.
