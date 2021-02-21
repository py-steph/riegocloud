from typing import Any, Dict
import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session

from sqlite3 import IntegrityError
from riego.db import get_db
from riego.web.security import (get_user, password_check,
                                password_hash, delete_websocket_auth)
import secrets
import asyncio


from logging import getLogger
_log = getLogger(__name__)

router = web.RouteTableDef()


def setup_routes_users(app):
    app.add_routes(router)


@router.get("/login", name='login')
@aiohttp_jinja2.template("users/login.html")
async def login(request: web.Request) -> Dict[str, Any]:
    redirect = request.rel_url.query.get("redirect", "")
    csrf_token = secrets.token_urlsafe()
#    session = await new_session(request)
    session = await get_session(request)
    session['csrf_token'] = csrf_token
    return {'csrf_token': csrf_token, 'redirect': redirect}


@ router.post("/login")
async def login_apply(request: web.Request) -> Dict[str, Any]:
    form = await request.post()
    session = await get_session(request)
    if session.get('csrf_token') != form['csrf_token']:
        # Normally not possible
        await asyncio.sleep(2)
        raise web.HTTPUnauthorized()

    if form.get('identity') is None:
        await asyncio.sleep(2)
        raise web.HTTPSeeOther(request.app.router['login'].url_for())

    cursor = get_db().conn.cursor()
    cursor.execute("""SELECT *, 'login' AS 'provider'
                    FROM users
                    WHERE identity = ?""", (form['identity'],))
    user = cursor.fetchone()

    if user is None or user['is_disabled']:
        await asyncio.sleep(2)
        raise web.HTTPSeeOther(request.app.router['login'].url_for())
#    if not bcrypt.checkpw(form['password'].encode('utf-8'), user['password']):
    if not password_check(form['password'].encode('utf-8'), user['password']):
        await asyncio.sleep(2)
        raise web.HTTPSeeOther(request.app.router['login'].url_for())

    session['user_id'] = user['id']

    location = form.get('redirect')
    if location is None or location == '':
        location = request.app.router['home'].url_for()
    response = web.HTTPSeeOther(location=location)
# TODO use create_remember_me_auth from modul security
    if form.get('remember_me') is not None:
        remember_me = secrets.token_urlsafe()
        try:
            with get_db().conn:
                get_db().conn.execute(
                    '''UPDATE users
                       SET remember_me = ?
                       WHERE id = ? ''',
                    (remember_me, user['id']))
        except IntegrityError:
            pass
        response.set_cookie("remember_me", remember_me,
                            max_age=request.app['options'].max_age_remember_me,
                            httponly=True,
                            samesite='strict')
    return response


@ router.get("/logout", name='logout')
async def logout(request: web.Request) -> Dict[str, Any]:
    user = await get_user(request)
    if user is not None:
        await delete_websocket_auth(request, user=user)
# TODO use delete_remember_me_auth from modul security
    try:
        with get_db().conn:
            get_db().conn.execute("""UPDATE users
                                     SET remember_me = ''
                                     WHERE id = ?""", (user['id'],))
    except IntegrityError:
        pass
    session = await get_session(request)
    if session is not None:
        session.pop('user_id', None)
    response = web.HTTPSeeOther(request.app.router['login'].url_for())
#    response.set_cookie('remember_me', None,
#                        expires='Thu, 01 Jan 1970 00:00:00 GMT')
    response.del_cookie('remember_me')
    return response


@ router.get("/passwd", name='passwd')
@ aiohttp_jinja2.template("users/passwd.html")
async def passwd(request: web.Request) -> Dict[str, Any]:
    return {}


@ router.post("/passwd")
async def passwd_apply(request: web.Request) -> Dict[str, Any]:
    form = await request.post()
    user = await get_user(request)

# TODO check old_password and equality of pw1 an pw2
    password = form['new_password_1'].encode('utf8')
