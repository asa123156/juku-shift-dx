#!/usr/bin/env bash
# JUKU-SHIFT DX を Ubuntu VM（Oracle Cloud / Google Cloud のどちらでも可）にセットアップする。
# VM 上で、リポジトリを /opt/juku-shift-dx に clone した後、そのログインユーザーで
# sudo 実行する:
#   sudo bash /opt/juku-shift-dx/deploy/setup.sh
set -euo pipefail

APP_DIR=/opt/juku-shift-dx
BACKEND_DIR="$APP_DIR/backend"
ENV_FILE="$BACKEND_DIR/.env.production"

if [ "$(id -u)" -ne 0 ]; then
  echo "sudo で実行してください: sudo bash deploy/setup.sh" >&2
  exit 1
fi

# 実行ユーザーは「このディレクトリを実際に所有しているユーザー」から判定する。
# $SUDO_USER は VM に複数のログインユーザー（例: GCP の既定 ubuntu と自分のアカウント）
# が存在すると誤判定することがあるため、$APP_DIR の所有者を正とする。
RUN_USER="$(stat -c '%U' "$APP_DIR" 2>/dev/null || echo "${SUDO_USER:-ubuntu}")"

if ! id "$RUN_USER" >/dev/null 2>&1; then
  echo "ユーザー '$RUN_USER' が見つかりません。sudo -u 付きでログインユーザーとして実行してください" >&2
  exit 1
fi

if ! id "$RUN_USER" >/dev/null 2>&1; then
  echo "ユーザー '$RUN_USER' が見つかりません。sudo -u 付きでログインユーザーとして実行してください" >&2
  exit 1
fi

echo "=== 1/6 OS パッケージ ==="
apt-get update
apt-get install -y python3-venv python3-pip caddy curl

# Vite のビルドに Node.js 20+ が必要。Ubuntu 標準の nodejs は古い（18系）ため
# NodeSource から導入する。NodeSource の nodejs は npm を同梱しているので
# npm パッケージを別途入れてはいけない（Conflicts で apt が壊れる）。
NODE_MAJOR="$(node -v 2>/dev/null | sed 's/^v\([0-9]*\).*/\1/' || echo 0)"
if [ "${NODE_MAJOR:-0}" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

echo "=== 2/6 Python 仮想環境と依存 ==="
sudo -u "$RUN_USER" python3 -m venv "$BACKEND_DIR/.venv"
sudo -u "$RUN_USER" "$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

echo "=== 3/6 フロントエンドのビルド ==="
cd "$APP_DIR/frontend"
sudo -u "$RUN_USER" npm install
sudo -u "$RUN_USER" npm run build

echo "=== 4/6 本番用シークレット (.env.production) ==="
if [ ! -f "$ENV_FILE" ]; then
  JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  cat > "$ENV_FILE" <<EOF
JWT_SECRET_KEY=$JWT_SECRET
EOF
  chown "$RUN_USER":"$RUN_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "生成しました: $ENV_FILE"
else
  echo "既存の $ENV_FILE を使います"
fi

echo "=== 5/6 systemd サービス登録 ==="
# ユニットファイルの User=ubuntu を実際のログインユーザーに置き換えて配置
sed "s/^User=ubuntu/User=$RUN_USER/" "$APP_DIR/deploy/juku-shift.service" > /etc/systemd/system/juku-shift.service
sed "s/^User=ubuntu/User=$RUN_USER/" "$APP_DIR/deploy/juku-shift-backup.service" > /etc/systemd/system/juku-shift-backup.service
cp "$APP_DIR/deploy/juku-shift-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now juku-shift.service
systemctl enable --now juku-shift-backup.timer

echo "=== 6/6 Caddy (HTTPS リバースプロキシ) ==="
if grep -q "juku.example.com" /etc/caddy/Caddyfile 2>/dev/null || [ ! -s /etc/caddy/Caddyfile ]; then
  cp "$APP_DIR/deploy/Caddyfile" /etc/caddy/Caddyfile
  echo "!!! /etc/caddy/Caddyfile の juku.example.com を自分のドメインに書き換えて、"
  echo "!!! sudo systemctl reload caddy を実行してください。"
fi
systemctl enable --now caddy

echo ""
echo "セットアップ完了。確認: curl -s http://127.0.0.1:8000/health"
