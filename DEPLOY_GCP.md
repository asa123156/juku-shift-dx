# デプロイ手順（Google Cloud / 無料枠重視・月額0円）

JUKU-SHIFT DX を Google Cloud の無料枠 VM で公開するための手順。
[DEPLOY.md](DEPLOY.md)（Oracle Cloud 向け）と同じ構成・同じスクリプトを使う。
アプリは1プロセス（uvicorn）でフロントも API も配信し、Caddy が HTTPS を自動化する。

```
利用者のブラウザ ──HTTPS──> Caddy ──> uvicorn(127.0.0.1:8000)
                                        ├─ /api/...  FastAPI
                                        └─ /...      frontend/dist (SPA)
```

## 0. 費用と前提（無料枠重視で選定）

| 項目 | 費用 | 備考 |
|------|------|------|
| Compute Engine e2-micro（Always Free） | 0円（無期限） | **無料枠は米国リージョンのみ対象**（`us-west1`/`us-central1`/`us-east1`）。東京リージョンだと有料（月$6〜7程度） |
| 標準永続ディスク 30GB | 0円 | 無料枠の上限ちょうど |
| 静的外部IP | 0円 | インスタンスが稼働中であれば無料（停止すると課金される点に注意） |
| 下り通信 1GB/月（北米→日本含む主要地域） | 0円 | 超過分は課金。塾の生徒・講師数規模なら通常収まる |
| 独自ドメイン | 年1,000〜1,500円程度 | 唯一の実費 |
| HTTPS証明書 | 0円 | Caddy が Let's Encrypt で自動取得・更新 |

**トレードオフ**: 米国西海岸（`us-west1` = オレゴン）から日本への通信になるため、往復で+100〜150ms程度の遅延が乗る。フォーム入力・シフト提出が中心のこのアプリでは体感上ほぼ問題にならない想定だが、体感速度を最優先したい場合は東京リージョン（有料）に切り替えることもできる（下記「リージョンを変える場合」参照）。

## 1. 自分でやること（アカウント関連）

### 1-1. Google Cloud アカウント・プロジェクト作成

1. https://console.cloud.google.com/ にアクセスし、Googleアカウントでログイン
2. 初回はクレジットカード登録が必要（無料トライアル $300 分のクレジットが付くが、Always Free 枠の範囲なら期限後も0円）
3. 新しいプロジェクトを作成（例: `juku-shift-dx`）
4. [Cloud Shell](https://console.cloud.google.com/) を開く（画面右上の `>_` アイコン）— ブラウザだけで `gcloud` コマンドが使える。ローカルに `gcloud` をインストールしなくてもよい

以下のコマンドは Cloud Shell（またはローカルにインストール済みの `gcloud`）で実行する。

```bash
# プロジェクトIDを自分のものに置き換えて設定
gcloud config set project YOUR_PROJECT_ID

# Compute Engine API を有効化
gcloud services enable compute.googleapis.com
```

### 1-2. VM作成（無料枠 e2-micro / us-west1）

```bash
gcloud compute instances create juku-shift-vm \
  --zone=us-west1-b \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-type=pd-standard \
  --boot-disk-size=30GB \
  --tags=http-server,https-server
```

### 1-3. ファイアウォール（80/443番ポート開放）

```bash
gcloud compute firewall-rules create allow-http \
  --allow=tcp:80 --target-tags=http-server --direction=INGRESS

gcloud compute firewall-rules create allow-https \
  --allow=tcp:443 --target-tags=https-server --direction=INGRESS
```

（`http-server`/`https-server` タグ用のルールが既に存在する場合はこのコマンドはエラーになるが、無視してよい）

### 1-4. 静的IPの予約

VMの再起動でIPが変わらないよう、外部IPを静的化する。

```bash
# 今のVMに割り当たっている一時IPを確認
gcloud compute instances describe juku-shift-vm --zone=us-west1-b \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# そのIPを静的IPとして予約（既存の一時IPをそのまま昇格）
gcloud compute addresses create juku-shift-ip \
  --region=us-west1 \
  --addresses=<上で表示されたIP>
```

### 1-5. ドメイン取得とDNS設定

- お名前.com / Cloudflare Registrar 等で取得
- Aレコードを上記の静的IPに向ける（例: `juku.example.com → 34.x.x.x`）

## 2. VM上でのセットアップ

```bash
gcloud compute ssh juku-shift-vm --zone=us-west1-b
```

（初回は鍵ペアが自動生成される。パスフレーズは空でも可）

VMに入ったら:

```bash
sudo git clone https://github.com/asa123156/juku-shift-dx.git /opt/juku-shift-dx
sudo chown -R "$USER":"$USER" /opt/juku-shift-dx
sudo bash /opt/juku-shift-dx/deploy/setup.sh
```

`setup.sh` はログインユーザー（GCPアカウント名）をそのままアプリの実行ユーザーとして使うので、Oracle向けに書かれた手順でも変更なしでそのまま動く。やること:

1. OSパッケージ（python3-venv / nodejs / caddy）のインストール
2. Python仮想環境の作成と依存インストール
3. フロントエンドのビルド（`frontend/dist` 生成）
4. `backend/.env.production` に `JWT_SECRET_KEY` を自動生成（初回のみ）
5. systemd登録: アプリ本体（`juku-shift.service`）+ 日次バックアップ（4:00、14世代）
6. Caddyの起動

最後にドメインを設定:

```bash
sudo nano /etc/caddy/Caddyfile   # juku.example.com を自分のドメインに変更
sudo systemctl reload caddy
```

ブラウザで `https://自分のドメイン/` を開き、ログイン画面が表示されれば完了。

## 3. 日常運用

[DEPLOY.md](DEPLOY.md) の「3. 日常運用」「リストア（復元）」セクションと同じ。SSHコマンドだけ以下に置き換える:

```bash
gcloud compute ssh juku-shift-vm --zone=us-west1-b
```

### VMの外へのバックアップ（推奨・任意）

```bash
# 手元のMacから
gcloud compute scp --recurse \
  juku-shift-vm:/opt/juku-shift-dx/backend/backups/ ~/juku-backups/ \
  --zone=us-west1-b
```

## 4. リージョンを変える場合（速度優先・有料）

体感速度を優先して東京リージョンにしたい場合は、VM作成時に以下を変更するだけでよい（無料枠の対象外になり、e2-micro相当で月$6〜7程度の課金が発生）:

```bash
gcloud compute instances create juku-shift-vm \
  --zone=asia-northeast1-a \
  --machine-type=e2-small \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-type=pd-balanced \
  --boot-disk-size=20GB \
  --tags=http-server,https-server
```

以降の手順（ファイアウォール・静的IP・setup.sh実行）は同じ。

## 5. ローカル開発との関係

[DEPLOY.md](DEPLOY.md) の「4. ローカル開発との関係」を参照（内容は同じ）。
