#!/usr/bin/env python3
"""Render the wiki/ tree into a GitHub wiki checkout.

Usage: build_wiki.py <source_dir> <out_dir>

A GitHub wiki is a flat set of <Page>.md files with no front matter and a _Sidebar.md for
navigation. For every wiki/*.md this converter:
  - strips the YAML front matter (the body already starts with the H1),
  - rewrites internal links [x](slug.md[#a]) -> [x](slug[#a]) (a wiki has no .md),
  - names the page by its slug, except index.md -> Home.md (the wiki landing page),
and then generates _Sidebar.md from the parent/has_children/nav_order tree.

The wiki page name becomes both the URL and the start of the <title> GitHub serves, so a
slug is never renamed once published: the wiki has no redirects.

Adapted from feder-cr/invisible_playwright's scripts/build_wiki.py, without the view pixels.
"""
import os
import re
import sys

DOCS = sys.argv[1]
OUT = sys.argv[2]


def parse(path):
    t = open(path, encoding="utf-8").read()
    fm, body = {}, t
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', t, re.S)
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'([A-Za-z_]+):\s*(.*?)\s*$', line)
            if mm:
                v = mm.group(2)
                if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                    v = v[1:-1]
                fm[mm.group(1)] = v
        body = m.group(2)
    return fm, body.lstrip("\n")


pages = {}
for f in sorted(os.listdir(DOCS)):
    if f.endswith(".md"):
        slug = f[:-3]
        pages[slug] = parse(os.path.join(DOCS, f))

valid = set(pages)


def rewrite(body):
    def repl(m):
        target, anchor = m.group(1), (m.group(2) or "")
        if target in valid:
            return "](" + ("Home" if target == "index" else target) + anchor + ")"
        return m.group(0)
    # The underscore is in both classes: a heading like "What jev_latest means" makes an
    # anchor with an underscore, and an anchor the pattern cannot match leaves the WHOLE link
    # unrewritten, which ships to the wiki as a dead `](slug.md#...)`.
    return re.sub(r'\]\(([a-z0-9_\-]+)\.md(#[A-Za-z0-9_\-]+)?\)', repl, body)


os.makedirs(OUT, exist_ok=True)
for slug, (fm, body) in pages.items():
    name = "Home" if slug == "index" else slug
    with open(os.path.join(OUT, name + ".md"), "w", encoding="utf-8", newline="\n") as out:
        out.write(rewrite(body) + "\n")


def title_of(slug):
    return pages[slug][0].get("title", slug)


def link(slug):
    return "[%s](%s)" % (title_of(slug), "Home" if slug == "index" else slug)


def children_of(group_title):
    kids = [(s, fm) for s, (fm, b) in pages.items() if fm.get("parent") == group_title]
    kids.sort(key=lambda x: int(x[1].get("nav_order", "999")))
    return kids


toplevel = [(s, fm) for s, (fm, b) in pages.items() if not fm.get("parent") and s != "index"]
toplevel.sort(key=lambda x: int(x[1].get("nav_order", "999")))

lines = ["### " + link("index"), ""]
for slug, fm in toplevel:
    lines.append("**%s**" % link(slug))
    for cs, cfm in children_of(title_of(slug)):
        lines.append("- %s" % link(cs))
    lines.append("")
with open(os.path.join(OUT, "_Sidebar.md"), "w", encoding="utf-8", newline="\n") as out:
    out.write("\n".join(lines) + "\n")

# A link the rewriter did not resolve reaches the wiki as a dead `.md` link, and the page
# that carries it renders fine: only the target 404s. So the build refuses instead.
dead = []
for name in os.listdir(OUT):
    text = open(os.path.join(OUT, name), encoding="utf-8").read()
    dead += ["%s -> %s" % (name, m) for m in re.findall(r'\]\(([^)h][^)]*\.md[^)]*)\)', text)]
if dead:
    raise SystemExit("unresolved internal links:\n  " + "\n  ".join(dead))

print("wrote %d pages + _Sidebar.md to %s" % (len(pages), OUT))
