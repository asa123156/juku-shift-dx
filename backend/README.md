# JUKU-SHIFT DX バックエンド

FastAPI による API サーバーです。**フロント接続前に必要な API は一通り揃えています。**

## セットアップ

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 起動

```bash
uvicorn main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs
- ヘルス: http://127.0.0.1:8000/health

## テスト

```bash
python -m tests.test_api
python -m tests.test_assignment_engine
```

## エンドポイント一覧

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/auth/login` | モックログイン |
| GET | `/api/shifts/dates` | 日付一覧 |
| GET | `/api/shifts/teachers` | 講師一覧 |
| GET | `/api/shifts` | 教室長ダッシュボード |
| GET | `/api/shifts/me` | 講師入力用 |
| POST | `/api/shifts` | 講師提出 |
| PATCH | `/api/shifts/bulk` | 期間一括提出（講師・生徒） |
| GET | `/api/shifts/my-schedule` | 確定スケジュール閲覧 |
| PATCH | `/api/admin/shifts/slot` | 教室長がコマ変更 |
| POST | `/api/admin/shifts/confirm` | 待機→一括確定 |
| POST | `/api/admin/assignments/candidates` | 割当候補一覧 |
| POST | `/api/admin/auto-assign` | AI自動割当実行 |
| POST | `/api/admin/assignment-requests/import` | CSV 割当リクエスト取込 |
| GET | `/api/lessons` | 授業コマ割り |

仕様詳細: [docs/api.md](../docs/api.md)

## デモアカウント

| メール | パスワード |
|--------|------------|
| `teacher@example.com` | `demo` |
| `admin@example.com` | `demo` |

## データベース（SQLite）

起動時に `backend/juku_shift.db` が自動作成されます（SQLAlchemy）。

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

**Period CRUD**、**period-bases（◎ 固定枠）**、**teacher/student submissions** は SQLite を使用。初回起動時に `data/*.json` が空 DB へシードされる。admin-overrides 等は引き続き JSON。

## データファイル

```
backend/data/
  shift-dashboards/   # 日別ダッシュボード（2026-06-10 など）
  teacher-submissions.json
  admin-overrides.json
  users.json
docs/lesson_mock.json   # 授業コマ割り
```

## フォルダ構成

```
backend/
  main.py
  config.py
  routers/    # auth, shifts, admin, lessons
  schemas/
  services/   # data_loader, shift_store, admin_store, dashboard_builder
  tests/
  data/
```
