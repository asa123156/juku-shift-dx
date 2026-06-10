# JUKU-SHIFT DX API 一覧

ベース URL（開発）: `http://127.0.0.1:8000`  
Swagger: http://127.0.0.1:8000/docs

## 認証（モック）

### `POST /api/auth/login`

| メール | パスワード | 役割 | 遷移先 |
|--------|------------|------|--------|
| `teacher@example.com` | `demo` | 講師 (`teacher_id: 1`) | `/student` |
| `admin@example.com` | `demo` | 教室長 | `/admin` |

## シフト

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/shifts/dates` | 利用可能な日付一覧 |
| GET | `/api/shifts/teachers?date=` | 講師一覧（id, name, color） |
| GET | `/api/shifts?date=` | 教室長ダッシュボード |
| GET | `/api/shifts/me?teacher_id=&date=` | 講師入力（○/×） |
| POST | `/api/shifts` | 講師が1日分提出 |
| PATCH | `/api/shifts` | 講師が1コマ更新 |

## 教室長操作

| メソッド | パス | 説明 |
|----------|------|------|
| PATCH | `/api/admin/shifts/slot` | コマのステータスを直接変更 |
| POST | `/api/admin/shifts/confirm` | 当日の「待機」→「確定」 |
| POST | `/api/admin/assignments/candidates` | 自動割当候補の取得（NGルール適用後） |
| POST | `/api/admin/auto-assign` | 未割当リクエストの一括自動割当 |

### 自動割当ルール

1. 講師コマが「不可」→ 候補から除外
2. 生徒が同科目を隣接コマで連続受講 → 除外
3. 講師が3コマ連続担当になる → 除外

割当成功時、該当コマはダッシュボード上 **「AI提案」** になる。

## 授業コマ割り

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/lessons?date=` | `docs/lesson_mock.json` |

## データの優先順位（シフト表示）

1. `backend/data/shift-dashboards/{date}.json`（ベース）
2. `teacher-submissions.json`（講師提出）
3. `admin-overrides.json`（教室長操作・確定）

## 日付

フロントの日付タブに対応: `2026-06-10`（月）, `2026-06-11`（火）, `2026-06-12`（水）

詳細・例: [api-shifts.md](./api-shifts.md)
