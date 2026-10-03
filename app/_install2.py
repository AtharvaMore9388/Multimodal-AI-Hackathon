import subprocess
import sys

PACKAGES = [
    "sqlalchemy",
    "pydantic-settings",
    "aiosqlite",
    "pytest",
    "pytest-asyncio",
    "uvicorn",
]

with open("pip_install2.log", "w", encoding="utf-8") as log:
    log.write(f"Using Python: {sys.executable}\n\n")
    for pkg in PACKAGES:
        log.write(f"\n--- Installing {pkg} ---\n")
        log.flush()
        cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir", pkg]
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=180)
        log.write(f"[{pkg}] EXIT: {result.returncode}\n")
        log.flush()
        print(f"[{pkg}] EXIT: {result.returncode}")
    log.write("\nALL DONE\n")
print("ALL DONE")
