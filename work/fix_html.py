import os

html_path = r"C:\Users\arenn\Documents\Codex\2026-06-30\opencall-token\outputs\opencall-token\index.html"

# Read the file
with open(html_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find and fix the nav section - remove duplicate grant and add it back in right place
new_lines = []
skip_grant = False
grant_seen = False
for line in lines:
    stripped = line.strip()
    # Skip duplicate grant buttons (keep only the first if we removed it, add back)
    if 'data-view="grant"' in stripped:
        if not grant_seen:
            # Insert the unique grant line
            new_lines.append(line)
            grant_seen = True
        # Skip all other grant lines
        continue
    new_lines.append(line)

with open(html_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Processed {len(lines)} lines -> {len(new_lines)} lines")
