import aiohttp_jinja2
from aiohttp import web

from logging import getLogger
_log = getLogger(__name__)


class Clients():
    def __init__(self, app, db, security):
        self._db_conn = db.conn
        self._security = security
        app.router.add_get('/clients', self._index, name='clients')
        app.router.add_get('/clients/new', self._new, name='clients_new')
        app.router.add_post('/clients/new', self._new_apply,)
        app.router.add_get('/clients/{item_id}',
                           self._view, name='clients_view')
        app.router.add_get('/clients/{item_id}/edit',
                           self._edit, name='clients_edit')
        app.router.add_post('/clients/{item_id}/edit', self._edit_apply)
        app.router.add_get('/clients/{item_id}/delete',
                           self._delete, name='clients_delete')

    @ aiohttp_jinja2.template("clients/index.html")
    async def _index(self, request: web.Request):
        await self._security.raise_perm(request, perm='superuser')
        cursor = self._db_conn.cursor()
        cursor.execute('SELECT * FROM clients')
        items = cursor.fetchall()
        return {"items": items}

    @ aiohttp_jinja2.template("clients/new.html")
    async def _new(self, request: web.Request):
        await self._security.raise_perm(request, perm='superuser')
        return {}

    async def _new_apply(self, request: web.Request):
        await self._security.raise_perm(request, perm='superuser')
        item = await request.post()
        cursor = self._db_conn.cursor()
        try:
            cursor.execute(
                ''' INSERT INTO clients
                    (cloud_identifier, is_disabled,
                    public_user_key, ssh_server_listen_port,
                    ssh_server_hostname, ssh_server_port)
                    VALUES (%s, %s, %s, %s, %s, %s) ''',
                (item['cloud_identifier'], item['is_disabled'],
                 item['public_user_key'], item['ssh_server_listen_port'],
                 item['ssh_server_hostname'], item['ssh_server_port']))
            self._db_conn.commit()
        except Exception as e:
            self._db_conn.rollback()
            _log.debug(f'clients add: {e}')
            raise web.HTTPSeeOther(request.app.router['clients_new'].url_for())
        item_id = str(cursor.lastrowid)
        raise web.HTTPSeeOther(
            request.app.router['clients_view'].url_for(item_id=item_id))

    @ aiohttp_jinja2.template("clients/view.html")
    async def _view(self, request: web.Request):
        await self._security.raise_perm(request, perm='superuser')
        item_id = request.match_info["item_id"]
        cursor = self._db_conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE id = %s', (item_id,))
        item = cursor.fetchone()
        if item is None:
            raise web.HTTPSeeOther(request.app.router['clients'].url_for())
        return {"item": item}

    @ aiohttp_jinja2.template("clients/edit.html")
    async def _edit(self, request: web.Request):
        await self._security.raise_perm(request, perm='superuser')
        item_id = request.match_info["item_id"]
        cursor = self._db_conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE id = %s', (item_id,))
        item = cursor.fetchone()
        if item is None:
            raise web.HTTPSeeOther(request.app.router['clients'].url_for())
        return {"item": item}

    async def _edit_apply(self, request: web.Request):
        await self._security.raise_perm(request, perm='superuser')
        item_id = request.match_info["item_id"]
        item = await request.post()
        cursor = self._db_conn.cursor()
        try:
            cursor.execute(
                '''UPDATE clients
                        SET cloud_identifier = %s, is_disabled = %s,
                        public_user_key = %s, ssh_server_listen_port = %s,
                        ssh_server_hostname = %s, ssh_server_port = %s,
                        WHERE id = %s ''',
                (item['cloud_identifier'], item['is_disabled'],
                 item['public_user_key'], item['ssh_server_listen_port'],
                 item['ssh_server_hostname'], item['ssh_server_port'],
                 item_id))
            cursor.commit()
        except Exception as e:
            _log.debug(f'clients: edit fail: {e}')
            raise web.HTTPSeeOther(
                request.app.router['clients_edit'].url_for(item_id=item_id))
        if cursor.rowcount < 1:
            _log.debug('clients: edit fail:')
            raise web.HTTPSeeOther(
                request.app.router['clients_edit'].url_for(item_id=item_id))
        raise web.HTTPSeeOther(
            request.app.router['clients_view'].url_for(item_id=item_id))

    async def _delete(self, request: web.Request):
        await self._security.raise_perm(request, perm='superuser')
        item_id = request.match_info["item_id"]
        if item_id is None or len(item_id) < 1:
            raise web.HTTPSeeOther(request.app.router['clients'].url_for())
        cursor = self._db_conn.cursor()
        try:
            cursor.execute(
                'DELETE FROM clients WHERE id = %s',
                (item_id,))
            self._db_conn.commit()
        except Exception as e:
            self._db_conn.rollback()
            _log.debug(f'clients delete fail: {e}')
            raise web.HTTPSeeOther(
                request.app.router['clients_delete'].url_for())
        if cursor.rowcount < 1:
            _log.debug('clients delete fail')
            raise web.HTTPSeeOther(
                request.app.router['clients_delete'].url_for())
        raise web.HTTPSeeOther(request.app.router['clients'].url_for())
