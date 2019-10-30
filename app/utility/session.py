import socket

from plugins.terminal.app.utility.console import Console


class Session:

    def __init__(self, term_svc, services, log):
        self.term_svc = term_svc
        self.services = services
        self.log = log
        self.sessions = []
        self.console = Console()

    async def accept(self, reader, writer):
        if not await self._handshake(reader, writer):
            self.console.line('Blocked an incoming reverse shell connection from {} because '
                              'it did not send a known key.\n'.format(writer.get_extra_info('socket').getpeername()))
            return
        connection = writer.get_extra_info('socket')
        paw = await self._gen_paw_print(connection)
        self.sessions.append(dict(id=len(self.sessions) + 1, paw=paw, connection=connection))
        self.console.line('New session: %s' % paw)

    async def refresh(self):
        for index, session in enumerate(self.sessions):
            try:
                session.get('connection').send(str.encode(' '))
            except socket.error:
                del self.sessions[index]

    async def has_agent(self, paw):
        agents = await self.services.get('data_svc').locate('agents')
        return next((i for i in agents if i['paw'] == paw), False)

    async def _handshake(self, reader, writer):
        client_key_hash = (await reader.read(32))
        if await self.term_svc.validate_key_hash(client_key_hash):
            return True
        else:
            return False

    @staticmethod
    async def _gen_paw_print(connection):
        paw = ''
        while True:
            try:
                data = str(connection.recv(1), 'utf-8')
                paw += data
            except BlockingIOError:
                break
        return paw
