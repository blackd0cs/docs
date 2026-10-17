#!/bin/bash
echo "=== Установка BootUEFI Server ==="

sudo apt update && sudo apt install -y python3-pip python3-venv git

REPO_URL="https://github.com/blackd0cs/docs.git"
INSTALL_DIR="/opt/bootuefi"

if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR" && git pull
else
    sudo git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

sudo python3 -m venv $INSTALL_DIR/.venv
sudo $INSTALL_DIR/.venv/bin/pip install --upgrade pip
sudo $INSTALL_DIR/.venv/bin/pip install -r $INSTALL_DIR/requirements.txt

sudo bash -c "cat > /etc/systemd/system/bootuefi.service" <<EOF
[Unit]
Description=BootUEFI VPS Server
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable bootuefi
sudo systemctl restart bootuefi

echo "=== ГОТОВО! Панель доступна по адресу http://IP_ТВОЕГО_VPS:8000 ==="
