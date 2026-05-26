# juku-shift-dx
個別指導塾の複雑なコマ割りやシフト管理を自動化・効率化するためのWebアプリケーションです。
フロントエンド（React）とバックエンド（FastAPI）を連携させて開発しています。

## 📁 フォルダ構成

- `バックエンド/` : FastAPI（Python）によるバックエンドAPIサーバー
- `ドキュメント/` : フロント・バック間のデータ設計（JSONモックなど）

## 🚀 バックエンドの起動方法
他のメンバーが自分のPCでこのバックエンドを動かすための手順です。
### 1. 仮想環境の有効化
ターミナルで `juku-shift-dx` のルート（一番上）にいる状態から、以下を実行します。
```bash
cd バックエンド
source .venv/bin/activate  # Macの場合
# .venv\Scripts\activate  # Windowsの場合
起動コマンド
uvicorn main:app --reload
🛠 使用技術（技術スタック）
バックエンド : Python 3.x / FastAPI / Uvicorn
フロントエンド : React（TypeScript）
環境管理 : venv (Python仮想環境)