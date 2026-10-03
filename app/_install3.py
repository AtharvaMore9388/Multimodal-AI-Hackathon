import subprocess
import sys

results = {}
for pkg in ["uvicorn", "pytest"]:
    print(f"Trying {pkg}...")
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--timeout", "60", pkg]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        results[pkg] = (r.returncode, (r.stdout or "")[-500:] + "\n---STDERR---\n" + (r.stderr or "")[-500:])
        print(f"  {pkg} -> exit={r.returncode}")
    except Exception as e:
        results[pkg] = ("EXC", str(e))
        print(f"  {pkg} -> EXC: {e}")

with open("pip_install3.log", "w") as f:
    for k, v in results.items():
        f.write(f"=== {k} ({v[0]}) ===\n{v[1]}\n\n")
print("DONE")
