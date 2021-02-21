from aiohttp_session import get_session
from sqlite3 import IntegrityError, Row
from riego.db import get_db
from aiohttp import web
import bcrypt
import secrets
import json

from logging import getLogger
_log = getLogger(__name__)


async def current_user_ctx_processor(request):
    websocket_auth = '''{"token": "", "sequence": ""}'''
    user = await get_user(request)
    if user is not None:
        websocket_auth = await create_websocket_auth(request, user=user)
    return {'user': user, 'websocket_auth': json.loads(websocket_auth)}


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

    return await check_remember_me_auth(request)


def password_hash(pw):
    return bcrypt.hashpw(pw, bcrypt.gensalt(12))


def password_check(pw, pw_hash):
    return bcrypt.checkpw(pw, pw_hash)


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


async def create_websocket_auth(request: web.BaseRequest,
                                user: Row = None) -> json:
    """create token and sequence number if not exist in session. Than
    a) put token and sequence into session for using in templates
    b) put hashed token and sequence into database for later checking against
       data recived with websocket.py

    :param request: [description]
    :type request: web.BaseRequest
    :param user: [description], defaults to None
    :type user: Row, optional
    :return: [description]
    :rtype: json
    """
    if user is None:
        return None
    db = get_db()
    session = await get_session(request)
    session_key = request.app['options'].session_key_websocket_auth
    websocket_auth = session.get(session_key, '')
    if len(websocket_auth) > 0:
        return websocket_auth

    sequence = secrets.token_urlsafe()
    token = secrets.token_urlsafe()
    token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt())

    try:
        with db.conn:
            db.conn.execute('''INSERT INTO users_tokens
                                (sequence, hash, category, user_id)
                                VALUES (?, ?, ?, ?)''',
                            (sequence, token_hash, "websocket", user['id']))
    except IntegrityError as e:
        _log.error(f'Unable to insert token: {e}')
        return None
    websocket_auth = json.dumps({"sequence": sequence, "token": token})
    session[session_key] = websocket_auth
    return websocket_auth


async def delete_websocket_auth(request, user=None):
    db = get_db()
    session = await get_session(request)
    session_key = request.app['options'].session_key_websocket_auth
    if session is not None:
        session.pop(session_key, None)
    try:
        with db.conn:
            db.conn.execute('''DELETE FROM users_tokens
                               WHERE category = ? AND user_id = ?''',
                            ("websocket", user['id']))
    except IntegrityError:
        pass
    return None


async def create_remember_me_auth(request, response=None, user: Row = None):
    remember_me = secrets.token_urlsafe()
    try:
        with get_db().conn:
            get_db().conn.execute(
                '''UPDATE users
                    SET remember_me = ?
                    WHERE id = ? ''',
                (remember_me, user['id']))
    except IntegrityError:
        return None
    response.set_cookie("remember_me", remember_me,
                        max_age=request.app['options'].max_age_remember_me,
                        httponly=True,
                        samesite='strict')
    return response


async def delete_remember_me_auth(request, response=None, user: Row = None):
    if user is not None:
        try:
            with get_db().conn:
                get_db().conn.execute("""UPDATE users
                                        SET remember_me = ''
                                        WHERE id = ?""", (user['id'],))
        except IntegrityError:
            pass

    session = await get_session(request)
    session.pop('user_id', None)
#    response.set_cookie('remember_me', None,
#                        expires='Thu, 01 Jan 1970 00:00:00 GMT')
    response.del_cookie('remember_me')
    return response


async def check_remember_me_auth(request) -> Row:
    db = get_db()
    user = None
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
    return user
