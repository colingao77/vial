"""Turn this repository's GitHub Releases into a PEP 503 ("simple") package index.

Every non-draft release is scanned for wheel and sdist assets. The output is a static
site: `simple/index.html` lists the projects, `simple/<project>/index.html` lists that
project's files with `#sha256=` fragments so installers verify downloads. Asset bytes
are fetched once here to compute the hashes; the links point at the release assets
themselves, so Pages serves only HTML.

    python tools/build_index.py <owner>/<repo> <out dir>

GH_TOKEN (or GITHUB_TOKEN) is used for the API when present, which lifts the anonymous
rate limit; the assets are public and need no token.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

API = "https://api.github.com"
DIST_SUFFIXES = (".whl", ".tar.gz", ".zip")


def _api(url: str) -> tuple[object, str | None]:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        link = resp.headers.get("Link", "")
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        return json.load(resp), (nxt.group(1) if nxt else None)


def releases(repo: str) -> list[dict]:
    out: list[dict] = []
    url: str | None = f"{API}/repos/{repo}/releases?per_page=100"
    while url:
        page, url = _api(url)
        out.extend(r for r in page if not r.get("draft"))
    return out


def project_name(filename: str) -> str:
    """Normalised project name (PEP 503) from a wheel or sdist filename."""
    stem = (
        filename[: -len(".tar.gz")] if filename.endswith(".tar.gz") else filename.rsplit(".", 1)[0]
    )
    raw = stem.split("-", 1)[0]
    return re.sub(r"[-_.]+", "-", raw).lower()


def sha256_of(url: str) -> str:
    h = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=300) as resp:
        for chunk in iter(lambda: resp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(repo: str, out: Path) -> dict[str, list[tuple[str, str]]]:
    files: dict[str, list[tuple[str, str]]] = {}  # project -> [(filename, href)]
    for rel in releases(repo):
        for asset in rel.get("assets", []):
            name = asset["name"]
            if not name.endswith(DIST_SUFFIXES):
                continue
            url = asset["browser_download_url"]
            digest = sha256_of(url)
            files.setdefault(project_name(name), []).append((name, f"{url}#sha256={digest}"))
            print(f"{rel['tag_name']}: {name} sha256={digest[:12]}...", file=sys.stderr)

    simple = out / "simple"
    simple.mkdir(parents=True, exist_ok=True)
    (out / ".nojekyll").write_text("")
    head = "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    links = "".join(f"<a href='{p}/'>{html.escape(p)}</a><br>\n" for p in sorted(files))
    (simple / "index.html").write_text(
        f"{head}<meta name='pypi:repository-version' content='1.0'><title>Simple index</title>"
        f"</head><body>\n{links}</body></html>\n"
    )
    for project, entries in files.items():
        d = simple / project
        d.mkdir(exist_ok=True)
        rows = "".join(
            f"<a href='{html.escape(href, quote=True)}'>{html.escape(fname)}</a><br>\n"
            for fname, href in sorted(entries)
        )
        (d / "index.html").write_text(
            f"{head}<meta name='pypi:repository-version' content='1.0'>"
            f"<title>Links for {html.escape(project)}</title></head><body>\n"
            f"<h1>Links for {html.escape(project)}</h1>\n{rows}</body></html>\n"
        )
    (out / "index.html").write_text(
        f"{head}<title>{html.escape(repo)} package index</title></head><body>\n"
        f"<p>PEP 503 index built from the GitHub Releases of "
        f"<a href='https://github.com/{html.escape(repo)}'>{html.escape(repo)}</a>. "
        f"Use <code>simple/</code> as the index URL.</p>\n"
        f"<p><a href='simple/'>simple/</a></p>\n</body></html>\n"
    )
    return files


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    result = build(sys.argv[1], Path(sys.argv[2]))
    total = sum(len(v) for v in result.values())
    print(f"indexed {len(result)} project(s), {total} file(s) into {sys.argv[2]}", file=sys.stderr)
