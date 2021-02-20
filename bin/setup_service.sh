#!/bin/sh

sudo bash -c "cat > /lib/systemd/system/riegocloud.service" <<'EOT'
[Unit]
Description=Riego Cloud Service
After=memcached.service
StartLimitIntervalSec=500
StartLimitBurst=5

[Service]
Environment="PYTHONUNBUFFERED=1"
Type=simple
User=riegocloud
WorkingDirectory=/srv/riegocloud
ExecStart=/srv/riegocloud/.venv/bin/riegocloud
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOT

systemctl daemon-reload
systemctl enable riegocloud
systemctl restart riegocloud
