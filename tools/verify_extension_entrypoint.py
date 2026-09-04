#!/usr/bin/env python3
"""Verify a CloudStack extension entry point against an expected SHA-512 digest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SHA512_RE = re.compile(r"^[0-9a-fA-F]{128}$")


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected: str) -> dict[str, object]:
    expected = expected.strip().lower()
    if not SHA512_RE.fullmatch(expected):
        return {
            "verified": False,
            "reason": "invalid_expected_sha512",
            "path": str(path),
            "expected_sha512": expected,
        }
    if not path.is_file():
        return {
            "verified": False,
            "reason": "entrypoint_not_found",
            "path": str(path),
            "expected_sha512": expected,
        }

    actual = sha512_file(path)
    return {
        "verified": actual == expected,
        "reason": "match" if actual == expected else "checksum_mismatch",
        "path": str(path),
        "expected_sha512": expected,
        "actual_sha512": actual,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="extension entry point to verify")
    parser.add_argument("expected_sha512", help="expected 128-character SHA-512 hex digest")
    args = parser.parse_args()

    result = verify(args.path, args.expected_sha512)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
