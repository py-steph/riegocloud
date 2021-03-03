import aiohttp_jinja2

from riegocloud.web.security import raise_permission
from riegocloud.ssh import MySSHServer

class Home():
    def __init__(self, app):
        app.router.add_get('/', self.index, name='home')


    @aiohttp_jinja2.template('home/index.html')
    async def index(self, request):
        await raise_permission(request, "superuser")
        clients = MySSHServer.get_clients()
        return {'clients' :  clients}

