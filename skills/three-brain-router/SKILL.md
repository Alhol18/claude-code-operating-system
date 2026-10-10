---
name: three-brain-router
description: Routes tasks across Claude (driver), Codex/GPT-5 (code review), and Gemini (multimodal). Voice-protected: copy never leaves Claude. Use for video/audio/PDF analysis, code review, or cross-model debate.
---

# Three-Brain Router

You are the orchestrator for a three-LLM stack. You stay the driver. You delegate to Codex (GPT-5) and Gemini (2.5 Pro) only when their unique strengths beat yours, never reflexively.

## When this skill triggers

A request matches one of these signals:

- File extensions: `.mp4`, `.mov`, `.wav`, `.mp3`, `.pdf` (Gemini)
- YouTube/Vimeo URLs longer than ~5 min (Gemini)
- File extensions: `.liquid`, `.py`, `.ts`, `.js`, `.json` for Flow/theme/tools (Codex review)
- Phrases: "do adversarial review", "check code", "find bugs", "is this biomechanically correct" (Codex review or fact-check)
- Explicit `/three-brain-debate` invocation (parallel consensus)

If none match, do not invoke this skill. Stay in normal Claude flow.

## Routing rules

### 1. Multimodal ingest → Gemini

**Triggers:** video, audio, PDF, image stacks, YouTube URLs.

**Use the tool, not the CLI, for any media file or media URL:**
```bash
venv/bin/python tools/gemini_video.py <file-or-url> --mode transcribe
venv/bin/python tools/gemini_video.py <file-or-url> --mode custom --prompt "..." --save out.md
```

Handles YouTube / Instagram / TikTok URLs, local files inline up to 20 MB and larger ones through the File API. Verified working on audio 2026-09-25.

**The bare CLI no longer ingests media.** As of the agentic Gemini CLI, `@file` is a file-read tool call, not an attachment: on audio it answers "I am unable to directly transcribe the provided audio file ... please provide the full transcription". Also changed: a positional prompt together with `-p` is now an error (put `@file` inside the `-p` string), and headless runs need `GEMINI_CLI_TRUST_WORKSPACE=true` or `--skip-trust`. Reserve the bare CLI for text prompts.

**Fallback when Gemini is down or quota is out** (503 "high demand" happens): transcribe locally, no API key, no Claude budget.
```bash
venv/bin/python -c "import mlx_whisper; print(mlx_whisper.transcribe('<file>', path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='en')['text'])"
```
Roughly 90 seconds for 27 minutes of audio on this machine. First run pulls a 1.6 GB model.

**YouTube gotchas (2026-09-25):** keep `yt-dlp` current or every format 403s. The caption endpoint returns HTTP 429 without cookies, so do not build on `--write-auto-subs`: pull `bestaudio` and transcribe.

**Use cases that fit:**
- Workout video frame-level analysis (extends `/workout-analyzer`)
- Brand book and source-book PDF ingestion in one pass
- Reverse-engineering competitor reels frame-by-frame
- Image library analysis (the brand photo set)
- Long audio (lectures, podcasts, voice memos) up to ~10 hours

**Do not route here:**
- PDFs already in a NotebookLM corpus → use NotebookLM, not Gemini CLI
- Trivial single-image questions Claude can answer directly

### 2. Code review → Codex

**Triggers:** `.liquid`, `.py`, `.ts`, `.js`, `theme.json`, Shopify Flow JSON, GitHub PRs.

**Use:**
```bash
codex exec --skip-git-repo-check --sandbox read-only "Do adversarial code review of file <path>. Find real bugs, edge cases, performance issues, security, accessibility. Format: HIGH / MEDIUM / LOW. No filler."
```

**Use cases that fit:**
- Shopify Liquid sections / snippets / templates
- `tools/` Python scripts before merging
- Meta Pixel Flow logic + Liquid pixel snippets (security-critical)
- Theme JSON schema changes
- API integrations

**Trigger mode:** manual, not auto-on-save. Run after a meaningful change is staged.

### 3. Copy review → existing voice pipeline (NEVER Codex/Gemini)

**Triggers:** blog posts, carousel slides, ad copy, email, landing copy, product descriptions, social captions.

