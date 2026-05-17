# How to Publish to PyPI

## Setup

1. **Add your PyPI token to GitHub Secrets:**
   - Go to: https://github.com/RedCiprianPater/nwo-mr/settings/secrets/actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token (starts with `pypi-`)
   - Click "Add secret"

## Publishing Methods

### Method 1: Automatic (on Release)

1. Create a new release on GitHub:
   - Go to: https://github.com/RedCiprianPater/nwo-mr/releases
   - Click "Draft a new release"
   - Choose a tag (e.g., `v0.1.0`)
   - Title: `v0.1.0 - Initial Release`
   - Add release notes
   - Click "Publish release"

2. The workflow will automatically:
   - Build the package
   - Check it with twine
   - Publish to PyPI

### Method 2: Manual (Workflow Dispatch)

1. Go to: https://github.com/RedCiprianPater/nwo-mr/actions
2. Click on "Publish to PyPI" workflow
3. Click "Run workflow"
4. Select branch (usually `main`)
5. Click "Run workflow"

## Verify Installation

After publishing, test with:

```bash
pip install nwo-mr
