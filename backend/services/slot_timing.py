"""コマ時間: 13:00（1時）開始、授業 80 分、次コマは前コマ終了 10 分後。"""

from datetime import datetime, timedelta

FIRST_SLOT_START = "13:00"
CLASS_MINUTES = 80
GAP_MINUTES = 10
SLOT_COUNT = 6
SLOT_NUMS = tuple(range(1, SLOT_COUNT + 1))
SLOT_KEYS = tuple(str(n) for n in SLOT_NUMS)
SLOT_FIELDS = tuple(f"s{n}" for n in SLOT_NUMS)


def empty_slot_map() -> dict[str, str]:
    return {k: "" for k in SLOT_KEYS}


def generate_time_slots() -> list[dict]:
    current = datetime.strptime(FIRST_SLOT_START, "%H:%M")
    slots: list[dict] = []
    for i in SLOT_NUMS:
        end = current + timedelta(minutes=CLASS_MINUTES)
        slots.append(
            {
                "slot": i,
                "label": f"{i}コマ",
                "start": current.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
            }
        )
        current = end + timedelta(minutes=GAP_MINUTES)
    return slots
