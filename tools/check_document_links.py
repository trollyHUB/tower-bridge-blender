"""Check local Markdown links in the repository's maintained documentation."""
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT/'README.md', *sorted((ROOT/'docs').glob('*.md')),
         *sorted((ROOT/'assets').rglob('*.md'))]
missing = []
checked = 0
for path in files:
    for match in re.finditer(r'!?\[[^\]]*\]\(([^\n]+?)\)', path.read_text(encoding='utf-8-sig')):
        target = match.group(1).strip().strip('<>')
        if target.startswith('#') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
            continue
        target = unquote(target.split('#',1)[0])
        if not target:
            continue
        checked += 1
        if not (path.parent/target).exists():
            missing.append((str(path.relative_to(ROOT)),target))
assert not missing, ('Broken local Markdown links', missing)
print('DOCUMENT_LINKS_OK', checked)
