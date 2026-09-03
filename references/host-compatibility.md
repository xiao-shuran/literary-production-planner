# Agent Host Compatibility

This Skill is designed to be portable across Agent hosts. The portable contract is deliberately small:

```text
literary-production-planner/
├── SKILL.md                 # required instruction entrypoint
├── references/              # relative guides selected by SKILL.md
├── scripts/                 # optional standard-library repair tools
└── recovery/                # optional integrity baseline used by the tools
```

Keep this directory structure unchanged. A host may install the directory in a different parent folder, but it should load the same `SKILL.md` and keep its relative siblings available. Do not copy the core instructions into several vendor-specific files: duplicated copies drift and can produce different planning behavior.

The package follows the common Agent Skills shape: a directory whose entrypoint is a UTF-8 `SKILL.md` with YAML frontmatter containing `name` and `description`. The host's discovery path and invocation syntax are host concerns; they do not change the adaptation rules.

Compatibility here means **portable source and behavior**, not a claim that every host exposes identical APIs. A host that supports the common directory-and-`SKILL.md` convention can use this package unchanged. A host with a proprietary registry may need a small local registration pointing at the same directory.

## Host-Neutral Rules

- The only required skill metadata is YAML frontmatter with `name` and `description` in `SKILL.md`.
- `agents/openai.yaml` is optional Codex UI metadata. Claude Code, OpenClaw, and other hosts may ignore it.
- `README.md`, `PORTABILITY.md`, and this guide are documentation, not additional instruction entrypoints.
- `references/` files are loaded only when relevant. If a host cannot follow relative links automatically, make the relevant files available as additional context without changing `SKILL.md`.
- The Python repair tools are maintenance utilities, not host plugins. They do not call an Agent API, use a vendor SDK, or require a particular shell.
- Host discovery and invocation are separate from literary adaptation. A host may expose the Skill as a slash command, a named skill, an auto-loaded directory, or a project instruction; the generated plan should be the same once `SKILL.md` is loaded.

The compatibility boundary is therefore explicit:

| Layer | Shared across hosts | Host-specific |
| --- | --- | --- |
| Skill behavior | `SKILL.md` and the relative `references/` rules | Nothing |
| Optional maintenance | Python repair scripts and `recovery/` baseline | Which terminal or task runner invokes them |
| Discovery | The directory and `SKILL.md` entrypoint | Parent skills directory and invocation syntax |
| UI metadata | None required | `agents/openai.yaml` is useful to Codex and ignorable elsewhere |

## Codex

Install the complete directory under a Codex skills root. Depending on whether the skill is user-wide or project-local, common locations are:

```text
$CODEX_HOME/skills/literary-production-planner/
<project>/.agents/skills/literary-production-planner/
```

When `CODEX_HOME` is unset, the user-level default is commonly `~/.codex/skills/literary-production-planner/`. Use the Codex host's normal skill invocation surface, for example `$literary-production-planner` where supported. Keep `agents/openai.yaml` if Codex UI metadata is desired; it is not needed for the planning logic or repair tools.

## Claude Code (CC)

Install the same directory in the Claude Code project skill location or user-level skill location documented by the host, commonly:

```text
<project>/.claude/skills/literary-production-planner/
~/.claude/skills/literary-production-planner/
```

Use the host's normal skill discovery or slash-command surface. Do not create a second `CLAUDE.md` copy of `SKILL.md`; project instructions can mention the skill, but the canonical entrypoint remains `SKILL.md`. The optional `agents/openai.yaml` file may be left in place or ignored.

## OpenClaw

Install the complete directory in the OpenClaw workspace or configured skills directory. A workspace-level layout commonly looks like:

```text
<openclaw-workspace>/skills/literary-production-planner/
```

Use the OpenClaw configuration or skill loader to register that directory, then invoke the skill using the host's normal skill mechanism. Do not assume Codex's `$skill-name` syntax or OpenAI metadata is available in OpenClaw. The core `SKILL.md`, relative references, and standard-library repair commands remain the same.

Because OpenClaw deployments can configure their workspace and skill roots differently, the installer should use the path shown by that deployment's configuration or documentation rather than guessing a global directory. This package intentionally has no mandatory OpenClaw plugin manifest, network connector, or runtime dependency.

If an OpenClaw installation has a managed, extra, or workspace skill root, choose the configured root and place the directory directly beneath it. Do not wrap the package in another directory or rename `SKILL.md`; both can prevent discovery.

## Other Agent Hosts

For a host that follows the common Agent Skills convention, place the directory under its documented skills root and preserve `SKILL.md`. Project-local roots commonly use a `.agents/skills/<skill-name>/` shape; vendor-specific roots may use a hidden directory such as `.claude/skills/<skill-name>/`. For a host that only accepts one instruction file:

1. Load `SKILL.md` as the instruction entrypoint.
2. Provide the sibling `references/` files when the entrypoint routes to them.
3. Keep `scripts/` and `recovery/` on disk if self-integrity repair is required.
4. Ignore `agents/openai.yaml` unless that host explicitly supports it.

For hosts with a stricter manifest, create a host-local registration that points to this directory rather than editing the portable core. The registration should expose the name `literary-production-planner` and the description from the frontmatter.

## Cross-Host Acceptance Test

After installation on any host, confirm:

1. The host can discover or load `SKILL.md`.
2. A request for a literary adaptation triggers diagnosis by source type before a planning structure is chosen.
3. A fixed user template is followed without forcing every work into the same shape.
4. A user request for no narration does not receive disguised narration.
5. The relevant reference files are available through their relative paths.
6. From the skill root, `python scripts/skill_repair.py verify` reports `healthy` (or the local Python equivalent such as `python3` / `py -3`).

If a host fails only at discovery, fix the host registration or install location. Do not fork or rewrite the core Skill for that host unless its loader has a documented, unavoidable format requirement. A platform adapter should point to this directory, not duplicate its contents.
