import aiohttp_jinja2
from aiohttp import web

import asyncio
import sys
import json


class System():
    def __init__(self, app, db, security, options):
        self._db_conn = db.conn
        self._security = security
        self._options = options
        app.router.add_get('/system', self._index, name='system')
        app.router.add_get("/system/check_update",
                           self._check_update, name='system_check_update')
        app.router.add_get("/system/do_update",
                           self._do_update, name='system_do_update')
        app.router.add_get("/system/restart", self._restart,
                           name='system_restart')

    @aiohttp_jinja2.template('system/index.html')
    async def _index(self, request):
        await self._security.raise_perm(request, perm='superuser')
        text = ''
        return {"text": text}

    @aiohttp_jinja2.template('system/index.html')
    async def _check_update(self, request):
        latest_version = "No Upate"
        await self._security.raise_perm(request, perm='superuser')
        proc = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', 'list', "-o", "--format=json",
            "--disable-pip-version-check",
            "--no-color",
            "--no-python-version-warning",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()
        data = json.loads(stdout)

        for item in data:
            if item['name'] == 'riegocloud':
                latest_version = item['latest_version']
                break
        return {'text':  latest_version}

    @aiohttp_jinja2.template('system/index.html')
    async def _do_update(self, request):
        await self._security.raise_perm(request, perm='superuser')
        proc = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', 'install', "riegocloud", "--upgrade",
            "--disable-pip-version-check",
            "--no-color",
            "--no-python-version-warning",
            "-q", "-q", "-q")
        await proc.wait()
        return {'text': "Restart erforderlich"}

    @aiohttp_jinja2.template('system/index.html')
    async def _restart(self, request):
        await self._security.raise_perm(request, perm='superuser')
        # TODO shedule exit for a few seconds and return a redirect
        asyncio.get_event_loop().call_later(1, exit, 0)
        raise web.HTTPSeeOther(request.app.router['system'].url_for())

    async def check_installed(self):
        version = "0.0.0"
        proc = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'pip', 'list', "--format=json",
            "--disable-pip-version-check",
            "--no-color",
            "--no-python-version-warning",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()
        data = json.loads(stdout)
        for item in data:
            if item['name'] == 'riegocloud':
                version = item['version']
                break
        return version
