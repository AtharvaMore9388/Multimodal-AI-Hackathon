import subprocess
import sys

PACKAGES = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic",
    "pydantic-settings",
    "python-multipart",
    "python-dotenv",
    "httpx",
    "sqlalchemy",
    "aiosqlite",
    "pytest",
    "pytest-asyncio",
]

with open("pip_install.log", "w", encoding="utf-8") as log:
    log.write(f"Using Python: {sys.executable}\n")
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"] + PACKAGES
    log.write(f"Running: {' '.join(cmd)}\n\n")
    result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    log.write(f"\nEXIT CODE: {result.returncode}\n")
    print(f"EXIT CODE: {result.returncode}")
    sys.exit(result.returncode)
