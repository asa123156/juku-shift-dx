# シフト API 詳細

一覧は [api.md](./api.md) を参照。

## 日付

`GET /api/shifts/dates` で一覧取得。フロントの日付タブ対応:

- `2026-06-10`（月）
- `2026-06-11`（火）
- `2026-06-12`（水）

## `GET /api/shifts?date=`

提出・教室長操作を反映したダッシュボードを返す。

## `GET /api/shifts/me`

| クエリ | 必須 |
|--------|------|
| `teacher_id` | はい |
| `date` | いいえ（省略時 `2026-06-10`） |

`slots`: `priority` (◎) | `available` (○) | `unavailable` (×) | `blank` (未入力)

## `POST /api/shifts`

```json
{
  "teacher_id": 1,
  "date": "2026-06-10",
  "slots": { "1": "priority", "2": "available", "3": "unavailable", "4": "blank" }
}
```

| 提出値 | 記号 | ダッシュボード |
|--------|------|----------------|
| `priority` | ◎ | ◎ |
| `available` | ○ | 待機 |
| `unavailable` | × | 不可 |
| `blank` | 未入力 | 未提出 |

## 教室長

### `PATCH /api/admin/shifts/slot`

```json
{ "date": "2026-06-10", "teacher_id": 2, "slot": 3, "status": "確定" }
```

### `POST /api/admin/shifts/confirm`

```json
{ "date": "2026-06-10" }
```

当日の「待機」をすべて「確定」にする（「シフトを確定する」ボタン用）。

## 認証（開発用）

`POST /api/auth/login` — `teacher@example.com` / `admin@example.com`、パスワード `demo`
