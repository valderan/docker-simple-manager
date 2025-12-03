# Releasing Docker Simple Manager

## Prerequisites

- Ensure `uv` is installed and the development environment is configured (`uv pip install -e ".[dev]"`).
- Docker Engine (or Docker Desktop) must be available for smoke tests.
- On macOS, install required build tools (Xcode Command Line Tools) and ensure PyInstaller is able to codesign if needed.

## Release Checklist

1. **Update version**
   - Increment `version` in `pyproject.toml`.
   - Update badges/links if necessary.
2. **Documentation**
   - Review `README.md` / `README_en.md`.
   - Update `CHANGELOG.md` with the new release section.
3. **Quality gates**
   ```bash
   make lint
   make typecheck
   make test
   ```
4. **Smoke test GUI**
   - Launch `uv run docker-simple-manager`.
   - Verify at least one local connection and basic actions (refresh, logs, dialogs).
5. **Build binaries**
   ```bash
   make build-linux            # produces dist/dsm-linux/dsm
   # On macOS host:
   DSM_MAC_ARCH=universal2 make build-macos
   ```
   - Optionally build per-arch binaries: `DSM_MAC_ARCH=arm64 make build-macos`.
6. **Verify artifacts**
   - Run the built binaries (`dist/dsm-linux/dsm`, `dist/dist-macos/dsm`) and ensure they start without errors.
   - Compress output folders for distribution (e.g., `tar.gz` for Linux, `.zip`/`.dmg` for macOS).
7. **Clean workspace**
   ```bash
   make dist-clean
   ```
8. **Git commit & tag**
   - Commit changes with message `Release vx.y.z`.
   - Create annotated tag: `git tag -a vx.y.z -m "Release vx.y.z"`.
9. **Publish**
   - Push commits and tags to GitHub.
   - Create a GitHub Release, attach binaries, include changelog notes.

## Notes

- PyInstaller may warn about missing system libraries (e.g., `libtiff.so.5`); document required packages in release notes.
- For notarized macOS builds, additional codesigning/notarization steps are required (not yet automated).
