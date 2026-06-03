# JUKU-SHIFT DX バックエンド

FastAPI による API サーバーです。

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

- API ドキュメント: http://127.0.0.1:8000/docs
- ヘルスチェック: http://127.0.0.1:8000/health

## エンドポイント

| メソッド | パス | 説明 | データ源 |
|----------|------|------|----------|
| GET | `/api/shifts` | 教室長ダッシュボード用シフト | `backend/data/shift-dashboard.json` |
| GET | `/api/lessons` | 授業コマ割り | `docs/lesson_mock.json` |

詳細は [docs/api-shifts.md](../docs/api-shifts.md) を参照してください。

## フォルダ構成

```
backend/
  main.py              # FastAPI アプリ・CORS
  routers/             # ルート定義
  schemas/             # Pydantic モデル
  services/            # JSON 読み込みなど
  data/                # シフト用モック JSON
```
