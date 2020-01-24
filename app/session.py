import socket
import time


class ShellHandshakeFailure(ConnectionError):
    pass


class SessionHandler:

    def __init__(self, terminal_keys):
        self.terminal_keys = terminal_keys
        self.sessions = []
        self.seen_ips = set()

    async def refresh(self):
        for index, session in enumerate(self.sessions):
            try:
                session.get('connection').send(str.encode(' '))
            except socket.error:
                del self.sessions[index]

    async def accept(self, reader, writer):
        try:
            shell_info = await self._handshake(reader, writer)
        except ShellHandshakeFailure:
            return
        connection = writer.get_extra_info('socket')
        self.sessions.append(dict(id=len(self.sessions) + 1, shell_info=shell_info, connection=connection))

    async def send(self, session_id, cmd):
        conn = next(i['connection'] for i in self.sessions if i['id'] == int(session_id))
        conn.send(str.encode(' '))
        conn.send(str.encode('%s\n' % cmd))
        client_response = await self._attempt_connection(conn, 100)
        return client_response

    """ PRIVATE """

    async def _handshake(self, reader, writer):
        recv_proof = (await reader.readline()).strip()
        remote_socket = writer.get_extra_info('socket').getpeername()
        if recv_proof.decode() in self.terminal_keys:
            return (await reader.readline()).strip().decode()
        elif remote_socket[0] in self.seen_ips:
            writer.close()
            raise ShellHandshakeFailure
        else:
            self.seen_ips.add(remote_socket[0])
            writer.close()
            raise ShellHandshakeFailure

    @staticmethod
    async def _attempt_connection(connection, max_tries):
        attempts = 0
        client_response = None
        while not client_response:
            try:
                client_response = str(connection.recv(4096), 'utf-8')
            except BlockingIOError as err:
                if attempts > max_tries:
                    raise err
                attempts += 1
                time.sleep(.1 * attempts)
        return client_response
