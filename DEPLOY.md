# デプロイ手順（Oracle Cloud Always Free / 月額0円）

JUKU-SHIFT DX を Oracle Cloud の無料枠 VM で公開するための手順。
アプリは1プロセス（uvicorn）でフロントも API も配信し、Caddy が HTTPS を自動化する。

```
利用者のブラウザ ──HTTPS──> Caddy ──> uvicorn(127.0.0.1:8000)
                                        ├─ /api/...  FastAPI
                                        └─ /...      frontend/dist (SPA)
```

## 0. 費用

| 項目 | 費用 |
|------|------|
| Oracle Cloud Always Free VM | 0円（無期限） |
| 独自ドメイン | 年1,000〜1,500円程度（唯一の実費） |
| HTTPS 証明書 | 0円（Caddy が Let's Encrypt で自動取得・更新） |

## 1. 自分でやること（アカウント関連）

1. **Oracle Cloud アカウント作成** — https://www.oracle.com/jp/cloud/free/
   - クレジットカード登録が必要（Always Free 枠内なら課金されない）
   - リージョンは **Japan East (Tokyo)** を推奨（後から変更不可）
2. **VM 作成**（コンソール → Compute → Instances → Create Instance）
   - Image: **Ubuntu 24.04**
   - Shape: **Ampere (VM.Standard.A1.Flex)** — Always Free 対象。まずは 2 OCPU / 12GB で十分
   - SSH 公開鍵を登録し、秘密鍵を保管
3. **ポート開放**（VCN → Security List → Ingress Rules）
   - TCP 80 と 443 を 0.0.0.0/0 に対して許可
   - ※ VM 内の iptables も Oracle の Ubuntu イメージは初期状態で閉じているので、
     セットアップ時に `sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT`（443も同様）を実行し、
     `sudo netfilter-persistent save` で永続化する
4. **ドメイン取得と DNS 設定**
   - お名前.com / Cloudflare Registrar 等で取得
   - A レコードを VM のパブリック IP に向ける（例: `juku.example.com → 140.x.x.x`）

## 2. VM 上でのセットアップ

SSH でログインして:

```bash
sudo git clone https://github.com/asa123156/juku-shift-dx.git /opt/juku-shift-dx
sudo chown -R ubuntu:ubuntu /opt/juku-shift-dx
sudo bash /opt/juku-shift-dx/deploy/setup.sh
```

`setup.sh` がやること:

1. OS パッケージ（python3-venv / nodejs / caddy）のインストール
2. Python 仮想環境の作成と依存インストール
3. フロントエンドのビルド（`frontend/dist` 生成）
4. `backend/.env.production` に JWT_SECRET_KEY を自動生成（初回のみ）
5. systemd 登録: アプリ本体（`juku-shift.service`）+ 日次バックアップ（4:00、14世代）
6. Caddy の起動

最後にドメインを設定:

```bash
sudo nano /etc/caddy/Caddyfile   # juku.example.com を自分のドメインに変更
sudo systemctl reload caddy
```

ブラウザで `https://自分のドメイン/` を開き、ログイン画面が表示されれば完了。

## 3. 日常運用

| やりたいこと | コマンド |
|------|------|
| 状態確認 | `systemctl status juku-shift` |
| ログ確認 | `journalctl -u juku-shift -f` |
| アプリ更新 | `cd /opt/juku-shift-dx && git pull && cd frontend && npm run build && sudo systemctl restart juku-shift` |
| 手動バックアップ | `cd /opt/juku-shift-dx/backend && .venv/bin/python -m scripts.backup_data` |
| バックアップ一覧 | `ls /opt/juku-shift-dx/backend/backups/` |

### リストア（復元）

```bash
sudo systemctl stop juku-shift
cd /opt/juku-shift-dx/backend
cp backups/<スナップショット>/juku_shift.db juku_shift.db
rm -rf data && cp -r backups/<スナップショット>/data data
sudo systemctl start juku-shift
```

### VM の外へのバックアップ（推奨・任意）

VM 自体が消えた場合に備え、`backups/` を手元にも定期的にコピーする:

```bash
# 手元の Mac から（cron や手動で）
rsync -az ubuntu@<VMのIP>:/opt/juku-shift-dx/backend/backups/ ~/juku-backups/
```

## 4. ローカル開発との関係

- 開発時は今まで通り `uvicorn main:app --reload` + `npm run dev`（Vite が /api をプロキシ）
- `frontend/dist` が存在すると uvicorn 単体でもフロントを配信する（本番と同じ形）
- 本番の環境変数は `backend/.env.production`（gitignore 済み）に置く。
  設定可能: `JWT_SECRET_KEY`（必須）, `CORS_ALLOWED_ORIGINS`（同一オリジン配信なら不要）
