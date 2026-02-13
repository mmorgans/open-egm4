# Release Process

This project uses tag-based releases with `setuptools_scm`.

## Overview

- CI runs on every push and pull request.
- Release builds run when you push a tag matching `v*` (for example, `v1.3.0`).
- A GitHub Release is created automatically with generated notes and attached build artifacts.

## Maintainer Checklist

1. Ensure local changes are committed.
2. Merge into `main`.
3. Confirm CI is green on `main`.
4. Create and push tag:
   ```bash
   git checkout main
   git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. Verify the `Release` workflow completed successfully.
6. Review generated release notes on GitHub.

## Workflows

- CI workflow: `.github/workflows/ci.yml`
- Release workflow: `.github/workflows/release.yml`

## Versioning Notes

- The package version is derived from git tags via `setuptools_scm`.
- Use semantic versioning:
  - `vMAJOR.MINOR.PATCH`
