# WB-0011 — Release v0.1.0-alpha.1

## Goal

Create the first explicit CyberCore development release checkpoint.

## Delivered

- versioned changelog entry;
- release notes;
- release scope and known limitations;
- tag and GitHub Release checklist.

## Verification

```bash
python -m pip install -e '.[dev]'
pytest
python -c 'import cybercore; assert cybercore.__version__ == "0.1.0a1"'
git diff --check
```

## Release procedure

After merge to `main`:

```bash
git switch main
git pull --ff-only origin main
git tag -a v0.1.0-alpha.1 -m "CyberCore v0.1.0-alpha.1"
git push origin v0.1.0-alpha.1
```

Then create a GitHub Release from the tag using
`docs/releases/v0.1.0-alpha.1.md` as the release body.

Mark it as a **pre-release**.

## Rollback

Delete the local and remote tag only if the release was created against the
wrong commit. Published release history should otherwise remain immutable.
