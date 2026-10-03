from pathlib import Path
p = Path("pip_install2.log")
print(f"EXISTS: {p.exists()} SIZE: {p.stat().st_size if p.exists() else 0}")
if p.exists():
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"TOTAL LINES: {len(lines)}")
    for line in lines[-50:]:
        print(line)
