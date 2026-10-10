# Model routing

One strong model can do every job. It is also the most expensive way to rename forty files or to find out whether a button is centered. This page is the routing I settled on after a year of daily work, and the reasons behind each line.

## The table

| Work | Model | Effort |
|---|---|---|
| Base: code, brand voice, plans, decisions, synthesis | Opus 5 | high. Extra high by hand, only for the truly hard |
| Light: conversation, status, research, cleanups, scans | Sonnet 5 | low |
| Background: cron jobs, collectors, bots | Sonnet 5 or Haiku | default |
| Mechanical: renames, formatting, bulk edits, summaries of long files, scraping, list building | Haiku subagent | default |
| Visual escalation: a layout that failed twice on the base model | Fable 5 | default |
| Code review | Codex, outside Claude | default |
| Images, video, audio, PDF | Gemini, outside Claude | default |

## Rules behind the table

**Pick the model at the start of a session, never in the middle.** The prompt cache is bound to the model. Switching mid-session invalidates tools, system prompt and the whole history, and all of it is paid again at full price. I split sessions by mode instead: one for building, one for a visual loop, one for light talk.

**Delegate reading, keep deciding.** The reading half of preparation goes to a read-only subagent: where things live, what calls what, which files are dead. Its reading never enters the main context, only its conclusion does. The deciding half stays in the main loop: architecture, trade-offs, order of work.

**A subagent's conclusion is input, not a verdict.** Anything it calls dead or unused gets checked before I act on it.

**Do not spawn a subagent for a few tool calls, and never for verification.** A fresh agent knows only what the brief says. A check I can run inline is cheaper and more exact.

**Verification is moved out, not skipped.**

- Code and diffs go to Codex: `cat diff | codex exec --skip-git-repo-check "<prompt>"`. The diff carries no imports, so the prompt has to give context, or the review reports names it cannot see.
- Screenshots, video and PDFs go to Gemini through one wrapper script, [tools/gemini_video.py](../tools/gemini_video.py).
- Neither of them spends the Claude limits, so the review is independent in two senses: a different model and a different budget.

**Brand voice never leaves the main model.** Copy is calibrated in rule files that only the main loop loads. Sending a draft to another model for polish returns it smooth and generic. One reviewer skill is the only gate for text.

## Cheapest path to the same result

Quality is not traded. These rules apply only where two routes give the same result.

| Instead of | Do | Why |
|---|---|---|
| Looking at an image to judge layout | Measure with code: pixels, boxes, colors, proportions printed as numbers | An image costs about 40,000 tokens per look. Six numbers cost about 200 |
| Reading the same screenshot twice | Downscale to 768 px, read once, or build one contact sheet instead of many reads | An image that was read stays in context and is resent every turn |
| Letting install, build and test logs into context | A hook trims them to error lines plus the last 30 lines. See [hooks/trim-noisy-bash](../hooks/trim-noisy-bash) | Most of a build log is noise the model pays to reread |
| Other loud output | Write to a file, then `grep` or `tail` | Same reason |
| Compacting a long session to save tokens | Clear between tasks | Compaction pays to reread and loses detail |
| A long visual iteration loop in the main session | A separate session per wave | Parallel sessions share one bank of limits, so the price is named before the second heavy one starts |

## Naming the price first

Before a large task the agent writes four lines and waits for a nod:

```
Task:     what exactly I am doing
Price:    about N input tokens, about N turns
Cheaper:  route X (Gemini, code measurement, separate session), or "none"
Quality:  does not suffer / suffers here
```

Small and medium tasks do not get this ceremony. The same goes for anything that calls a paid API or changes an external system: the agent names what will be called and what it costs, and waits. An external call is treated like a deploy.
