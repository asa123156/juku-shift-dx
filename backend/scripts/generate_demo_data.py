"""デモ用 JSON データを生成する（11開校日・生徒5名+）。

Usage:
    cd backend && python -m scripts.generate_demo_data
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from config import DASHBOARDS_DIR, DATA_DIR
from services.slot_timing import SLOT_COUNT, SLOT_FIELDS, SLOT_NUMS, generate_time_slots

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

TEACHERS = [
    {"id": 1, "name": "田中 先生", "color": "bg-blue-100 text-blue-600"},
    {"id": 2, "name": "佐藤 先生", "color": "bg-pink-100 text-pink-600"},
    {"id": 3, "name": "鈴木 先生", "color": "bg-green-100 text-green-600"},
]

STUDENTS = [
    (1, "近大太郎", "high", 2),
    (2, "山田花子", "middle", 3),
    (3, "近大次郎", "middle", 1),
    (4, "佐藤美咲", "elementary", 6),
    (5, "高橋健太", "high", 1),
    (99, "テスト太郎", "elementary", 4),
]

PERIOD_START = "2026-06-09"
PERIOD_END = "2026-06-20"

# 講師ベースパターン（日ごとにローテーション）
TEACHER_PATTERNS = [
    ["待機", "待機", "待機", "未提出", "待機", "待機"],
    ["確定", "待機", "待機", "不可", "待機", "待機"],
    ["待機", "不可", "待機", "待機", "待機", "未提出"],
    ["未提出", "待機", "確定", "待機", "待機", "待機"],
    ["待機", "待機", "不可", "待機", "待機", "待機"],
    ["確定", "待機", "待機", "待機", "待機", "待機"],
    ["待機", "待機", "待機", "待機", "待機", "待機"],
]


def iter_open_dates(start: str, end: str) -> list[str]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    out: list[str] = []
    while current <= last:
        if current.weekday() != 6:
            out.append(current.isoformat())
        current += timedelta(days=1)
    return out


def _teacher_row(meta: dict, pattern: list[str]) -> dict:
    row = dict(meta)
    for field, status in zip(SLOT_FIELDS, pattern, strict=True):
        row[field] = status
    return row


def build_dashboard(iso_date: str, day_idx: int) -> dict:
    d = date.fromisoformat(iso_date)
    display = f"2026年 {d.month}月{d.day}日 ({WEEKDAY_JA[d.weekday()]}) の状況"
    teachers = []
    for i, meta in enumerate(TEACHERS):
        pat = TEACHER_PATTERNS[(day_idx + i) % len(TEACHER_PATTERNS)]
        teachers.append(_teacher_row(meta, pat))
    unsubmitted = sum(1 for t in teachers if any(t[f"s{n}"] == "未提出" for n in SLOT_NUMS))
    return {
        "date": iso_date,
        "display_date": display,
        "metrics": {"unsubmitted_teachers": unsubmitted},
        "time_slots": generate_time_slots(),
        "teachers": teachers,
    }


def build_period_bases(open_dates: list[str]) -> dict:
    """教室長が設定する ◎ 通常コマ（生徒・講師）。"""
    students: dict = {}
    for sid, *_ in STUDENTS:
        days: dict = {}
        for idx, iso_date in enumerate(open_dates):
            slots = {str(n): "" for n in SLOT_NUMS}
            if sid == 1 or (idx + sid) % 3 != 2:
                slots["1"] = "◎"
            days[iso_date] = slots
        students[str(sid)] = days

    teachers: dict = {}
    for tid in (1, 2, 3):
        days = {}
        for idx, iso_date in enumerate(open_dates):
            slots = {str(n): "" for n in SLOT_NUMS}
            if tid == 1 and iso_date == "2026-06-10":
                slots["1"] = "◎"
            elif tid == 1 and iso_date == "2026-06-11":
                slots["2"] = "◎"
            elif (idx + tid) % 4 == 0:
                slots["1"] = "◎"
            elif (idx + tid) % 4 == 1:
                slots["2"] = "◎"
            days[iso_date] = slots
        teachers[str(tid)] = days

    return {
        "1": {
            "teachers": teachers,
            "students": students,
            "_dates_initialized": open_dates,
        }
    }


def build_student_submissions(open_dates: list[str]) -> dict:
    """生徒ごとに 空き/× パターンを日付に割当。"""
    patterns = {
        1: ["", "×", "×", "", "×", "×"],
        2: ["×", "", "×", "", "×", ""],
        3: ["×", "", "", "×", "", "×"],
        4: ["", "×", "", "×", "", "×"],
        5: ["", "×", "", "×", "", ""],
        99: ["", "×", "", "×", "", ""],
    }
    out: dict = {}
    for idx, iso_date in enumerate(open_dates):
        day: dict = {}
        for sid, base in patterns.items():
            rotated = [base[(i + idx) % SLOT_COUNT] for i in range(SLOT_COUNT)]
            day[str(sid)] = {str(n + 1): rotated[n] for n in range(SLOT_COUNT)}
        out[iso_date] = day
    return out


def build_teacher_submissions(open_dates: list[str]) -> dict:
    out: dict = {}
    for idx, iso_date in enumerate(open_dates):
        if idx % 3 != 0:
            continue
        slots = {str(n): "" for n in SLOT_NUMS}
        slots["1"] = "◎"
        slots["3"] = "×"
        out[iso_date] = {"1": slots}
    return out


def build_assignment_requests(open_dates: list[str]) -> dict:
    """日付ごとの未割当リクエスト。"""
    plan = [
        (1, "近大太郎", "数学I"),
        (2, "山田花子", "英語"),
        (3, "近大次郎", "国語"),
        (4, "佐藤美咲", "理科"),
        (5, "高橋健太", "社会"),
        (99, "テスト太郎", "英語"),
        (1, "近大太郎", "英語"),
        (2, "山田花子", "数学I"),
    ]
    out: dict = {d: [] for d in open_dates}
    for idx, iso_date in enumerate(open_dates):
        for j in range(3):
            sid, name, subject = plan[(idx * 3 + j) % len(plan)]
            if j == 2 and idx % 2 == 1:
                continue
            out[iso_date].append({"student_id": sid, "student_name": name, "subject": subject})
    return out


def build_users() -> list[dict]:
    users = [
        {
            "email": "teacher@example.com",
            "password": "demo",
            "role": "teacher",
            "teacher_id": 1,
            "name": "田中 先生",
            "redirect": "/student",
        },
        {
            "email": "admin@example.com",
            "password": "demo",
            "role": "admin",
            "teacher_id": None,
            "student_id": None,
            "name": "教室長",
            "redirect": "/admin",
        },
    ]
    for sid, name, *_ in STUDENTS:
        if sid == 1:
            users.append(
                {
                    "email": "student@example.com",
                    "password": "demo",
                    "role": "student",
                    "teacher_id": None,
                    "student_id": sid,
                    "name": name,
                    "redirect": "/student-schedule",
                }
            )
        else:
            users.append(
                {
                    "email": f"student{sid}@example.com",
                    "password": "demo",
                    "role": "student",
                    "teacher_id": None,
                    "student_id": sid,
                    "name": name,
                    "redirect": "/student-schedule",
                }
            )
    return users


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    open_dates = iter_open_dates(PERIOD_START, PERIOD_END)
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    for idx, iso_date in enumerate(open_dates):
        write_json(DASHBOARDS_DIR / f"{iso_date}.json", build_dashboard(iso_date, idx))

    write_json(DATA_DIR / "periods.json", {
        "next_id": 2,
        "active_period_id": 1,
        "items": [
            {
                "id": 1,
                "name": "2026年6月 夏期講習",
                "start_date": PERIOD_START,
                "end_date": PERIOD_END,
                "status": "COLLECTING",
            }
        ],
    })
    write_json(DATA_DIR / "period-bases.json", build_period_bases(open_dates))
    write_json(DATA_DIR / "student-submissions.json", build_student_submissions(open_dates))
    write_json(DATA_DIR / "teacher-submissions.json", build_teacher_submissions(open_dates))
    write_json(DATA_DIR / "assignment-requests.json", build_assignment_requests(open_dates))
    write_json(DATA_DIR / "assignments.json", {})
    write_json(DATA_DIR / "users.json", build_users())
    write_json(
        DATA_DIR / "students.json",
        {
            "next_id": 100,
            "items": [
                {"id": s[0], "name": s[1], "school_level": s[2], "grade_year": s[3]}
                for s in STUDENTS
            ],
        },
    )
    write_json(
        DATA_DIR / "teachers.json",
        {
            "next_id": 10,
            "items": [{"id": t["id"], "name": t["name"], "color": t["color"]} for t in TEACHERS],
        },
    )

    print(f"生成完了: 開校日 {len(open_dates)} 日（日曜除外）")
    print(f"  {open_dates[0]} 〜 {open_dates[-1]}")
    print(f"  生徒 {len(STUDENTS)} 名 / 講師 {len(TEACHERS)} 名 / コマ {SLOT_COUNT}")
    print(f"  ダッシュボード {len(open_dates)} 件")
    req_total = sum(len(v) for v in build_assignment_requests(open_dates).values())
    print(f"  割当リクエスト {req_total} 件")


if __name__ == "__main__":
    main()
