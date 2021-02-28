import asyncio
import configargparse
import pkg_resources
import os
import sys
from pathlib import Path

import logging
from logging.handlers import RotatingFileHandler

from aiohttp import web
import aiohttp_jinja2
import jinja2
import aiohttp_debugtoolbar
from aiohttp_remotes import setup as setup_remotes, XForwardedRelaxed
from aiohttp_session import setup as session_setup, get_session
from aiohttp_session.memcached_storage import MemcachedStorage
import aiomcache


from riegocloud.web.views.home import Home
from riegocloud.web.views.system import setup_routes_system
from riegocloud.web.views.api import setup_routes_api
from riegocloud.web.security import current_user_ctx_processor, setup_routes_security

from riegocloud.ssh import setup_ssh
from riegocloud.db import setup_db

from riegocloud import __version__

app_name = 'riegocloud'


async def on_startup(app):
    logging.getLogger(__name__).debug("on_startup")


async def on_shutdown(app):
    logging.getLogger(__name__).debug("on_shutdown")


async def on_cleanup(app):
    logging.getLogger(__name__).debug("on_cleanup")


def main():
    options = _get_options()

    _setup_logging(options=options)

    if sys.version_info >= (3, 8) and options.WindowsSelectorEventLoopPolicy:
        asyncio.DefaultEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy  # noqa: E501

    if os.name == "posix":
        import uvloop  # pylint: disable=import-error
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    web.run_app(run_app(options=options),
                host=options.http_server_bind_address,
                port=options.http_server_bind_port)


async def run_app(options=None):
    loop = asyncio.get_event_loop()

    if options.enable_asyncio_debug_log:
        loop.set_debug(True)

    app = web.Application()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.on_cleanup.append(on_cleanup)

    app['version'] = __version__
    app['options'] = options

    mcache = aiomcache.Client(options.memcached_host, options.memcached_port)
    session_setup(app, MemcachedStorage(mcache))

    async def mcache_shutdown(app):
        await mcache.close()
    app.on_shutdown.append(mcache_shutdown)

    loader = jinja2.FileSystemLoader(options.http_server_template_dir)
    aiohttp_jinja2.setup(app,
                         loader=loader,
                         # enable_async=True,
                         context_processors=[current_user_ctx_processor],
                         )

    await setup_remotes(app, XForwardedRelaxed())
    if options.enable_aiohttp_debug_toolbar:
        aiohttp_debugtoolbar.setup(
            app, check_host=False, intercept_redirects=False)

    app.router.add_static('/static', options.http_server_static_dir,
                          name='static', show_index=True)

    db = setup_db(options=options)
    setup_ssh(app, options=options, db=db)
    setup_routes_security(app)
    setup_routes_system(app)
    setup_routes_api(app)

    Home(app)

    return app


def _setup_logging(options=None):
    formatter = logging.Formatter(
        "%(asctime)s;%(levelname)s;%(name)s;%(message)s ")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    Path(options.log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(options.log_file, mode='a',
                                       maxBytes=options.log_max_bytes,
                                       backupCount=options.log_backup_count,
                                       encoding=None, delay=0)
    file_handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[stream_handler, file_handler])

    if options.enable_aiohttp_access_log:
        logging.getLogger("aiohttp.access").setLevel(logging.DEBUG)
    else:
        logging.getLogger("aiohttp.access").setLevel(logging.ERROR)

    if options.enable_ssh_debug_log:
        logging.getLogger("asyncssh").setLevel(logging.DEBUG)
    else:
        logging.getLogger("asyncssh").setLevel(logging.ERROR)


def _get_options():
    p = configargparse.ArgParser(
        default_config_files=[f'/etc/{app_name}/conf.d/*.conf',
                              f'~/.{app_name}.conf',
                              f'{app_name}.conf'],
        args_for_writing_out_config_file=['-w',
                                          '--write-out-config-file'])
    p.add('-c', '--config', is_config_file=True, env_var=app_name.capitalize(),
          required=False, help='config file path')
# Database
    p.add('-d', '--db_filename', help='Path and name for DB file',
          default=f'db/{app_name}.db')
    p.add('--db_migrations_dir',
          help='path to database migrations directory',
          default=pkg_resources.resource_filename(app_name, 'migrations'))
