from aiohttp import web
from aiohttp_session import get_session
import aiohttp_jinja2
import bcrypt
import secrets
import asyncio

from logging import getLogger
_log = getLogger(__name__)


async def current_user_ctx_processor(request):
    user = await get_security().get_user(request)
    return {'user': user}


def get_security():
    return Security._instance


def setup_security(app, db=None):
    if Security._instance is not None:
        del Security._instance
    Security._instance = Security(app, db=db)
    return Security._instance


class Security():
    _instance = None

    def __init__(self, app, db=None):
        if Security._instance is None:
            Security._instance = self
        self._db = db
        app.router.add_get('/login', self._login, name='login')
        app.router.add_post('/login', self._login_apply)
        app.router.add_get('/logout', self._logout, name='logout')
        app.router.add_get('/profile', self._profile, name='profile')
        app.router.add_post('/profile', self._profile_apply)

    async def get_user(self, request):
        session = await get_session(request)
        conn = self._db.conn
        user_id = session.get('user_id')
        if user_id is not None:
            cursor = conn.cursor()
            cursor.execute("""SELECT *, 'login' AS provider
                            FROM users
                            WHERE id = %s""", (user_id,))
            user = cursor.fetchone()
            if user is None or user['is_disabled']:
                session.pop('user_id', None)
                return None
            return user
        remember_me = request.cookies.get('remember_me')
        if remember_me is not None:
            cursor = conn.cursor()
            cursor.execute("""SELECT *, 'cookie' AS provider
                            FROM users
                            WHERE remember_me = %s""", (remember_me,))
            user = cursor.fetchone()
            if user is not None and user['is_disabled']:
                try:
                    cursor.execute("""UPDATE users
                                    SET remember_me = ''
                                    WHERE id = %s""", (user['id'],))
                    conn.commit()
                except Exception:
                    conn.rollback()
                return None
            return user
        return None

    async def check_permission(self, request, permission=None):
        user = await self.get_user(request)
        conn = self._db.conn
        if user is None:
            return None
        if user['is_disabled']:
            return None
        if user['is_superuser']:
            return user
        if permission is None:
            return user

        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM users_permissions
                        WHERE user_id = %s''', (user['id'],))
        for row in cursor:
            if row['name'] == permission:
                return user
        return None

    async def raise_permission(self,
                               request: web.BaseRequest,
                               permission: str = None):
        """Generate redirection to login form if permission is not
        sufficent. Append query string with information for redirecting
        after login to the original url.

        :param request: [description]
        :type request: web.Baserequest
        :param permission: If no permission is given, check auth only
        :type permission: str, optional
        :raises web.HTTPSeeOther: [description]
        """
        if await self.check_permission(request, permission=permission) is None:
            raise web.HTTPSeeOther(
                request.app.router['login'].url_for(
                ).with_query(
                    {"redirect": str(request.rel_url)}
                )
            )

    @aiohttp_jinja2.template("security/login.html")
    # @router.get("/login", name='login')
    async def _login(self, request: web.Request):
        redirect = request.rel_url.query.get("redirect", "")
        csrf_token = secrets.token_urlsafe()
    #    session = await new_session(request)
        session = await get_session(request)
        session['csrf_token'] = csrf_token
        return {'csrf_token': csrf_token, 'redirect': redirect}

    async def _login_apply(self, request: web.Request):
        # @ router.post("/login")
        form = await request.post()
        session = await get_session(request)
        conn = self._db.conn
        if session.get('csrf_token') != form['csrf_token']:
            # Normally not possible
            await asyncio.sleep(2)
            raise web.HTTPUnauthorized()

        if form.get('identity') is None:
            await asyncio.sleep(2)
            raise web.HTTPSeeOther(request.app.router['login'].url_for())

        cursor = conn.cursor()
        cursor.execute("""SELECT *, 'login' AS provider
                        FROM users
                        WHERE identity = %s""", (form['identity'],))
        user = cursor.fetchone()

        if (
            user is None or
            user['is_disabled'] or
            user['password'] is None or
            not len(user['password'])
        ):
            await asyncio.sleep(2)
            raise web.HTTPSeeOther(request.app.router['login'].url_for())
        if not bcrypt.checkpw(form['password'].encode('utf-8'),
                              user['password'].encode('utf-8')):
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
                cursor.execute('''UPDATE users
                                SET remember_me = %s
                                WHERE id = %s ''', (remember_me, user['id']))
                conn.commit()
            except Exception:
                conn.rollback()
            response.set_cookie("remember_me", remember_me,
                                max_age=request.app['options'].max_age_remember_me,  # noqa: E501
                                httponly=True,
                                samesite='strict')
        return response

    async def _logout(self, request: web.Request):
        # @ router.get("/logout", name='logout')
        user = await self.get_user(request)
        conn = self._db.conn
        cursor = conn.cursor()
        if user is not None:
            try:
                cursor.execute("""UPDATE users
                                SET remember_me = ''
                                WHERE id = %s""", (user['id'],))
                conn.commit()
            except Exception:
                conn.rollback()
        session = await get_session(request)
        if session is not None:
            session.pop('user_id', None)
        response = web.HTTPSeeOther(request.app.router['login'].url_for())
    #    response.set_cookie('remember_me', None,
    #                        expires='Thu, 01 Jan 1970 00:00:00 GMT')
        response.del_cookie('remember_me')
        return response

    @ aiohttp_jinja2.template("security/profile.html")
    async def _profile(self, request: web.Request):
        # @ router.get("/profile", name='profile')
        return {}

    async def _profile_apply(self, request: web.Request):
        # @ router.post("/profile")
        form = await request.post()
        user = await self.get_user(request)

    # TODO check old_password and equality of pw1 an pw2
        password = form['new_password_1'].encode('utf-8')
        password = bcrypt.hashpw(password, bcrypt.gensalt())
        password = password.decode('utf-8')
        conn = self._db.conn
        cursor = conn.cursor()
        try:
            cursor.execute('''UPDATE users
                            SET password = %s
                            WHERE id = %s ''', (password, user['id']))
            conn.commit()
        except Exception:
            conn.rollback()
        if cursor.rowcount < 1:
            raise web.HTTPSeeOther(request.app.router['profile'].url_for())
        else:
            raise web.HTTPSeeOther(request.app.router['home'].url_for())
