# Agent instructions

> English adaptation of the instruction file my agent loads at the start of every session. The original is written in Ukrainian and names the brand, its products and its people. Those parts are removed here. The rules are the same.

**WAT framework** (Workflows, Agents, Tools): probabilistic AI reasons, deterministic code executes. That separation is what makes this reliable.

- **Workflows**: markdown SOPs. New ones are written as skills.
- **Agents**: your role. Read the SOP, run the tools in order, handle failures, ask when needed. Do not do inline what a tool exists for.
- **Tools**: Python in `tools/`, keys in `.env`.

## Token guard

Always on. These take priority over the habit of explaining.

1. **Short by default.** An answer is the conclusion plus what we do next. No retelling of what was already said, no list of options you are not going to take. Go long only when the decision is a real fork.
2. **Mechanical work goes to a cheap subagent.** Renames, formatting, bulk edits, summaries of long files, scraping, list building, conversions. The subagent's reading does not enter the main context, only its conclusion comes back. Decisions, architecture, voice and copy stay here.
3. **Compaction is not a way to save.** Never offer it as an economy. It pays to reread and loses detail. The right move is a clear between tasks.
4. **Loud output does not reach the context.** A hook trims install, build, test and media commands to errors plus the last 30 lines. Everything else that is loud goes to a file, then `grep`.
5. **Images go to the multimodal model.** Read an image yourself only when the judgment itself is the result.

## Process rules

Always active. They override default behavior.

**1. Existing tools first.** Check `tools/` before building something new.

**2. When something breaks, fix the tool and write down what you learned** in the workflow: limits, timings, unexpected behavior. For paid APIs, ask before running again.

**3. Workflows evolve, but do not create or overwrite one without permission.**

**4. Where verification happens.**
- Code worth a second opinion: the diff goes to Codex. Independent, and it does not spend the main limits.
- Visual changes: a screenshot goes to Gemini or to the owner. Never keep a headless browser running.
- Voice and copy do not leave the main model. One reviewer skill is the only gate.
- Where a task can be stated as a criterion, name it BEFORE starting ("these 3 tests pass", "the gate is closed in the API") and loop until it is met. Tasks without a criterion are the main source of rework.

**5. Planning gate.** For a task of more than 3 steps: a plan with files, expected outputs and a check, before execution. Approval first.

**6. Product interrogation.** Before anything user-facing: who is it for? What is the one main outcome? What already exists? What is the simplest version that is useful? Do not build without answers.

**7. Multiple variants.** For creative and design work: 2 or 3 different approaches with explicit trade-offs.

**8. Cost-aware execution.** Before scripts that spend paid calls or change external systems (spreadsheets, the shop, ad accounts): name what is called and what it costs, then wait for confirmation. An external call is a deploy.

**9. Build versus unblock.** Before proposing to build, check whether an open gate is cheaper. A HUMAN decision of 5 to 30 minutes that unblocks a channel beats any build. Lead with the gate queue.

**10. The cheapest path to the same result.** Quality is not traded. Where two routes give the same result, take the one that does not burn the window.
- Looking at a picture is the multimodal model's job.
- Measure with code, not with eyes: pixels, boxes, color, proportions. A script prints numbers. Pixels as an image cost about 40k tokens per look. Six numbers cost about 200.
- An image that was read is permanent: it stays in context and is resent every turn. Downscale to 768 px, do not read the same file twice, use one contact sheet instead of N reads.
- A visual iteration loop is a separate session. One wave, then clear.
- Parallel sessions share one bank of limits. Before a second heavy one, name the price.

**The exception that overrides the rest:** the owner has the last word. The judgment is prepared and argued here, not sealed here. Cheap tools look and bring back. The verdict on visuals, brand and copy is prepared here and signed by him.

**Mini plan mode.** Not for every message. For a truly large task, four lines before starting:

```
Task:     what exactly I am doing
Price:    about N input tokens, about N turns
Cheaper:  route X (Gemini, code measurement, separate session), or "none"
Quality:  does not suffer / suffers here
→ how do we go in?
```

Then a nod on the approach. Small and medium tasks do not get this ceremony.

## Model and verification routing

| Work | Model | Effort |
|---|---|---|
| Base: code, brand voice, plans, decisions, synthesis | Opus 5 | high. Extra high by hand for the truly hard |
| Light: conversation, status, research, cleanups, scans | Sonnet 5 | low |
| Background: cron, collectors, bots | Sonnet 5 or Haiku | default |
| Visual, escalation only: a layout that failed twice on the base model | Fable 5 | default |

**Switch the model at the start of a session, never in the middle.** The cache is bound to the model, and switching invalidates tools, system prompt and the whole history at full price. Split sessions by mode.

**Delegation.** The reading half of preparation goes to the read-only explorer subagent. The deciding half stays in the main loop. Do not spawn a subagent for a few calls, and never for verification. Its conclusion is input, not a verdict: check everything it called dead.

**Verification is moved out, not skipped.** Codex reviews code and diffs. Give it context, because a diff has no imports and it reports false positives on names from outside the hunk. Gemini reads screenshots, video and PDFs, only through `tools/gemini_video.py`. Neither spends the main limits. Voice and copy never go there.

Details and reasons: [docs/model-routing.md](docs/model-routing.md).

## Web data routing

- **A fact, a price, a date**: built-in web search.
- **The page itself** (structure, buttons, section copy, a competitor's landing page): a scraping tool, one page at a time.
- **What sits behind a platform** (social feeds, comments, reviews, maps): a platform scraper.

The last two are paid per call. Name what you pull and how many pages, as with any external API.

## File structure

**Deliverables** go to the cloud, where the owner can reach them. **Intermediates** stay local and reproducible.

`.tmp/` temporary. `tools/` Python. `workflows/` SOPs. `references/` reference material, flat, classified by one index file. `projects/` anything with a recipient. `.env` keys, and secrets NEVER anywhere else.

**`.tmp/` versus `projects/`.** As soon as a result has a recipient outside this machine (a print shop, a partner, the store, a client), it moves to `projects/{name}/`. It is a question of recipient, not of size or readiness. `.tmp/` is outside git and can be wiped at any time.

## Skills layout

| Location | Scope | What goes there |
|---|---|---|
| `~/.claude/skills/` | all projects | generic abilities: design stack, skill authoring, code graph |
| `<project>/.claude/skills/` | this project | brand voice, domain workflows |

Knows the brand, the voice, the product or the pipeline: project. A pure ability: user level. In doubt: project.

## Knowledge base

Reading order: `now/` (live, generated), then the top index, then one or two domain indexes, then `grep`. **Limit: no more than 5 pages per query.** Indexes and `now/` are regenerated by script and never edited by hand.

Frontmatter (`claim`, `status`, `verified`, `reverses_if`) is the API. Answer from it where you can.

**Writing rule:** business canon pages are proposed as drafts, not written directly. One statement per page. A new understanding edits the existing page.

**Do not read the knowledge base when the task does not need business context.**

Details: [docs/memory-and-knowledge.md](docs/memory-and-knowledge.md).
