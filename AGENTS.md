# AGENTS.md
> System-level instructions for AI coding agents working on this project.

## TL;DR
- All documentation must follow ARC (Agent-Readable Content) structure
- Run `./arc-lint.sh` before committing any .md file
- Use CCA annotations (HERE:, THIS:, KEEP:, WAIT:, ASK:, LINK:)
- Keep files under 4000 tokens

HERE: This file tells agents how to behave in this repository.
THIS: Rules that apply to ALL agent interactions, regardless of task.

---

## Core Principles

### 1. Documentation Is Attention-Optimized

LLMs have a U-shaped attention curve. We structure docs accordingly:

```
Attention Level:

HIGH  ██████████                    ██████████
      ██████████                    ██████████
      ██████████                    ██████████
MED   ██████████   ░░░░░░░░░░░░░   ██████████
      ██████████   ░░░░░░░░░░░░░   ██████████
LOW   ██████████   ░░░░░░░░░░░░░   ██████████
      ──────────────────────────────────────►
      First 20%    Middle 60%      Last 20%
      (HEADER)     (DEAD ZONE)     (FOOTER)
```

KEEP: Critical information goes in header or footer, never middle.

### 2. Every .md File Has This Structure

```markdown
# Title
> One-sentence summary (standalone)

## TL;DR
- Point 1
- Point 2
- Point 3

HERE: Context grounding.
THIS: What the file contains.

---

## Content Sections
(Use H2 every 300-500 words)

---

## Links
LINK: Related to [X](./x.md)
LINK: Depends on [Y](./y.md)
```

### 3. CCA Annotations Are Required

| Prefix | When to use |
|--------|-------------|
| `HERE:` | Start of complex blocks |
| `THIS:` | Before non-obvious code/content |
| `KEEP:` | Unusual but correct patterns |
| `WAIT:` | High-risk modification zones |
| `ASK:`  | Before making assumptions |
| `LINK:` | Non-obvious dependencies |

---

## Before Modifying Any .md File

1. Read the file's TL;DR section first
2. Check for KEEP: and WAIT: annotations
3. Preserve header structure (don't bury summaries)
4. Add LINK: annotations when creating dependencies
5. Run `./arc-lint.sh [file]` before committing

---

## Before Creating New .md Files

1. Start with TL;DR section (write it FIRST)
2. Add HERE: and THIS: in header
3. Add LINK: section in footer
4. Keep under 4000 tokens
5. Update llms.txt with new file

---

## File Size Constraints

| Limit | Value | Reason |
|-------|-------|--------|
| Max file | 4000 tokens | Retrieval chunk size |
| Max section | 800 words | Sub-chunk addressable |
| Max sentence | 20 words | Parsing accuracy |
| Header block | 150 words | Survives truncation |

WAIT: Files over 4000 tokens should be split.
The agent may not see full content of large files.

---

## Validation Commands

```bash
# Lint single file
./arc-lint.sh docs/file.md

# Lint all docs
./arc-lint.sh docs/

# Generate llms.txt index
./arc-lint.sh --generate-llms

# Check before commit (add to pre-commit hook)
./arc-lint.sh docs/ || exit 1
```

---

## This Repository's Structure

```
project/
├── AGENTS.md              ← You are here
├── llms.txt               ← Index for agents
├── arc-lint.sh            ← Validation tool
├── .windsurf/
│   └── rules/
│       └── agent-readable-docs.mdc
└── docs/
    └── *.md               ← All docs follow ARC
```

---

## Links

LINK: See [.windsurf/rules/agent-readable-docs.mdc](./.windsurf/rules/agent-readable-docs.mdc) for full rule specification
LINK: Run [arc-lint.sh](./arc-lint.sh) to validate compliance
LINK: Reference [llms.txt](./llms.txt) for documentation index

## Metadata

- Standard: ARC v1.0 (Agent-Readable Content)
- Based on: "Lost in the Middle" (Liu et al., 2023)
- Applies to: All .md files in repository
