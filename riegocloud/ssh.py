import asyncio, asyncssh, sys

passwords = {'guest': '',                 # guest account with no password
             'user123': 'user123'   # password of 'secretpw'
            }

def handle_client(process):
    process.stdout.write('Welcome to my SSH server, %s!\n' %
                         process.get_extra_info('username'))
    process.exit(0)

class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        print('SSH connection received from %s.' %
                  conn.get_extra_info('peername')[0])

    def connection_lost(self, exc):
        if exc:
            print('SSH connection error: ' + str(exc), file=sys.stderr)
        else:
            print('SSH connection closed.')

    def begin_auth(self, username):
        # If the user's password is the empty string, no auth is required
        return passwords.get(username) != ''

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        pw = passwords.get(username, '*')
        # return crypt.crypt(password, pw) == pw
        return True

async def start_server():
    await asyncssh.create_server(MySSHServer, '', 8022,
                                 server_host_keys=['ssh/ssh_host_key'],
                                 process_factory=handle_client)

def setup_ssh(app):
    app.cleanup_ctx.append(sshd_engine)

async def sshd_engine(app):
    task = asyncio.create_task(start_server())
    yield
    task.cancel()

if __name__ == "__main__":

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(start_server())
    except (OSError, asyncssh.Error) as exc:
        sys.exit('Error starting server: ' + str(exc))
    
    loop.run_forever()