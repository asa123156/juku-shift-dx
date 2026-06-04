# シフト API

## `GET /api/shifts`

教室長ダッシュボード用。講師の提出があれば `teachers` 行に反映し、`metrics` を再計算します。

| クエリ | 必須 | 説明 |
|--------|------|------|
| `date` | いいえ | `YYYY-MM-DD`。不一致は `404` |

データ源: `backend/data/shift-dashboard.json` + `backend/data/teacher-submissions.json`

---

## `GET /api/shifts/me`

講師シフト入力画面用（○/×/未入力）。

| クエリ | 必須 | 説明 |
|--------|------|------|
| `teacher_id` | はい | 例: `1`（田中 先生） |
| `date` | いいえ | 省略時はダッシュボードの既定日 |

### レスポンス例

```json
{
  "teacher_id": 1,
  "date": "2026-06-10",
  "slots": {
    "1": "available",
    "2": "unavailable",
    "3": "blank",
    "4": "blank"
  }
}
```

| 値 | UI |
|----|-----|
| `available` | ○ |
| `unavailable` | × |
| `blank` | 未選択 |

---

## `POST /api/shifts`

1日分をまとめて提出（「提出する」ボタン）。

### リクエスト例

```json
{
  "teacher_id": 1,
  "date": "2026-06-10",
  "slots": {
    "1": "available",
    "2": "available",
    "3": "unavailable",
    "4": "blank"
  }
}
```

`slots` は `"1"`〜`"4"` をすべて含めること。

### 教室長画面への変換

| 提出値 | ダッシュボード表示 |
|--------|-------------------|
| `available` | 待機 |
| `unavailable` | 不可 |
| `blank` | 未提出 |

### フロント接続例（StudentShift）

```javascript
const body = {
  teacher_id: 1,
  date: '2026-06-10',
  slots: {
    '1': shiftData.slot1 === 'available' ? 'available' : shiftData.slot1 === 'unavailable' ? 'unavailable' : 'blank',
    '2': /* slot2 同様 */,
    '3': /* ... */,
    '4': /* ... */,
  },
};
await fetch('http://127.0.0.1:8000/api/shifts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});
```

---

## `PATCH /api/shifts`

1コマだけ更新（任意）。

```json
{
  "teacher_id": 1,
  "date": "2026-06-10",
  "slot": 3,
  "status": "unavailable"
}
```

---

## 教室長ダッシュボード（GET レスポンス）

`teachers` のステータス: `確定` / `待機` / `不可` / `不足` / `未提出`

```javascript
const res = await fetch('http://127.0.0.1:8000/api/shifts?date=2026-06-10');
const { teachers, metrics, display_date } = await res.json();
setTeachers(teachers);
```

---

## 起動・確認

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload
```

```bash
# 提出
curl -s -X POST http://127.0.0.1:8000/api/shifts \
  -H 'Content-Type: application/json' \
  -d '{"teacher_id":1,"date":"2026-06-10","slots":{"1":"available","2":"available","3":"unavailable","4":"blank"}}'

# ダッシュボードで反映確認
curl -s 'http://127.0.0.1:8000/api/shifts' | python3 -m json.tool
```

- Swagger: http://127.0.0.1:8000/docs
