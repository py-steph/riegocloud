from jinja2 import FileSystemLoader, Environment, TemplateNotFound
import asyncio
from pathlib import Path


from logging import getLogger
_log = getLogger(__name__)

async def create_apache_conf(options=None):

    env = Environment(
        loader=FileSystemLoader(Path(options.apache_tpl_file).parent),
        autoescape=False
    )
    try: 
        template=env.get_template(Path(options.apache_tpl_file).name)
    except TemplateNotFound as e:
        _log.error(f'No template found: {e}')
        return False

    with open(options.apache_conf_file, "w") as f:
        f.write(template.render(clients=clients))

    try:
        proc = await asyncio.create_subprocess_exec(
            '/usr/bin/sudo', 
            '/usr/sbin/apachectl', 'graceful',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        print(f'stdout: {stdout}, stderr: {stderr}')
    except FileNotFoundError as e:
        print(f'Apache not reloaded: {e}')

    
    

        
class Options():

    def __init__(self):
        self.apache_tpl_file = "riegocloud/apache/apache.conf.tpl"
        self.apache_conf_file = "riegocloud/apache/apache.conf"

clients = [
    {'ssh_server_listen_port' : '33337', 'cloud_identifier' : 'ident1'},
    {'ssh_server_listen_port' : '33338', 'cloud_identifier' : 'ident2'},
    {'ssh_server_listen_port' : '33338', 'cloud_identifier' : 'ident3'},
]

async def main():
    app = {}
    options = Options()
    app['options'] = options

    await create_apache_conf(options=options)


if __name__ == "__main__":
    asyncio.run(main())