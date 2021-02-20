import aiohttp_jinja2


class Home():
    def __init__(self, app):
        app.router.add_get('/', self.index, name='home')


    @aiohttp_jinja2.template('home/index.html')
    async def index(self, request):
        text = "Test text"
        return {'text': text}
