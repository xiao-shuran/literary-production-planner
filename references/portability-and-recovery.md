# Portability And Self-Recovery Guide

Use this guide when installing the Skill on another agent platform, or when a user reports that the **Skill itself** is missing, corrupted, incomplete, or unexpectedly modified.

“Another agent platform” here means another Agent host such as Codex, Claude Code, OpenClaw, or a host with a compatible skill loader. For their discovery paths and invocation surfaces, read [the host compatibility guide](host-compatibility.md); this document focuses on the Skill's own integrity chain.

## Portable Core

`SKILL.md` is the portable source of behavior. It uses relative Markdown links and does not require a specific agent vendor, shell, operating system, or external package. The `agents/openai.yaml` file is optional metadata for Codex-compatible hosts; it does not define core behavior and may be ignored by other hosts.

The same directory can be registered in Codex, Claude Code, OpenClaw, or another host that understands the common `SKILL.md` convention. Host-specific discovery instructions are kept in [host-compatibility.md](host-compatibility.md); the recovery procedure below is independent of the host.

Keep the complete directory together. A host may choose a different skills location or discovery rule, but it must retain these sibling paths:

```text
SKILL.md
references/
scripts/
recovery/
```

If a host has no native Skill mechanism, load `SKILL.md` as the agent instruction entrypoint and make the sibling reference files available in the same relative structure.

## What “Repair” Means

Repair applies only to managed files shipped with this Skill: the five shipped root files, reference guides, repair scripts, and optional host metadata. It does not repair literary works, Word files, PDFs, media, user-written plans, or unrelated files in the workspace.

The packaged recovery baseline contains canonical copies and checksums. It supports accidental deletion, truncation, encoding damage, and unintended edits to managed files. It is not evidence that the files are safe against an attacker who can replace every local trust anchor together.

## Normal Recovery Flow

From the installed Skill directory, run:

```text
python scripts/skill_repair.py verify
```

Interpret the result before acting:

- `healthy`: managed files and the recovery baseline match.
- `degraded`: one or more managed files differ or are missing, but the local recovery baseline is verified and can restore them.
- `baseline invalid`: the local recovery chain cannot be trusted or used. Do not rebuild it from the damaged installation.

For a `degraded` result, run:

```text
python scripts/skill_repair.py repair
```

The script validates the baseline first, copies files it will replace to `recovery/backups/<timestamp>/`, restores only managed paths, and leaves unknown files untouched. Add `--dry-run` to preview the action or `--json` for machine-readable output.

## Emergency Recovery

If `SKILL.md`, the local repair script, the manifest, or `recovery/baseline.zip` is damaged, obtain a trusted clean release directory or verified Git checkout. Run its clean repair script against the damaged directory:

```text
python /path/to/clean-skill/scripts/skill_repair.py repair --target /path/to/damaged-skill --source /path/to/clean-skill
```

The `--source` directory must contain a verified `recovery/baseline.zip` and must itself match that baseline. The clean script validates the archive's internal manifest and the source installation before it writes the target. It replaces the target's local recovery archive and checksum with the trusted source's copies, then restores managed files.

Do not use an arbitrary download, an unknown copy from another project, or a newly generated baseline as the trusted source. Prefer a release archive you published, a verified Git tag or commit, or a clean local copy whose origin you trust.

## Rules For Agents

When asked to repair the Skill:

1. Treat repair as a maintenance operation, separate from literary adaptation.
2. Run `verify` first and report whether the baseline is trustworthy.
3. Do not overwrite files before baseline validation succeeds.
4. Do not delete unknown files, user additions, backups, or user deliverables.
5. If a target path is a directory where a managed file should be, stop and report the collision rather than deleting it.
6. If no trusted local baseline exists, ask for or use an explicitly trusted release source; do not claim recovery succeeded without one.
7. After repair, run `verify` again and report the result and backup location.

## Maintainer Rule

`scripts/build_recovery_baseline.py` creates the canonical baseline for a known-good release. Run it only after reviewing intentional Skill changes. Never run it as a repair shortcut: doing so would make a damaged version the new recovery source.
