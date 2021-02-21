import setuptools
from riegocloud.__init__ import __version__


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="riegocloud",
    version=__version__,
    author="Stephan Winter",
    author_email="riego@finca-panorama.es",
    url="https://github.com/py-steph/riegocloud",
    description="Riego Cloud Service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=[
        'ConfigArgParse',
        'aiohttp',
        'aiohttp_jinja2',
        'aiohttp_remotes',
        'aiohttp_session[aiomcache]',
        'aiohttp_debugtoolbar',
        'uvloop; sys_platform == "linux"',
        'yoyo-migrations',
        'bcrypt',
        'cchardet',
        'asyncssh',
    ],
    include_package_data=True,
    scripts=['bin/setup_service.sh'],
    entry_points={
        'console_scripts': ['riegocloud=riegocloud.app:main'],
    },
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Framework :: AsyncIO",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.7',
    zip_safe=False,
)
