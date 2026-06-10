"""コマ時間: 13:30 開始、授業 80 分、次コマは前コマ終了 10 分後。"""

from datetime import datetime, timedelta

FIRST_SLOT_START = "13:30"
CLASS_MINUTES = 80
GAP_MINUTES = 10
SLOT_COUNT = 4


def generate_time_slots() -> list[dict]:
    current = datetime.strptime(FIRST_SLOT_START, "%H:%M")
    slots: list[dict] = []
    for i in range(1, SLOT_COUNT + 1):
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
