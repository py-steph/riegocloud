#!/bin/sh

sudo bash -c "cat > /lib/systemd/system/riego-cloud.service" <<'EOT'
[Unit]
Description=Riego Cloud Service
After=memcached.service
StartLimitIntervalSec=500
StartLimitBurst=5

[Service]
Environment="PYTHONUNBUFFERED=1"
Type=simple
User=riego-cloud
WorkingDirectory=/srv/riego-cloud
ExecStart=/srv/riego-cloud/.venv/bin/riego-cloud
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOT

systemctl daemon-reload
systemctl enable riego-cloud
systemctl restart riego-cloud
