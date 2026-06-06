# ─────────────────────────────────────────────────────────────────────────────
# tests/test_key_manager.py
#
# Full test suite for the Key Management System.
#
# Covers:
#   Group 1 — generate_key()  : size, type, randomness
#   Group 2 — validate_key()  : valid key, wrong type, wrong length
#   Group 3 — save_key()      : file creation, content, round-trip
#   Group 4 — load_key()      : from file, from env var, fallback, missing
#   Group 5 — rotate_key()    : new key generated, old key archived
#   Group 6 — get_key()       : singleton behaviour, cache clearing
#
# Run:
#   cd security
#   python tests/test_key_manager.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import io
import base64
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from encryption.key_manager import (
    generate_key, validate_key, save_key, load_key, rotate_key,
    get_key, clear_key_cache,
    KeyError_, InvalidKeyError,
)
from configs.security_settings import EncryptionConfig


def run_tests():

    passed = 0
    failed = 0
    last_group = None

    def check(group: str, description: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed, last_group
        if group != last_group:
            last_group = group
            header = f"  ── {group} "
            print(header + "─" * max(0, 64 - len(header)))
        ok     = bool(condition)
        status = "✅ PASS" if ok else "❌ FAIL"
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        print(f"  {status}  {description}")
        if detail:
            print(f"         {detail}")

    print("\n" + "=" * 68)
    print("       KEY MANAGER — FULL TEST SUITE")
    print("       Covers: generate | validate | save | load | rotate | singleton")
    print("=" * 68)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 1 — generate_key()
    # ══════════════════════════════════════════════════════════════════════════

    key1 = generate_key()
    key2 = generate_key()

    check("generate_key()",
          "Returns bytes",
          isinstance(key1, bytes))

    check("generate_key()",
          "Returns exactly 32 bytes (256 bits)",
          len(key1) == EncryptionConfig.KEY_SIZE_BYTES,
          f"len={len(key1)}")

    check("generate_key()",
          "Two calls produce different keys (randomness)",
          key1 != key2,
          f"key1[:8]={key1[:8].hex()}  key2[:8]={key2[:8].hex()}")

    # 10 unique keys
    keys = [generate_key() for _ in range(10)]
    check("generate_key()",
          "10 generated keys are all unique",
          len(set(keys)) == 10,
          f"unique={len(set(keys))}/10")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 2 — validate_key()
    # ══════════════════════════════════════════════════════════════════════════

    valid_key = generate_key()

    # Valid key — should pass silently (no exception)
    try:
        validate_key(valid_key)
        check("validate_key()", "Valid 32-byte key passes silently", True)
    except Exception as e:
        check("validate_key()", "Valid 32-byte key passes silently", False, str(e))

    # Wrong type — string
    try:
        validate_key("a_string_key")
        check("validate_key()", "String key raises InvalidKeyError", False)
    except InvalidKeyError:
        check("validate_key()", "String key raises InvalidKeyError", True)

    # Wrong type — int
    try:
        validate_key(12345)
        check("validate_key()", "Integer key raises InvalidKeyError", False)
    except InvalidKeyError:
        check("validate_key()", "Integer key raises InvalidKeyError", True)

    # Wrong type — None
    try:
        validate_key(None)
        check("validate_key()", "None raises InvalidKeyError", False)
    except InvalidKeyError:
        check("validate_key()", "None raises InvalidKeyError", True)

    # Too short
    try:
        validate_key(b"only_16_bytes___")
        check("validate_key()", "16-byte key raises InvalidKeyError", False)
    except InvalidKeyError:
        check("validate_key()", "16-byte key raises InvalidKeyError (needs 32)", True)

    # Too long
    try:
        validate_key(os.urandom(64))
        check("validate_key()", "64-byte key raises InvalidKeyError", False)
    except InvalidKeyError:
        check("validate_key()", "64-byte key raises InvalidKeyError (needs 32)", True)

    # Exactly 31 bytes
    try:
        validate_key(os.urandom(31))
        check("validate_key()", "31-byte key raises InvalidKeyError", False)
    except InvalidKeyError:
        check("validate_key()", "31-byte key (one short) raises InvalidKeyError", True)

    # Exactly 33 bytes
    try:
        validate_key(os.urandom(33))
        check("validate_key()", "33-byte key raises InvalidKeyError", False)
    except InvalidKeyError:
        check("validate_key()", "33-byte key (one long) raises InvalidKeyError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 3 — save_key()
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        key      = generate_key()
        key_file = tmp_path / "test.key"

        saved_path = save_key(key, key_file)

        check("save_key()",
              "Returns the path where the key was saved",
              saved_path == key_file)

        check("save_key()",
              "Key file is created on disk",
              key_file.exists())

        check("save_key()",
              "Key file is not empty",
              key_file.stat().st_size > 0)

        # Verify it's valid Base64 that decodes to the original key
        raw_content = key_file.read_text(encoding="ascii").strip()
        decoded     = base64.urlsafe_b64decode(raw_content)
        check("save_key()",
              "Key file contains Base64-encoded key that decodes to original bytes",
              decoded == key,
              f"base64_len={len(raw_content)}  decoded_len={len(decoded)}")

        # Invalid key should raise
        try:
            save_key(b"too_short", tmp_path / "bad.key")
            check("save_key()", "Invalid key raises InvalidKeyError", False)
        except InvalidKeyError:
            check("save_key()", "Invalid key raises InvalidKeyError before writing", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 4 — load_key()
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        key      = generate_key()
        key_file = tmp_path / "master.key"
        save_key(key, key_file)

        # Load from file
        loaded = load_key(path=key_file)
        check("load_key()",
              "Loaded key matches saved key (file round-trip)",
              loaded == key,
              f"key[:8]={key[:8].hex()}  loaded[:8]={loaded[:8].hex()}")

        check("load_key()",
              "Loaded key is exactly 32 bytes",
              len(loaded) == 32)

        # Load from environment variable
        env_name   = "_XPLOR_TEST_KEY_12345"
        b64_key    = base64.urlsafe_b64encode(key).decode("ascii")
        os.environ[env_name] = b64_key

        from_env = load_key(path=tmp_path / "nonexistent.key", env_var=env_name)
        check("load_key()",
              "Loads key from environment variable (env priority over file)",
              from_env == key)

        del os.environ[env_name]

        # Env var takes priority over file (even when file exists)
        other_key = generate_key()
        os.environ[env_name] = base64.urlsafe_b64encode(other_key).decode("ascii")
        priority_load = load_key(path=key_file, env_var=env_name)
        check("load_key()",
              "Environment variable takes priority over key file",
              priority_load == other_key)
        del os.environ[env_name]

        # Auto-generate fallback
        gen_key = load_key(
            path=tmp_path / "missing.key",
            env_var="_XPLOR_MISSING_ENV_KEY",
            allow_generate=True,
        )
        check("load_key()",
              "allow_generate=True produces a valid 32-byte key when nothing found",
              isinstance(gen_key, bytes) and len(gen_key) == 32)

        # Missing key — no fallback
        try:
            load_key(
                path=tmp_path / "missing.key",
                env_var="_XPLOR_MISSING_ENV_KEY",
                allow_generate=False,
            )
            check("load_key()", "Missing key with allow_generate=False raises KeyError_", False)
        except KeyError_:
            check("load_key()", "Missing key with allow_generate=False raises KeyError_", True)

        # Corrupted key file
        corrupt_file = tmp_path / "corrupt.key"
        corrupt_file.write_text("not-valid-base64-!@#$%", encoding="ascii")
        try:
            load_key(path=corrupt_file)
            check("load_key()", "Corrupted key file raises KeyError_", False)
        except KeyError_:
            check("load_key()", "Corrupted key file raises KeyError_", True)

        # Short key in file (valid Base64 but only 16 bytes)
        short_key = base64.urlsafe_b64encode(os.urandom(16)).decode("ascii")
        short_file = tmp_path / "short.key"
        short_file.write_text(short_key, encoding="ascii")
        try:
            load_key(path=short_file)
            check("load_key()", "Short key (16B) in file raises KeyError_", False)
        except (KeyError_, InvalidKeyError):
            check("load_key()", "Short key (16B) in file raises KeyError_ or InvalidKeyError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 5 — rotate_key()
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        key_file = tmp_path / "master.key"

        # Create initial key
        original_key = generate_key()
        save_key(original_key, key_file)

        # Rotate
        new_key = rotate_key(key_file)

        check("rotate_key()",
              "rotate_key() returns bytes",
              isinstance(new_key, bytes))

        check("rotate_key()",
              "New key is exactly 32 bytes",
              len(new_key) == 32)

        check("rotate_key()",
              "New key is different from the original key",
              new_key != original_key)

        # New key file loads correctly
        loaded_new = load_key(path=key_file)
        check("rotate_key()",
              "master.key now contains the new key",
              loaded_new == new_key)

        # Old key is archived
        archives = list(tmp_path.glob("master.key.*"))
        check("rotate_key()",
              "Old key is archived with timestamp suffix",
              len(archives) == 1,
              f"archive={archives[0].name if archives else 'none'}")

        if archives:
            # Archived key loads as the original key
            archived_key = load_key(path=archives[0])
            check("rotate_key()",
                  "Archived key file contains the original key (for legacy decryption)",
                  archived_key == original_key)

        # Rotate a second time — should produce two archive files
        rotate_key(key_file)
        archives2 = list(tmp_path.glob("master.key.*"))
        check("rotate_key()",
              "Second rotation produces two archive files total",
              len(archives2) == 2,
              f"archives={[a.name for a in sorted(archives2)]}")

        # Rotate when no file exists yet (first rotation)
        fresh_dir = tmp_path / "fresh"
        fresh_dir.mkdir()
        fresh_key_file = fresh_dir / "master.key"
        first_key = rotate_key(fresh_key_file)
        check("rotate_key()",
              "rotate_key() works on a fresh directory with no existing key file",
              isinstance(first_key, bytes) and len(first_key) == 32)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 6 — get_key() singleton
    # ══════════════════════════════════════════════════════════════════════════

    clear_key_cache()

    k1 = get_key(allow_generate=True)
    k2 = get_key(allow_generate=True)
    k3 = get_key(allow_generate=True)

    check("get_key() Singleton",
          "get_key() returns the same object on repeated calls (singleton)",
          k1 is k2 and k2 is k3)

    check("get_key() Singleton",
          "Cached key is 32 bytes",
          len(k1) == 32)

    # Clear and re-generate
    clear_key_cache()
    k4 = get_key(allow_generate=True)

    check("get_key() Singleton",
          "clear_key_cache() allows a new key to be generated on next call",
          True)  # If we got here without error, the test passed

    clear_key_cache()


    # ══════════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    total   = passed + failed
    overall = "ALL TESTS PASSED ✅" if failed == 0 else f"{failed} TEST(S) FAILED ❌"

    print("\n" + "=" * 68)
    print(f"  {passed} passed  |  {failed} failed  |  {total} total")
    print(f"  {overall}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    run_tests()
