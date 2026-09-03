# Portability Contract

This directory is designed as a portable Agent Skill. Its canonical behavior is defined by `SKILL.md`; the other Markdown files are relative references that the entrypoint selects as needed.

The target hosts include Codex, Claude Code (CC), OpenClaw, and other agents that can load a directory-based `SKILL.md` skill. Discovery paths and command syntax are host-specific; the Skill content is not duplicated per host.

## What Is Portable

- `SKILL.md` uses YAML frontmatter and plain UTF-8 Markdown, with no required proprietary tool call, shell, absolute path, or operating-system-specific command.
- Reference links are relative to the skill directory.
- `scripts/skill_repair.py` and `scripts/build_recovery_baseline.py` use only the Python standard library and run on Python 3.8 or later on Windows, macOS, and Linux.
- `agents/openai.yaml` is optional integration metadata for Codex-compatible hosts. It is not required by the core skill and can be ignored by hosts that do not recognize it.
- The repair commands are host-neutral; invoke them with the local Python 3 executable (`python`, `python3`, or `py -3`).
- The recovery baseline has an explicit managed-file scope: the five shipped root files plus files under `agents/`, `references/`, and `scripts/`. Unknown additions are not restored, deleted, or overwritten.
- The shipped root-file scope includes `.gitattributes`, `.gitignore`, `README.md`, `PORTABILITY.md`, and `SKILL.md`, plus files under `agents/`, `references/`, and `scripts/`.
- The package follows the common Agent Skills layout: one directory, one canonical `SKILL.md` entrypoint, and sibling resources referenced by relative path. Host-specific registration should point to this directory instead of duplicating `SKILL.md`.

## Host Integration

1. Preserve the top-level `literary-production-planner` directory and its internal paths.
2. Install that directory in the host's documented skills location, or attach `SKILL.md` as the skill instruction file when the host uses a project-local skills convention.
3. Keep the `references/`, `scripts/`, and `recovery/` directories alongside `SKILL.md`; relative links and integrity repair depend on them.
4. If a host does not discover skills automatically, reference `SKILL.md` explicitly in that host's agent configuration or project instructions.

No platform is assumed to run the repair command automatically. A user or agent with filesystem permission invokes it when integrity needs to be checked.

## Integrity Scope

The recovery baseline owns the Skill's shipped instructions, reference guides, scripts, and optional metadata. It never treats literary inputs, user-created plans, output documents, project files, or unknown files placed beside the Skill as repair targets.

For repair commands and trust boundaries, read [references/portability-and-recovery.md](references/portability-and-recovery.md).

For Codex, Claude Code, OpenClaw, and other Agent host installation mappings, read [references/host-compatibility.md](references/host-compatibility.md).
