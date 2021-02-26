"""

"""

from yoyo import step

__depends__ = {'__init__'}

steps = [
    step(
    '''CREATE TABLE "users" (
	"id"	        INTEGER,
	"identity"	    TEXT,
	"password"	    TEXT,
    "full_name"     TEXT,
    "email"         TEXT,
    "permission_id"	INTEGER,
	"is_superuser"	INTEGER DEFAULT 0,
	"is_disabled"	INTEGER DEFAULT 0,
	"remember_me"	TEXT,
	"created_at"	timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "identity_uc" UNIQUE("identity"),
	PRIMARY KEY("id"))''',
    '''DROP TABLE users'''
    ),
    step(
    '''INSERT INTO "users"
    ("identity","password","is_superuser")
    VALUES ("admin","$2b$12$SsmDaUnej3koYln39Dq9Ue2VBjYd.FyGMeAV9kK3edRjAzLztIaCC",1)''',
      '''DELETE FROM users WHERE identity = "admin" '''
    ),
    step(
    ''' CREATE TABLE "users_permissions" (
	"id"	        INTEGER,
	"name"	        TEXT,
	"user_id"	    INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
	"created_at"	timestamp DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id"))''',
    ''' DROP TABLE "users_permissions" '''
    ),
    step(
    ''' CREATE TABLE "users_tokens" (
	"id"	        INTEGER,
	"sequence"	    TEXT NOT NULL,
    "hash"	        TEXT,
    "category"	    TEXT,
	"user_id"	    INTEGER NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
	"created_at"	timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "sequence_uc" UNIQUE("sequence"),
	PRIMARY KEY("id"))''',
    ''' DROP TABLE "users_tokens" '''
    )
]