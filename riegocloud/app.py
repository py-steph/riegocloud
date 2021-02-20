import asyncio
import configargparse
import pkg_resources
import os
import sys
from pathlib import Path




from riegocloud.web.views.home import Home

import logging
from logging.handlers import RotatingFileHandler

from aiohttp import web
import jinja2
import aiohttp_jinja2
import aiohttp_debugtoolbar
from aiohttp_remotes import setup as setup_remotes, XForwardedRelaxed

from riegocloud.ssh import setup_ssh

from riegocloud import __version__

PRIMARY_INI_FILE = 'riegocloud.conf'


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

    if options.enable_asyncio_debug:
        loop.set_debug(True)

    app = web.Application()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.on_cleanup.append(on_cleanup)

    app['version'] = __version__
    app['options'] = options

    loader = jinja2.FileSystemLoader(options.http_server_template_dir)
    aiohttp_jinja2.setup(app,
                         loader=loader,
                         # enable_async=True,
                         # context_processors=[current_user_ctx_processor],
                         )


    await setup_remotes(app, XForwardedRelaxed())
    if options.enable_aiohttp_debug_toolbar:
        aiohttp_debugtoolbar.setup(
            app, check_host=False, intercept_redirects=False)

    app.router.add_static('/static', options.http_server_static_dir,
                          name='static', show_index=True)

    setup_ssh(app)
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


def _get_options():
    p = configargparse.ArgParser(
        default_config_files=['/etc/riegocloud/conf.d/*.conf',
                              '~/.riegocloud.conf',
                              PRIMARY_INI_FILE],
        args_for_writing_out_config_file=['-w',
                                          '--write-out-config-file'])
    p.add('-c', '--config', is_config_file=True, env_var='RIEGO_CONF',
          required=False, help='config file path')
# Database
    p.add('-d', '--db_filename', help='Path and name for DB file',
          default='db/riegocloud.db')
    p.add('--db_migrations_dir',
          help='path to database migrations directory',
          default=pkg_resources.resource_filename('riegocloud', 'migrations'))
# Logging
    p.add('-l', '--log_file', help='Full path to logfile',
          default='log/riegocloud.log')
    p.add('--log_max_bytes', help='Maximum logfile size in bytes',
          default=1024*300, type=int)
    p.add('--log_backup_count', help='How many files to rotate',
          default=3, type=int)
# Memcache
    p.add('--memcached_host', help='IP adress of memcached host',
          default='127.0.0.1')
    p.add('--memcached_port', help='Port of memcached service',
          default=11211, type=int)
# HTTP-Server
    p.add('--http_server_bind_address',
          help='http-server bind address', default='127.0.0.1')
    p.add('--http_server_bind_port', help='http-server bind port',
          default=8181, type=int)
# Directories
    p.add('--base_dir', help='Change only if you know what you are doing',
          default=Path(__file__).parent)
    p.add('--http_server_static_dir',
          help='Serve static html files from this directory',
          default=pkg_resources.resource_filename('riegocloud.web', 'static'))
    p.add('--http_server_template_dir',
          help='Serve template files from this directory',
          default=pkg_resources.resource_filename('riegocloud.web', 'templates'))
# Debug
    p.add('--enable_aiohttp_debug_toolbar', action='store_true')
    p.add('--enable_aiohttp_access_log', action='store_true')
    p.add('--enable_asyncio_debug', action='store_true')
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
        with open(PRIMARY_INI_FILE, 'xt') as f:
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
    
    return options