#    password = bcrypt.hashpw(password, bcrypt.gensalt(12))
    password = password_hash(password)
    try:
        with get_db().conn:
            get_db().conn.execute(
                '''UPDATE users
                    SET password = ?
                    WHERE id = ? ''', (password, user['id']))
    except IntegrityError:
        raise web.HTTPSeeOther(request.app.router['passwd'].url_for())

    raise web.HTTPSeeOther(request.app.router['home'].url_for())
    return {}  # not reached


@ router.get("/users", name='users')
@ aiohttp_jinja2.template("users/index.html")
async def index(request: web.Request) -> Dict[str, Any]:
    cursor = get_db().conn.cursor()
    cursor.execute('SELECT * FROM users')
    items = cursor.fetchall()
    get_db().conn.commit()
    return {"items": items}


@ router.get("/users/new", name='users_new')
@ aiohttp_jinja2.template("users/new.html")
async def new(request: web.Request) -> Dict[str, Any]:
    return {}


@ router.post("/users/new")
async def new_apply(request: web.Request) -> Dict[str, Any]:
    item = await request.post()
    try:
        with get_db().conn:
            cursor = get_db().conn.execute(
                ''' INSERT INTO users
                (identity, password,
                full_name, email,
                permission_id, is_superuser,
                is_disabled, remember_me)
                VALUES (?, ?, ?, ?, ?, ?) ''',
                (item['identity'], item['password'],
                 item['full_name'], item['email'],
                 item['permission_id'], item['is_superuser'],
                 item['is_disabled'], item['remember_me']))
    except IntegrityError as e:
        _log.debug(f'users add: {e}')
        raise web.HTTPSeeOther(request.app.router['users_new'].url_for())
    else:
        item_id = str(cursor.lastrowid)
        raise web.HTTPSeeOther(
            request.app.router['users_item_view'].url_for(item_id=item_id))
    return {}  # not reached


@ router.get("/users/{item_id}", name='users_item_view')
@ aiohttp_jinja2.template("users/view.html")
async def view(request: web.Request) -> Dict[str, Any]:
    item_id = request.match_info["item_id"]
    cursor = get_db().conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id=?', (item_id,))
    item = cursor.fetchone()
    get_db().conn.commit()
    if item is None:
        raise web.HTTPSeeOther(request.app.router['users'].url_for())
    return {"item": item}


@ router.get("/users/{item_id}/edit", name='users_item_edit')
@ aiohttp_jinja2.template("users/edit.html")
async def edit(request: web.Request) -> Dict[str, Any]:
    item_id = request.match_info["item_id"]
    cursor = get_db().conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id=?', (item_id,))
    item = cursor.fetchone()
    get_db().conn.commit()
    if item is None:
        raise web.HTTPSeeOther(request.app.router['users'].url_for())
    return {"item": item}


@ router.post("/users/{item_id}/edit")
async def edit_apply(request: web.Request) -> web.Response:
    item_id = request.match_info["item_id"]
    item = await request.post()
    try:
        with get_db().conn:
            get_db().conn.execute(
                '''UPDATE users
                   SET identity = ?, password = ?,
                   full_name = ?, email = ?,
                   permission_id = ?, is_superuser = ?,
                   is_disabled = ?, remember_me = ?
                   WHERE id = ? ''',
                (item['identity'], item['password'],
                 item['full_name'], item['email'],
                 item['permission_id'], item['is_superuser'],
                 item['is_disabled'], item['remember_me'],
                 item_id))
    except IntegrityError as e:
        _log.debug(f'box.view edit: {e}')
        raise web.HTTPSeeOther(
            request.app.router['users_item_edit'].url_for(item_id=item_id))
    else:
        raise web.HTTPSeeOther(
            request.app.router['users_item_view'].url_for(item_id=item_id))
    return {}  # Not reached


@ router.get("/users/{item_id}/delete", name='users_item_delete')
async def delete(request: web.Request) -> web.Response:
    item_id = request.match_info["item_id"]
    try:
        with get_db().conn:
            get_db().conn.execute(
                'DELETE FROM users WHERE id = ?',
                (item_id,))
    except IntegrityError as e:
        _log.debug(f'users  delete: {e}')
    raise web.HTTPSeeOther(request.app.router['users'].url_for())
    return {}  # Not reached
