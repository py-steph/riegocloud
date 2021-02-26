from aiohttp import web
import asyncio
import sys
import json
import asyncssh

from sqlite3 import IntegrityError
from riegocloud.db import get_db

from logging import getLogger
_log = getLogger(__name__)

router = web.RouteTableDef()


def setup_routes_api(app):
    app.add_routes(router)


@router.post("/api_20210221/", name='api')
async def api_post(request):
    options = request.app['options']
    data = await request.json()
    cloud_identifier = data.get('cloud_identifier', '')
    public_user_key = data.get('public_user_key', '')
    if not len(cloud_identifier) or not len(public_user_key):
        await asyncio.sleep(5)
        raise web.HTTPBadRequest

    cursor = get_db().conn.cursor()
    cursor.execute("""SELECT MAX(ssh_server_listen_port) AS max_port
                    FROM clients""")
    max_port = cursor.fetchone()
    max_port = max_port['max_port']
    if max_port is None or max_port == 0:
        ssh_server_listen_port = 33333
    else:
        ssh_server_listen_port = max_port + 1
    try:
        with get_db().conn:
            get_db().conn.execute(
                """INSERT INTO clients
                    ('cloud_identifier', 'public_user_key', ssh_server_listen_port,
                    ssh_server_hostname, ssh_server_port)
                    VALUES (?,?,?,?,?)""",
                (cloud_identifier, public_user_key, ssh_server_listen_port,
                 options.ssh_server_hostname, options.ssh_server_port))
    except IntegrityError:
        try:
            with get_db().conn:
                get_db().conn.execute(
                    '''UPDATE clients
                       SET public_user_key = ?,
                       SET ssh_server_listen_port = ?,
                       SET ssh_server_hostname = ?,
                       SET ssh_server_port = ?,
                       WHERE cloud_identifier = ? ''',
                    (public_user_key, ssh_server_listen_port,
                     options.ssh_server_hostname, options.ssh_server_port,
                     cloud_identifier))
        except IntegrityError as e:
            _log.error(f'Cannot update Client: {e}')
            await asyncio.sleep(5)
            raise web.HTTPBadRequest
        else:
            _log.debug(f'Updated Client: {cloud_identifier}')
    else:
        _log.debug(f'Created Client: {cloud_identifier}')

    data['ssh_server_hostname'] = options.ssh_server_hostname
    data['ssh_server_port'] = options.ssh_server_port
    data['ssh_server_listen_port'] = ssh_server_listen_port

    return web.json_response(data)
