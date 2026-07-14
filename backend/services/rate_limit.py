"""ログイン試行のレート制限（インメモリ・単一プロセス前提）。

このアプリは systemd で uvicorn を単一プロセスで動かす小規模構成なので、
Redis 等を使わずプロセス内メモリで十分。複数ワーカー構成にする場合は
共有ストア（Redis 等）への置き換えが必要。
"""

from __future__ import annotations

import threading
import time

_LOCK = threading.Lock()
_ip_attempts: dict[str, list[float]] = {}
_account_failures: dict[str, list[float]] = {}

# IP 単位: 短時間の連打（スクリプトによる総当たり）を防ぐ
IP_WINDOW_SECONDS = 5 * 60
IP_MAX_ATTEMPTS = 20

# アカウント単位: 特定アカウントへのパスワード総当たりを防ぐ
ACCOUNT_WINDOW_SECONDS = 15 * 60
ACCOUNT_MAX_FAILURES = 5


def _prune(timestamps: list[float], window: float, now: float) -> list[float]:
    return [t for t in timestamps if now - t < window]


def check_login_allowed(ip: str, email: str) -> tuple[str, int] | None:
    """試行前に呼ぶ。ブロック中なら (メッセージ, Retry-After秒) を返す。"""
    now = time.time()
    with _LOCK:
        ip_hits = _prune(_ip_attempts.get(ip, []), IP_WINDOW_SECONDS, now)
        _ip_attempts[ip] = ip_hits
        if len(ip_hits) >= IP_MAX_ATTEMPTS:
            return "アクセスが集中しています。しばらく時間をおいて再度お試しください", IP_WINDOW_SECONDS

        key = email.lower()
        failures = _prune(_account_failures.get(key, []), ACCOUNT_WINDOW_SECONDS, now)
        _account_failures[key] = failures
        if len(failures) >= ACCOUNT_MAX_FAILURES:
            return (
                "ログイン試行回数が多すぎます。15分ほど時間をおいて再度お試しください",
                ACCOUNT_WINDOW_SECONDS,
            )
    return None


def record_attempt(ip: str, email: str, *, success: bool) -> None:
    """ログイン処理の後に呼ぶ。失敗のみアカウント単位カウントに積む。"""
    now = time.time()
    key = email.lower()
    with _LOCK:
        _ip_attempts.setdefault(ip, []).append(now)
        if success:
            _account_failures.pop(key, None)
        else:
            _account_failures.setdefault(key, []).append(now)


def reset_login_rate_limit_for_tests() -> None:
    with _LOCK:
        _ip_attempts.clear()
        _account_failures.clear()
