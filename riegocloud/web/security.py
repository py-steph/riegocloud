from aiohttp_session import get_session
import aiohttp_jinja2
from sqlite3 import IntegrityError, Row
from riegocloud.db import get_db
from aiohttp import web
import bcrypt
import secrets
import json
import asyncio

from logging import getLogger
_log = getLogger(__name__)


async def current_user_ctx_processor(request):
    user = await get_user(request)
    return {'user': user}

router = web.RouteTableDef()

def setup_routes_security(app):
    app.add_routes(router)

async def get_user(request) -> Row:
    session = await get_session(request)
    db = get_db()
    user_id = session.get('user_id')
    if user_id is not None:
        cursor = db.conn.cursor()
        cursor.execute("""SELECT *, 'login' AS 'provider'
                          FROM users
                          WHERE id = ?""", (user_id,))
        user = cursor.fetchone()
        if user is None or user['is_disabled']:
            session.pop('user_id', None)
            return None
        return user
    remember_me = request.cookies.get('remember_me')
    if remember_me is not None:
        cursor = db.conn.cursor()
        cursor.execute("""SELECT *, 'cookie' AS 'provider'
                           FROM users
                           WHERE remember_me = ?""", (remember_me,))
        user = cursor.fetchone()
        if user is not None and user['is_disabled']:
            try:
                with db.conn:
                    db.conn.execute("""UPDATE users
                                       SET remember_me = ''
                                       WHERE id = ?""", (user['id'],))
            except IntegrityError:
                pass
            return None
        return user
    return None

async def check_permission(request, permission=None) -> Row:
    user = await get_user(request)
    db = get_db()
    if user is None:
        return None
    if user['is_disabled']:
        return None
    if user['is_superuser']:
        return user
    if permission is None:
        return user

    cursor = db.conn.cursor()
    cursor.execute(
        'SELECT * FROM users_permissions WHERE user_id = ?', (user['id'],))
    for row in cursor:
        if row['name'] == permission:
            return user
    return None


async def raise_permission(request: web.BaseRequest, permission: str = None):
    """Generate redirection to login form if permission is not
    sufficent. Append query string with information for redirecting
    after login to the original url.

    :param request: [description]
    :type request: web.Baserequest
    :param permission: If no permission is given, check auth only
    :type permission: str, optional
    :raises web.HTTPSeeOther: [description]
    """
    if await check_permission(request, permission=permission) is None:
        raise web.HTTPSeeOther(
            request.app.router['login'].url_for(
            ).with_query(
                {"redirect": str(request.rel_url)}
            )
        )



@router.get("/login", name='login')
@aiohttp_jinja2.template("security/login.html")
async def _login(request: web.Request):
    redirect = request.rel_url.query.get("redirect", "")
    csrf_token = secrets.token_urlsafe()
#    session = await new_session(request)
    session = await get_session(request)
    session['csrf_token'] = csrf_token
    return {'csrf_token': csrf_token, 'redirect': redirect}


@ router.post("/login")
async def _login_apply(request: web.Request):
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
    
    if user is None or user['is_disabled'] or not len(user['password']):
        await asyncio.sleep(2)
        raise web.HTTPSeeOther(request.app.router['login'].url_for())
    if not bcrypt.checkpw(form['password'].encode('utf-8'), user['password']):
        await asyncio.sleep(2)
        raise web.HTTPSeeOther(request.app.router['login'].url_for())

    session['user_id'] = user['id']

    location = form.get('redirect')
    if location is None or location == '':
        location = request.app.router['home'].url_for()
    response = web.HTTPSeeOther(location=location)
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
async def _logout(request: web.Request):
    user = await get_user(request)
    if user is not None:
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
@ aiohttp_jinja2.template("security/passwd.html")
async def _passwd(request: web.Request):
    return {}


@ router.post("/passwd")
async def _passwd_apply(request: web.Request):
    form = await request.post()
    user = await get_user(request)

# TODO check old_password and equality of pw1 an pw2
    password = form['new_password_1'].encode('utf-8')
    password = bcrypt.hashpw(password, bcrypt.gensalt(12))
    try:
        with get_db().conn:
            get_db().conn.execute(
                '''UPDATE users
                    SET password = ?
                    WHERE id = ? ''', (password, user['id']))
    except IntegrityError:
        raise web.HTTPSeeOther(request.app.router['passwd'].url_for())
    else:
        raise web.HTTPSeeOther(request.app.router['home'].url_for())
    return {}  # not reached