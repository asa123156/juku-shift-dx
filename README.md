# juku-shift-dx

個別指導塾のコマ割り・シフト管理 Web アプリ（React + FastAPI）。

## フォルダ構成

| パス | 内容 |
|------|------|
| `frontend/` | React（Vite）UI |
| `backend/` | FastAPI API サーバー |
| `docs/` | API 仕様・JSON モック |

## バックエンドの起動

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

- API ドキュメント: http://127.0.0.1:8000/docs
- 仕様一覧: [docs/api.md](docs/api.md)

## フロントエンドの起動

```bash
cd frontend
npm install
npm run dev
```

## 技術スタック

- バックエンド: Python 3.x / FastAPI / Uvicorn / Pydantic
- フロントエンド: React / Vite / Tailwind CSS
- 環境: venv（Python）

## 開発ブランチ

バックエンド API 一式: `feat/api-shifts`（マージ前はこのブランチを checkout）
