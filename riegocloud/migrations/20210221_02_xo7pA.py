"""

"""

from yoyo import step

__depends__ = {'20210221_01_PpQ5x'}

steps = [
    step(
    '''CREATE TABLE "clients" (
	"id"	                    INTEGER,
	"cloud_identifier"	        TEXT,
	"public_user_key"    	    TEXT,
    "ssh_server_listen_port"    INTEGER,
  	"ssh_server_hostname"       TEXT,
    "ssh_server_port"           INTEGER,
	"created_at"	            timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "cloud_identifier_uc" UNIQUE("cloud_identifier"),
    CONSTRAINT "ssh_server_listen_port_uc" UNIQUE("ssh_server_listen_port"),
	PRIMARY KEY("id"))''',
    '''DROP TABLE clients'''
    )
]
