#!/usr/bin/env python3
"""Prepare Firebase service-account credentials for GitHub Actions.

Preferred secret:
  FIREBASE_SERVICE_ACCOUNT_B64 = base64 -w0 service-account.json

Legacy fallback:
  FIREBASE_SERVICE_ACCOUNT_BALKES_SKOR = raw JSON service account

The legacy fallback tries to repair the common mistake where the private_key
field is pasted with real line breaks instead of escaped \n sequences.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

OUT = Path("/tmp/firebase-service-account.json")


def fail(msg: str) -> None:
    print(f"Firebase credentials error: {msg}", file=sys.stderr)
    sys.exit(1)


def repair_multiline_private_key(text: str) -> str:
    marker = '"private_key": "'
    start_marker = text.find(marker)
    if start_marker < 0:
        return text
    start = start_marker + len(marker)
    end_marker = "-----END PRIVATE KEY-----"
    end = text.find(end_marker, start)
    if end < 0:
        return text
    end += len(end_marker)
    private_key = text[start:end]
    private_key = private_key.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")
    return text[:start] + private_key + text[end:]


def load_secret() -> str:
    b64 = (os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64") or "").strip()
    raw = (os.environ.get("FIREBASE_SERVICE_ACCOUNT_BALKES_SKOR") or "").strip()

    if b64:
        try:
            return base64.b64decode(b64, validate=True).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            fail(f"FIREBASE_SERVICE_ACCOUNT_B64 çözülemedi: {exc}")
    if raw:
        return raw
    fail("FIREBASE_SERVICE_ACCOUNT_B64 veya FIREBASE_SERVICE_ACCOUNT_BALKES_SKOR secret yok.")
    return ""


def main() -> None:
    text = load_secret().strip("\ufeff\n\r\t ")
    try:
        info = json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_multiline_private_key(text)
        try:
            info = json.loads(repaired)
        except json.JSONDecodeError as exc:
            fail(
                "Secret geçerli JSON değil. En sağlam çözüm: service account JSON dosyasını "
                "base64 yapıp FIREBASE_SERVICE_ACCOUNT_B64 secret'ına koy. "
                f"JSON hatası: {exc}"
            )

    required = ["type", "project_id", "private_key", "client_email"]
    missing = [k for k in required if not info.get(k)]
    if missing:
        fail("Service account JSON eksik alan içeriyor: " + ", ".join(missing))
    if info.get("type") != "service_account":
        fail("Secret bir service_account JSON'u gibi görünmüyor.")

    OUT.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    OUT.chmod(0o600)
    print("Firebase credentials hazır: /tmp/firebase-service-account.json")
    print("Service account:", info.get("client_email", "unknown"))


if __name__ == "__main__":
    main()
