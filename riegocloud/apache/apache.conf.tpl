{% for client in clients %}
<Location /{{client['cloud_identifier']}}/>
    RewriteCond %{HTTP:Upgrade} ^WebSocket$ [NC]
    RewriteCond %{HTTP:Connection} Upgrade$ [NC]
    RewriteRule .*/(.*) ws://127.0.0.1:{{client['ssh_server_listen_port']}}/{{client['cloud_identifier']}}/$1 [P,L]

    ProxyPass http://127.0.0.1:{{client['ssh_server_listen_port']}}/{{client['cloud_identifier']}}/
    ProxyPassReverse http://127.0.0.1:{{client['ssh_server_listen_port']}}/{{client['cloud_identifier']}}/
</Location>
{% endfor %}
