"""Check starter syntax and report LOC; never pretend to be a human review."""
import ast
from pathlib import Path

root = Path(__file__).resolve().parent.parent
paths = sorted((root / "scripts").glob("*.py"))
for path in paths:
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))
    print(f"{path.relative_to(root)}: {len(source.splitlines())} lines; syntax valid")
print("Automated scope check only. See docs/REVIEW.md for the manual simplification review.")
