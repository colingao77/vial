# vial

Release channel for the `sanya` Python library. This repository holds no source code:
each [release](https://github.com/colingao77/vial/releases) carries the wheel, the
sdist and a `SHA256SUMS` file, built and published by the private `kitbag` repository
on its `sanya-v<version>` tags. The source of a version is the sdist of that release.
`releases/<tag>.sha256` on `main` records the checksums of every release; the publisher
adds that file right after creating the release.

A GitHub Pages workflow turns the releases into a PEP 503 package index:

```
https://colingao77.github.io/vial/simple
```

## Installing sanya

With uv, in the consuming project's `pyproject.toml`:

```toml
[project]
dependencies = ["sanya[web,db]>=0.1,<0.2"]      # only the extras you use

[[tool.uv.index]]
name = "vial"
url = "https://colingao77.github.io/vial/simple"
explicit = true                                  # only packages pinned to this index come from it

[tool.uv.sources]
sanya = { index = "vial" }
```

With pip:

```
pip install --extra-index-url https://colingao77.github.io/vial/simple "sanya[web,db]"
```

The index is public and carries `sha256` fragments, so no credentials are needed and
every download is verified. Versions start at 0.1.3.

## How it works

- `.github/workflows/pages-index.yml` runs on every push to `main` and deploys the
  output of `tools/build_index.py` to Pages. The publisher's `releases/<tag>.sha256`
  commit is that push. It does not run on the release event itself: Pages identifies a
  deployment by commit SHA, and a release adds no commit, so a deployment from an
  already-deployed SHA would keep serving the old index (actions/deploy-pages#383).
  For the same reason, force a rebuild by pushing a commit, not by re-running the workflow.
- `tools/build_index.py` lists the releases through the GitHub API, hashes each wheel
  and sdist, and writes `simple/index.html` plus `simple/<project>/index.html` with
  links to the release assets.

Releases are immutable: a fix is a new version, never a replaced file.
