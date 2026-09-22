# Building and publishing

Documentation lives in `docs/` in the same repository as the application. This
keeps interface changes and instructions reviewed and released together.

## Local development

```bash
python -m venv .venv
python -m pip install -e ".[all,dev,build,docs]"
python -m pytest -q
mkdocs serve
```

## Build a native application

PyInstaller builds for the operating system on which it is running:

```bash
pyinstaller --noconfirm --clean packaging/PraatFigure.spec
```

The result appears in `dist/`. The Windows installer is compiled by Inno Setup
from `packaging/windows/PraatFigure.iss`. The GitHub workflow creates macOS DMGs
and Linux AppImage and tar packages.

## GitHub Actions

- **Tests** checks Windows, macOS, and Linux on pushes and pull requests.
- **Build installers** can be started manually from the Actions tab.
- Pushing a version tag such as `v0.1.1` builds all packages and attaches them
  to the corresponding GitHub Release.
- **Documentation** builds and deploys this site when `main` documentation
  changes.

For the first Pages deployment, open **Settings → Pages** and select
**GitHub Actions** as the source. No separate `gh-pages` branch is required.

## First push

```bash
git init
git add .
git commit -m "Initial PraatFigure release"
git branch -M main
git remote add origin https://github.com/USER/REPOSITORY.git
git push -u origin main
```

To publish a version, update `pyproject.toml`, then create and push its tag:

```bash
git tag v0.1.1
git push origin v0.1.1
```

Automated packages are currently unsigned. Removing operating-system warnings
requires a Windows code-signing certificate and an Apple Developer ID with
notarization. Signing credentials must be stored as repository secrets, never
committed to source control.

