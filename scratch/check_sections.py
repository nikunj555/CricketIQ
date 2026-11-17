from pathlib import Path
import re

content = Path("frontend/src/pages/WorkspacePage.tsx").read_text(encoding="utf-8")
sections = [
    "section-how-to-play",
    "section-what-you-did",
    "section-mistakes",
    "section-fix-first",
    "section-scores",
    "section-side-by-side"
]

positions = {}
for s in sections:
    pos = content.find(f'id="{s}"')
    positions[s] = pos
    print(f"Section {s}: position {pos}")
    assert pos != -1, f"Missing section {s}"

indices = [positions[s] for s in sections]
assert indices == sorted(indices), "Sections are not in expected order A -> B -> C -> D -> E -> F"
print("SUCCESS: Sections are verified in exact order A -> B -> C -> D -> E -> F!")
