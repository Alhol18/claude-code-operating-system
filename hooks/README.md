# Hooks

A rule in the instruction file works until the agent is busy. A hook works every time. When I notice the agent breaking the same rule twice, the rule becomes a hook.

| File | Event | What it does |
|---|---|---|
| [trim-noisy-bash](trim-noisy-bash) | PreToolUse, Bash | Wraps install, build, test, ffmpeg and deploy commands so that only error lines and the last 30 lines reach the context. The exit code is preserved |
| [trim-output.py](trim-output.py) | called by the wrapper | The filter itself: keeps error and warning lines with their line numbers, then the tail |
| [mission_gate_sync.py](mission_gate_sync.py) | SessionStart | Compares goals (missions) with the queue of open decisions (gates). Prints a short drift report only when there is something to show. Never fails the session |
| [reaper-headless](reaper-headless) | Stop | Kills headless browser processes left spinning at high CPU after a visual check |

## Why the trim hook rewrites the command

A PostToolUse hook cannot change the output the model sees. A PreToolUse hook can change the command. So the hook wraps the command: output goes to a temp file, the filter prints the short version, and the original exit code is returned.

Commands that already limit their own output (`| tail`, `| head`, a redirect to a file) are left alone.

## Wiring

See [settings.example.json](settings.example.json). Copy the scripts to `~/.claude/hooks/`, make them executable, and merge the block into `~/.claude/settings.json` or the project's `.claude/settings.json`.
