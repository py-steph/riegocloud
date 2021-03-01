"""

"""

from yoyo import step

__depends__ = {'__init__'}

steps = [
    step(
    '''CREATE TABLE "users" (
	"id"	        serial,
	"identity"	    VARCHAR,
	"password"	    VARCHAR,
    "full_name"     VARCHAR,
    "email"         VARCHAR,
    "permission_id"	INTEGER,
	"is_superuser"	INTEGER DEFAULT 0,
	"is_disabled"	INTEGER DEFAULT 0,
	"remember_me"	VARCHAR,
	"created_at"	timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "identity_uc" UNIQUE("identity"),
	PRIMARY KEY("id"))''',
    '''DROP TABLE users'''
    ),
    step(
    '''INSERT INTO "users"
    ("identity","is_superuser")
    VALUES ('admin',1)''',
    """DELETE FROM users WHERE identity = 'admin' """
    ),
    step(
    ''' CREATE TABLE "users_permissions" (
	"id"	        serial,
	"name"	        VARCHAR,
	"user_id"	    INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
	"created_at"	timestamp DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id"))''',
    ''' DROP TABLE "users_permissions" '''
    ),
    step(
    ''' CREATE TABLE "users_tokens" (
	"id"	        serial,
	"sequence"	    VARCHAR NOT NULL,
    "hash"	        VARCHAR,
    "category"	    VARCHAR,
	"user_id"	    INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
	"created_at"	timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "sequence_uc" UNIQUE("sequence"),
	PRIMARY KEY("id"))''',
    ''' DROP TABLE "users_tokens" '''
    ),
    step(
    '''CREATE TABLE "clients" (
	"id"	                    serial,
	"cloud_identifier"	        VARCHAR,
    "is_disabled"               INTEGER DEFAULT 0,
	"public_user_key"    	    VARCHAR,
    "ssh_server_listen_port"    INTEGER,
  	"ssh_server_hostname"       VARCHAR,
    "ssh_server_port"           INTEGER,
	"created_at"	            timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "cloud_identifier_uc" UNIQUE("cloud_identifier"),
    CONSTRAINT "ssh_server_listen_port_uc" UNIQUE("ssh_server_listen_port"),
	PRIMARY KEY("id"))''',
    '''DROP TABLE clients'''
    )
]