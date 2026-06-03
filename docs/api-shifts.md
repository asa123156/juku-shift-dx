# シフト API（教室長ダッシュボード）

## `GET /api/shifts`

指定日のシフト状況（講師×コマ）を返します。開発中は `backend/data/shift-dashboard.json` を読み込みます。

### クエリパラメータ

| 名前 | 必須 | 説明 |
|------|------|------|
| `date` | いいえ | `YYYY-MM-DD`。JSON の `date` と一致しない場合は `404` |

### レスポンス例（200）

```json
{
  "date": "2026-06-10",
  "display_date": "2026年 6月10日 (月) の状況",
  "metrics": {
    "unsubmitted_teachers": 3,
    "shortage_slots": 5
  },
  "time_slots": [
    { "slot": 1, "label": "1コマ", "start": "13:00", "end": "14:20" }
  ],
  "teachers": [
    {
      "id": 1,
      "name": "田中 先生",
      "color": "bg-blue-100 text-blue-600",
      "s1": "確定",
      "s2": "確定",
      "s3": "不可",
      "s4": "不可"
    }
  ]
}
```

### `teachers` のステータス値

| 値 | 意味（UI） |
|----|------------|
| `確定` | シフト確定 |
| `待機` | 調整待ち |
| `不可` | 出勤不可 |
| `不足` | 講師不足 |
| `未提出` | 講師未提出 |

### フロント接続例

```javascript
const res = await fetch('http://127.0.0.1:8000/api/shifts?date=2026-06-10');
const data = await res.json();
setTeachers(data.teachers);
// data.metrics / data.display_date もヘッダー・KPIに利用可能
```

### 確認方法

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- 疎通: `curl -s 'http://127.0.0.1:8000/api/shifts' | python -m json.tool`
