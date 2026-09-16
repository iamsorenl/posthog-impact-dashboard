#!/usr/bin/env python3
"""Inline data.json into the template -> index.html (single self-contained file)."""
import json, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = open(os.path.join(R, "data.json")).read()
tpl = open(os.path.join(R, "scripts", "index.template.html")).read()
assert "__DATA__" in tpl
# guard against breaking out of the <script> element
safe = data.replace("</", "<\\/")
html = tpl.replace("__DATA__", safe)
out = os.path.join(R, "index.html")
open(out, "w").write(html)
n = len(EN := json.loads(data)["engineers"])
# mirror into public/ so Netlify can publish just the page, not the whole tree
pub = os.path.join(R, "public")
os.makedirs(pub, exist_ok=True)
open(os.path.join(pub, "index.html"), "w").write(html)
print(f"index.html {os.path.getsize(out)/1024:.0f} KB, {n} engineers inlined (also -> public/)")
