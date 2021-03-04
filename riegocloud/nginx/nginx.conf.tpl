{% for client in clients %}
location /{{client['cloud_identifier']}}/  {
	proxy_pass http://127.0.0.1:{{client['ssh_server_listen_port']}}/{{client['cloud_identifier']}}/;
}
{% endfor %}
