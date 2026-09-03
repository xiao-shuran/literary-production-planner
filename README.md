# Literary Production Planner

A portable Agent Skill for turning literature into practical performance and production plans. It supports stage productions, short videos, audio work, classroom presentations, and competitions.

## Supported Agent Hosts

The package uses one canonical `SKILL.md` entrypoint and is intended for:

| Host | Typical discovery location | Invocation |
| --- | --- | --- |
| Codex | `$CODEX_HOME/skills/` or project `.agents/skills/` | The host's named-skill surface, such as `$literary-production-planner` |
| Claude Code (CC) | Project `.claude/skills/` or the host's user skill directory | The host's normal skill or slash-command surface |
| OpenClaw | The configured workspace or global skills root | The host's configured skill loader or command |
| Other Agent hosts | Their documented skills root, or a project-local skill directory | Their native skill mechanism or explicit `SKILL.md` loading |

The paths above are discovery examples, not hard-coded requirements. The host's own configuration takes precedence. The contents of the Skill remain the same after installation; only discovery and invocation differ.

The skill does not impose a fixed planning-book template. It asks for, and follows, the user's own required headings, order, table layout, and submission constraints. When no structure has been supplied, it can propose a structure for approval.

## What It Handles

- Adapts a literary work, excerpt, or reliable synopsis into an executable plan.
- Diagnoses the source's form and narrative engine before selecting the adaptation's form, scene architecture, narration density, and visual language; it does not force every work into the same short-video pattern.
- Selects one of three script approaches: dialogue-only, narration-led, or hybrid.
- Keeps narration optional: when the user requests no narration, it does not substitute voice-over, host links, or other disguised narration.
- Produces character-labelled dialogue, scene/shot plans, staging notes, and optional narration appropriate to the chosen medium.
- Designs a recurring visual-motif system, an emotional rhythm curve, and a clear narrative or expressive value for each retained shot.
- Reviews a plan or completed cut for adaptation fidelity, pacing, motif development, shot redundancy, performance, sound, visual continuity, and delivery readiness.
- Preserves the source work's key relationships, conflicts, turning points, theme, and ending unless the requested adaptation intentionally changes them.
- Uses a standard-library Python integrity tool to verify and repair this Skill's own managed files from a packaged recovery baseline.

## Install

The portable entrypoint is `SKILL.md`. Put the complete `literary-production-planner` directory in the skill-discovery location documented by the agent host, retaining its folder structure and relative paths.

For Codex, the usual location is:

```text
~/.codex/skills/literary-production-planner/
```

Hosts that support the common Agent Skills convention can use the same directory unchanged. Hosts without native skill discovery can place the directory in the project and load `SKILL.md` as agent context. The optional `agents/openai.yaml` file provides Codex UI metadata only; other platforms may ignore it. See [PORTABILITY.md](PORTABILITY.md) for the compatibility contract.

For host-specific guidance, see [references/host-compatibility.md](references/host-compatibility.md). The same core directory is intended for Codex, Claude Code (CC), OpenClaw, and other hosts that can load a `SKILL.md` entrypoint; only the parent install location and invocation surface change.

Do not rename the directory's `SKILL.md`, create a separate platform copy, or assume that Codex's `$skill-name` invocation syntax works in another host. Register the directory using the host's own skill mechanism.

## Use

Invoke it explicitly, or describe a request that clearly calls for literary adaptation:

```text
Use $literary-production-planner to adapt [work or excerpt] into a 10-minute stage plan.
Use these exact headings: [headings]. There are four actors. Do not use narration.
```

For narration-led work, state it directly:

```text
Use $literary-production-planner to create a short-video plan from [work].
Include polished narration and dialogue; use this planning structure: [headings].
```

## Verify Or Repair The Skill

These commands repair the Skill's own managed instructions, references, scripts, and optional host metadata. They do not inspect or modify literary source files, user projects, or generated plans.

Run from the skill directory with any Python 3 installation:

```text
python scripts/skill_repair.py verify
python scripts/skill_repair.py repair
```

On systems where the executable is named differently, use `python3` (macOS/Linux) or `py -3` (Windows) in the same commands.

`verify` checks the installed files against the packaged baseline. `repair` first validates that baseline, creates a timestamped backup under `recovery/backups/`, and restores only missing or modified managed files. Files not owned by the Skill are left untouched.

When `--source` is used, the source directory must itself match its recovery baseline; a second damaged copy cannot be used as a trusted repair source. Successful repairs include a post-repair integrity check.

If the repair baseline or the local repair script is itself damaged, use a clean copy from a trusted release or Git checkout:

```text
python /path/to/clean-skill/scripts/skill_repair.py repair --target /path/to/damaged-skill --source /path/to/clean-skill
```

Do not rebuild `recovery/baseline.zip` from a suspected damaged installation. When the entire local recovery chain is untrusted, restore from a trusted release archive, a verified Git commit, or another known-clean copy. See [the detailed recovery guide](references/portability-and-recovery.md).

## Repository Layout

```text
literary-production-planner/
├── SKILL.md
├── .gitattributes
├── .gitignore
├── PORTABILITY.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── skill_repair.py
│   └── build_recovery_baseline.py
├── recovery/
│   ├── baseline.zip
│   └── baseline.sha256
└── references/
    ├── portability-and-recovery.md
    ├── host-compatibility.md
    ├── narration.md
    ├── production-design.md
    ├── narrative-routing.md
    ├── visual-language.md
    └── final-quality-review.md
```

`SKILL.md` is the entrypoint. The reference files are loaded only when narration, medium-specific production guidance, visual language, final quality review, or self-recovery guidance is needed.

The recovery baseline manages only the shipped Skill files under the paths shown above. Unknown files and user additions placed beside the Skill are deliberately left untouched.
