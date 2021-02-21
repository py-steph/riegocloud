import aiohttp_jinja2
from aiohttp import web

from riegocloud.web.security import raise_permission

import asyncio
import sys
import json

from pkg_resources import packaging

router = web.RouteTableDef()


def setup_routes_system(app):
    app.add_routes(router)


@router.get("/system", name='system')
@aiohttp_jinja2.template('system/index.html')
async def system_index(request):
    await raise_permission(request, permission=None)
    text = ''
    return {"text": text}


@router.get("/system/check_update", name='system_check_update')
@aiohttp_jinja2.template('system/index.html')
async def system_check_update(request):
    await raise_permission(request, permission=None)
    update = await _check_update("No update")
    return {'text':  update}


@router.get("/system/do_update", name='system_do_update')
@aiohttp_jinja2.template('system/index.html')
async def system_do_update(request):
    await raise_permission(request, permission=None)
    await _do_update()
    return {'text': "Restart erforderlich"}


@router.get("/system/restart", name='system_restart')
@aiohttp_jinja2.template('system/index.html')
async def system_restart(request):
    await raise_permission(request, permission=None)
    # TODO shedule exit for a few seconds and return a redirect
    asyncio.get_event_loop().call_later(1, exit, 0)
    raise web.HTTPSeeOther(request.app.router['system'].url_for())


async def _check_installed():
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


async def _check_update(latest_version=None):
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
    return latest_version


async def _do_update():
    proc = await asyncio.create_subprocess_exec(
        sys.executable, '-m', 'pip', 'install', "riegocloud", "--upgrade",
        "--disable-pip-version-check",
        "--no-color",
        "--no-python-version-warning",
        "-q", "-q", "-q")
    await proc.wait()
    exit (0)
    #return proc.returncode
