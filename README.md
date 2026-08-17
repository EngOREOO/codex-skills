# codex-skills

Portable export of the local Codex skills and plugin sources used by EngOREOO.

## Install in another Codex

The recommended path installs the merged `codex-skills` bundle through Codex's local marketplace support:

```bash
git clone https://github.com/EngOREOO/codex-skills.git
cd codex-skills
./install.sh
```

To install the separately packaged plugins as well:

```bash
./install.sh --all
```

The manual equivalent is:

```bash
codex plugin marketplace add https://github.com/EngOREOO/codex-skills.git
codex plugin add codex-skills@codex-skills
```

Restart Codex after installation. Use `codex plugin list` to verify the installed plugins.

## What's included

- `codex-skills`: the merged portable bundle of 297 canonical skills.
- `arabic-rtl-ui`, `backend-architect`, `devops-automator`, `filament-*`, and `senior-developer`.
- `humane-commit-flow` for guarded commits and authorized pushes.
- `codex-rtl`, a macOS-specific Codex desktop RTL utility; install it only when you intend to use that patch.
- `mem0` and `mem0-memory`; the full Mem0 plugin requires a `MEM0_API_KEY` and is not installed by the default command.
- `AUTHORIZATION.md`, an intentionally inactive scope-file template; `urgent-let-gaurd` requires a valid project-root copy before project-specific work.

The canonical bundle merges `~/.agents/skills` first and adds unique skills from `~/.codex/skills`. Supporting references and assets are kept with their skills.

## Export boundaries

Official OpenAI/vendor marketplace caches, dependency directories, nested Git repositories, Python bytecode, and the unrelated ChiledSafty evaluation files are intentionally excluded. Vendor plugins should be installed from their original marketplace when available.

Some included skills cover authorized security research. Review any skill before use and run security testing only against systems you own or are explicitly authorized to assess. Source files may have different upstream licenses; preserve their notices when redistributing or modifying them.
