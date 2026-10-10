# Memory and knowledge

Every session starts cold. The agent does not remember yesterday. Two stores fix that, and they are kept apart on purpose.

| Store | Holds | Written by |
|---|---|---|
| Memory | How to work with me, decisions already made, where things are | The agent, during work |
| Knowledge base | What the business knows: products, customers, method, sources | Me and the agent. Canon pages only with my approval |

## Memory

Claude Code keeps file-based memory per project. I use it with three rules.

**One fact per file.** Each note has a short frontmatter and one statement. Notes about how to work also carry two lines: why, and how to apply.

```markdown
---
name: verification-different-path
description: Check a result through a different source than the one that produced it
metadata:
  type: feedback
---

A check that repeats the route of the work repeats its mistakes.

**Why:** a report built from the database was "verified" against the same database.
**How to apply:** numbers from the shop API are checked against the bank export, not against the same API.
```

**The index is the only thing loaded every session.** `MEMORY.md` holds one line per note, grouped by domain: working style, voice, business state, content, ads, site, infrastructure. The agent reads the index, then opens only the notes a task needs. As of 10 October 2026 the private index points at 214 notes.

**Closed items leave the index.** Finished and frozen topics move to an archive file that is not loaded automatically.

What is not saved: anything the repository already records (code structure, past fixes, git history), and anything that matters only to the current conversation.

## Knowledge base

The knowledge base is an Obsidian vault of markdown pages. The risk is the opposite of forgetting: the agent reads forty pages to answer a question that needed two.

**Reading order.**

1. `now/`: a small generated layer with the current state. Rebuilt by script, never edited by hand.
2. `wiki/_index.md`: the top index.
3. One or two domain indexes, not all of them.
4. `grep` across the pages.

**A hard limit of five pages per query.**

**Frontmatter is the API.** Every page starts with `claim`, `status`, `verified` and `reverses_if`. The frontmatter of forty pages is about 5% of their bodies, so most questions are answered from frontmatter alone.

```markdown
---
claim: Bundles sell better than single items when the bundle solves one named situation
status: working-hypothesis
verified: 2026-09-14
reverses_if: Two consecutive months where single items outsell the hero bundle
---
```

**One statement per page.** A new understanding edits the existing page. It does not create a second one.

**Sources are hypotheses.** A page built from an outside source stays a hypothesis until our own data confirms it.

**Do not read the vault when the task does not need business context.** Code, execution and most copy edits do not.
