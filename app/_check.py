from pathlib import Path
p = Path("pip_install.log")
print(f"EXISTS: {p.exists()} SIZE: {p.stat().st_size if p.exists() else 0}")
if p.exists():
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    print(f"TOTAL LINES: {len(lines)}")
    for line in lines[-30:]:
        print(line)
