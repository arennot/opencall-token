import re

path = r"C:\Users\arenn\Documents\Codex\2026-06-30\opencall-token\outputs\opencall-token\index.html"

with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Insert grant button between residency and local (after line with residency)
old = 'data-view="residency">驻留</button>\n      <button class="nav-btn" data-view="local">'
new = 'data-view="residency">驻留</button>\n      <button class="nav-btn" data-view="grant">资助</button>\n      <button class="nav-btn" data-view="local">'

code = code.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)

print("Fixed - added grant button back")
