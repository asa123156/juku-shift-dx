#!/usr/bin/env bash
# JUKU-SHIFT DX を Ubuntu VM (Oracle Cloud Always Free 想定) にセットアップする。
# VM 上で、リポジトリを /opt/juku-shift-dx に clone した後に実行する:
#   sudo bash /opt/juku-shift-dx/deploy/setup.sh
set -euo pipefail

APP_DIR=/opt/juku-shift-dx
BACKEND_DIR="$APP_DIR/backend"
ENV_FILE="$BACKEND_DIR/.env.production"
RUN_USER=ubuntu

if [ "$(id -u)" -ne 0 ]; then
  echo "sudo で実行してください: sudo bash deploy/setup.sh" >&2
  exit 1
fi

echo "=== 1/6 OS パッケージ ==="
apt-get update
apt-get install -y python3-venv python3-pip nodejs npm caddy

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
cp "$APP_DIR/deploy/juku-shift.service" /etc/systemd/system/
cp "$APP_DIR/deploy/juku-shift-backup.service" /etc/systemd/system/
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
