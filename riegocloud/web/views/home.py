import aiohttp_jinja2


class Home():
    def __init__(self, app, db, security, ssh):
        self._db_conn = db.conn
        self._ssh = ssh

        self._security = security
        app.router.add_get('/', self.index, name='home')

    @aiohttp_jinja2.template('home/index.html')
    async def index(self, request):
        await self._security.raise_perm(request, perm="superuser")
        clients = self._ssh.get_clients()
        return {'clients':  clients}