**Hard rule:** never route brand copy to Codex or Gemini. Reasons (see project memory):
- Brand voice is heavily calibrated. Specific vocabulary rules, no em-dashes, no staccato fragments, plain-language imperative style. GPT/Gemini editors will smooth this into generic slop.
- Same principle as `caveman` skill: code only, never voice.

**Route to:** `/brand-reviewer` skill (which runs voice protection → humanizer pipeline).

**Exception (narrow):** factual claims about anatomy, biomechanics, peer-reviewed research, exercise science: Codex can fact-check the *claim* (not the prose) since it is neutral domain knowledge. Always point back to the primary sources in the knowledge base when applicable.

### 4. Architectural debate → explicit only

**Trigger:** user types `/three-brain-debate <question>` or explicitly asks all three models to discuss something.

**Mechanism:** ask the same structured question to Claude (you), Codex, Gemini, then synthesize their differing answers and present a verdict.

**Do not auto-trigger.** Token cost and time are real. Use only for genuine architectural forks (e.g. Pinecone vs pgvector, SEO stack choice, content strategy pivots).

## Hard rules (apply always)

1. **No self-loop:** if Claude attempts a task and fails once with the same error, hand off: do not retry. Codex for code, Gemini for multimodal.
2. **No voice contamination:** copy review never leaves the existing voice pipeline. This is non-negotiable.
3. **Cost-aware Gemini:** before sending video > 30 min or PDF > 100 pages, briefly state estimated impact (free tier = 50 pro requests/day) and proceed unless the user has objected.
4. **Codex sandbox:** always invoke Codex with `--sandbox read-only` for review tasks. Codex must not write or execute.
5. **Surface findings, do not auto-apply:** when Codex returns a review, present findings ranked HIGH/MEDIUM/LOW. Do not mass-edit the file. Wait for user direction or apply only the obvious HIGH-severity fixes after stating intent.

## Standard invocation patterns

### Quick Codex review
```bash
codex exec --skip-git-repo-check --sandbox read-only "<prompt>"
```

### Quick Gemini headless
```bash
gemini --skip-trust -p "<prompt>"
```

### Any media, local or URL (the only supported path)
```bash
venv/bin/python tools/gemini_video.py <file-or-url> --mode transcribe --save .tmp/out.md
```
Modes: `transcribe`, `form-check`, `custom --prompt "..."`. Do not pass media to the bare `gemini` CLI, it reads `@file` as text and refuses.

## Failure handling

- **Codex token limit reached:** state it, fall back to Claude self-review with explicit "I am going to be my own critic now" framing.
- **Gemini rate limit (free tier) or 503 "high demand":** state it, reschedule the call, do not loop-retry blindly. For transcription specifically, fall back to local mlx-whisper instead of waiting.
- **Plugin / auth broken:** drop to direct CLI invocation. Plugins are convenience layer, CLI is the contract.
- **Codex and Gemini both unavailable** (it happened: Codex quota gone for weeks, Gemini `RATE_LIMIT_EXCEEDED` the same evening). Do not skip the check silently and do not loop-retry:
  - *Probe first.* Before work whose gate is an external review, one cheap call to each (`codex exec --skip-git-repo-check "ok"`, `gemini --skip-trust -p "ok"`). A dead reviewer should be known at planning time, not at the gate.
  - *Code:* run the pure logic under `node` or `python` with real inputs, `shopify theme check` for Liquid, headless Chrome `--dump-dom` for rendered state.
  - *Visual:* measure instead of looking: DOM probes and PIL numbers. If a look is unavoidable, one contact sheet ≤1400 px, read once per wave.
  - *Say it.* The hand-off states "without independent review" and lists what was checked with which tool. Queue the diff for a real review when the quota returns.
- **Gemini reports a layout bug from a screenshot:** tell it up front what is NOT a bug (content cut by the fold of a viewport capture, lazy blocks below the fold, a video poster frame), and confirm any reported UI state in the DOM before acting on it. Layout questions are answered by DOM measurement, not by a model's eyes.

## What this skill does NOT do

- Does not pick model "for fun", only when triggered by the rules above.
- Does not run code review on every file save (manual trigger).
- Does not apply Codex/Gemini suggestions as edits without user approval.
- Does not route copy/voice/text content under any circumstance.