# Logging
    p.add('-l', '--log_file', help='Full path to logfile',
          default=f'log/{app_name}.log')
    p.add('--log_max_bytes', help='Maximum logfile size in bytes',
          default=1024*300, type=int)
    p.add('--log_backup_count', help='How many files to rotate',
          default=3, type=int)
# Secrets & Scurity
    p.add('--max_age_remember_me', type=int, default=7776000)
    p.add('--cookie_name_remember_me', default="remember_me")
    p.add('--reset_admin', help='Reset admin-pw to given value an exit')
# Memcache
    p.add('--memcached_host', help='IP adress of memcached host',
          default='127.0.0.1')
    p.add('--memcached_port', help='Port of memcached service',
          default=11211, type=int)
# HTTP-Server / API
    p.add('--http_server_bind_address',
          help='http-server bind address', default='127.0.0.1')
    p.add('--http_server_bind_port', help='http-server bind port',
          default=8181, type=int)
    p.add('--ssh_server_hostname', help='Send this hostname to client',
          default="cloud.finca-panorama.es")
    p.add('--ssh_server_port', help='Send this port to client',
          default=8022, type=int)
# SSH-Server
    p.add('--ssh_server_bind_port', help='ssh-server bind port',
          default=8022, type=int)
    p.add('--ssh_server_bind_address', help='ssh-server bind address',
          default='0.0.0.0')
    p.add('--ssh_host_key',
          help='ssh Host key', default='ssh/ssh_host_key')
# Apache patching
    p.add('--apache_tpl_file', help='path to apache config template(s)',
          default=pkg_resources.resource_filename(
              app_name, 'apache/apache.conf.tpl'))
    p.add('--apache_conf_file', help='path to apache config file',
          default=pkg_resources.resource_filename(
              app_name, 'apache/apache.conf'))

# Directories
    p.add('--base_dir', help='Change only if you know what you are doing',
          default=Path(__file__).parent)
    p.add('--http_server_static_dir',
          help='Serve static html files from this directory',
          default=pkg_resources.resource_filename(f'{app_name}.web', 'static'))
    p.add('--http_server_template_dir',
          help='Serve template files from this directory',
          default=pkg_resources.resource_filename(f'{app_name}.web', 'templates'))
# Debug
    p.add('--enable_aiohttp_debug_toolbar', action='store_true')
    p.add('--enable_aiohttp_access_log', action='store_true')
    p.add('--enable_asyncio_debug_log', action='store_true')
    p.add('--enable_ssh_debug_log', action='store_true')
    p.add('--WindowsSelectorEventLoopPolicy', action='store_true')

# Version, Help, Verbosity
    p.add('-v', '--verbose', help='verbose', action='store_true')
    p.add('--version', help='Print version and exit', action='store_true')
    p.add('--defaults', help='Print options with default values and exit',
          action='store_true')

    options = p.parse_args()
    if options.verbose:
        print(p.format_values())

    try:
        with open(f'{app_name}.conf', 'xt') as f:
            for item in vars(options):
                f.write(f'# {item}={getattr(options, item)}\n')
    except IOError:
        pass

    if options.defaults:
        for item in vars(options):
            print(f'# {item}={getattr(options, item)}')
        exit(0)

    if options.version:
        print('Version: ', __version__)
        exit(0)

    if options.reset_admin:
        _reset_admin(options)
        exit(0)

    return options


def _reset_admin(options):
    from sqlite3 import IntegrityError
    from riegocloud.db import setup_db
    import bcrypt

    db = setup_db(options=options)
    password = options.reset_admin

    if len(password) > 0:
        password = password.encode('utf-8')
        password = bcrypt.hashpw(password, bcrypt.gensalt(12))
        try:
            with db.conn:
                db.conn.execute(
                    '''UPDATE users
                        SET password = ?
                        WHERE id = ? ''', (password, 1))
        except IntegrityError as e:
            print(f'Unable to reset Admin PW: {e}')
        else:
            print(f'Succesfully reset Admin PW: {password}')
    db.conn.close()
