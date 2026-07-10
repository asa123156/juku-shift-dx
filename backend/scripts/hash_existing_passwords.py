"""backend/data/users.json の平文パスワードを bcrypt ハッシュに置き換える（冪等）。

Usage:
    cd backend && python -m scripts.hash_existing_passwords
"""

from __future__ import annotations

import json

from config import DATA_DIR
from security import hash_password

USERS_PATH = DATA_DIR / "users.json"


def main() -> None:
    users = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    changed = 0
    for user in users:
        password = user.get("password", "")
        if password.startswith("$2"):
            continue
        user["password"] = hash_password(password)
        changed += 1
    USERS_PATH.write_text(
        json.dumps(users, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{changed} 件のパスワードをハッシュ化しました（対象 {len(users)} 件）。")


if __name__ == "__main__":
    main()
