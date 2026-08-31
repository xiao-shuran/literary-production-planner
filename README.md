# Literary Production Planner

A reusable Codex skill for turning literature into practical performance and production plans. It supports stage productions, short videos, audio work, classroom presentations, and competitions.

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

## Install

Place the `literary-production-planner` directory in your Codex skills directory, typically:

```text
~/.codex/skills/literary-production-planner/
```

Or install the directory with a Codex skill installer that supports GitHub repository paths.

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

## Repository Layout

```text
literary-production-planner/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── narration.md
    ├── production-design.md
    ├── narrative-routing.md
    ├── visual-language.md
    └── final-quality-review.md
```

`SKILL.md` is the entrypoint. The reference files are loaded only when narration, medium-specific production guidance, visual language, or final quality review is needed.
