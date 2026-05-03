# Python Dependency Single Source of Truth

The Python dependency source of truth for the current repository has been consolidated into the root [`pyproject.toml`](/home/wxyhgk/tmp/Code/pyproject.toml).

## How to Maintain Now

- Runtime dependencies:
  `project.dependencies`
- Test dependencies:
  `project.optional-dependencies.test`
- Python version:
  `project.requires-python`
- Non-Python binary dependencies:
  `tool.retain_pdf.external-binaries`

Do not directly hand-edit these generated artifacts:

- [`docker/requirements-app.txt`](/home/wxyhgk/tmp/Code/docker/requirements-app.txt)
- [`docker/requirements-test.txt`](/home/wxyhgk/tmp/Code/docker/requirements-test.txt)
- [`desktop/requirements-desktop-posix.txt`](/home/wxyhgk/tmp/Code/desktop/requirements-desktop-posix.txt)
- [`desktop/requirements-desktop-windows.txt`](/home/wxyhgk/tmp/Code/desktop/requirements-desktop-windows.txt)
- [`desktop/requirements-desktop-macos.txt`](/home/wxyhgk/tmp/Code/desktop/requirements-desktop-macos.txt)

## Update Method

After modifying [`pyproject.toml`](/home/wxyhgk/tmp/Code/pyproject.toml), execute:

```bash
python backend/scripts/devtools/sync_python_requirements.py --repo-root .
```

If you only want to check for drift:

```bash
python backend/scripts/devtools/sync_python_requirements.py --repo-root . --check
```

## Current Scope

Runtime Python packages:

- `Pillow`
- `PyMuPDF`
- `pikepdf`
- `requests`
- `urllib3`

Additional test packages:

- `pytest`

Non-Python binary dependencies:

- `typst`: Required
- `gs`: Optional compression path dependency

## Why This Approach

Previously, Docker, desktop, and CI each maintained their own requirements, which easily led to:

- Missing packages on certain platforms
- Version drift between runtime and desktop packaging
- CI passing but local or release builds failing

The current goal is:

- Change in one place
- Generate in multiple places
- CI uses `--check` to prevent drift from entering the mainline
