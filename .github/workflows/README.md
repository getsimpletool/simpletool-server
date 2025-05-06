# GitHub Actions Workflows Structure

This directory contains all CI/CD workflows for the SimpleToolServer project.

## Main Workflows

- `ci.yml`: Runs tests on every push to `src/`.
- `release.yml`: Runs tests and, if successful, builds and pushes a Docker image on every published release. Uses reusable subflows for modularity.

## Reusable Subflows

<<<<<<< HEAD
Reusable workflows are stored alongside the main workflow files in `.github/workflows/` and are intended to be used as building blocks by main workflows
=======

Reusable workflows are stored alongside the main workflow files in `.github/workflows/` and are intended to be used as building blocks by main workflows.
>>>>>>> d0488d8 (v0.1.2)

- `reusable-test.yml`: Runs all server tests (Python + Node). No inputs required.
- `reusable-build-docker.yml`: Builds and optionally pushes the Docker image to GHCR. Requires three inputs:
  - `release_tag` (string, required): The Docker image version/tag (e.g., `v0.1.1`).
  - `release_tag_latest` (boolean, required): If `true`, also tags/pushes the image as `latest`.
  - `push_image` (boolean, optional, default: false): If `true`, pushes the image to the registry. If `false`, only builds locally.

### Usage Examples

**In a workflow job:**

```yaml
jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml


  build-docker:
    needs: test
    if: ${{ needs.test.result == 'success' }}
<<<<<<< HEAD
    uses: ./.github/workflows/reusable-build-docker.yml
=======
    uses: ./.github/workflows/reusable-build-docker.yml
>>>>>>> d0488d8 (v0.1.2)
    with:
      release_tag: ${{ github.event.release.tag_name }}
      release_tag_latest: true
      push_image: true
```

## Conventions

- Main workflows are in the root of `.github/workflows/`.
- Each reusable workflow has a header comment describing its purpose, inputs, and usage.

---

For more details, see the comments at the top of each workflow file.
