import subprocess, sys

scripts = [
    "tests/test_password_hashing.py",
    "tests/test_jwt.py",
    "tests/test_token_validation.py",
    "tests/test_rbac.py",
    "tests/test_file_upload_guard.py",
]

results = []
for s in scripts:
    r = subprocess.run(
        [sys.executable, s],
        capture_output=True, text=True,
        cwd=r"f:\University Work\04_Semester\Semester Project\Xplor\security"
    )
    results.append((s, r))

print("\n" + "=" * 60)
print("  GRAND TOTAL — ALL SECURITY TEST SUITES")
print("=" * 60)

total_p = 0
total_f = 0

for s, r in results:
    name = s.split("/")[-1]
    # Extract last summary line
    summary = ""
    for line in reversed(r.stdout.splitlines()):
        if "passed" in line:
            summary = line.strip()
            break
    if not summary:
        summary = "ERROR: " + r.stderr[:80]
    
    # Parse counts
    try:
        p = int(r.stdout.split("passed")[0].split()[-1])
        f = int(r.stdout.split("failed")[0].split()[-1])
        total_p += p
        total_f += f
        status = "✅" if f == 0 else "❌"
        print(f"  {status}  {name:<40} {p:>4} passed  |  {f} failed")
    except Exception:
        print(f"  ❌  {name:<40} COULD NOT PARSE")

print("-" * 60)
overall = "ALL TESTS PASSED ✅" if total_f == 0 else f"{total_f} FAILURE(S) ❌"
print(f"     {'TOTAL':<40} {total_p:>4} passed  |  {total_f} failed")
print(f"     {overall}")
print("=" * 60)
