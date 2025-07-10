import asyncio
import logging
from collections import deque
from dataclasses import dataclass
import datetime
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

HTTP_PORT = 8080
CLIENT_PORT = 8010

@dataclass
class ClientInfo:
    reader: Any
    writer: Any
    ip: str
    port: int
    connect_time: datetime.datetime
    disconnect_time: Optional[datetime.datetime] = None

clients = deque()  # Active clients
clients_lock = asyncio.Lock()

@dataclass
class SessionInfo:
    session: str
    client: ClientInfo
    init_time: datetime.datetime
    destroy_time: Optional[datetime.datetime] = None

sessions = {}  # session-id: SessionInfo
sessions_lock = asyncio.Lock()

@dataclass
class RequestInfo:
    session: SessionInfo
    method: str
    url: str
    request_time: datetime.datetime
    response_time: Optional[datetime.datetime] = None
    status_code: Optional[int] = None

requests = []  # List of RequestInfo
requests_lock = asyncio.Lock()

async def http_client_pipe(reader, writer):
    BUFFER_SIZE=1024
    SPLITER=b"\r\n"
    try:
        buffer = b""
        while True:
            data = await reader.read(BUFFER_SIZE)
            if not data:
                break
            buffer += data
            while SPLITER in buffer:
                line, buffer = buffer.split(SPLITER, 1)
                print(f"<= {line}{SPLITER}")
            if len(data)<BUFFER_SIZE:
                print(f"<= {buffer}")
                buffer=b""
            writer.write(data)
            await writer.drain()
    except Exception as e:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            pass

async def client_http_pipe(reader, writer):
    BUFFER_SIZE=1024
    SPLITER=b"\r\n"
    try:
        buffer = b""
        while True:
            data = await reader.read(BUFFER_SIZE)
            if not data:
                break
            buffer += data
            while SPLITER in buffer:
                line, buffer = buffer.split(SPLITER, 1)
                print(f"=> {line}{SPLITER}")
            if len(data)<BUFFER_SIZE:
                print(f"=> {buffer}")
                buffer=b""
            writer.write(data)
            await writer.drain()
    except Exception as e:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            pass

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    ip, port = addr if addr else ('unknown', 0)
    connect_time = datetime.datetime.now()
    client_info = ClientInfo(reader, writer, ip, port, connect_time)
    logging.info(f"[Client] Client connected: {ip}:{port} at {connect_time}")
    async with clients_lock:
        clients.append(client_info)
    try:
        await writer.wait_closed()
    finally:
        disconnect_time = datetime.datetime.now()
        client_info.disconnect_time = disconnect_time
        logging.info(f"[Client] Client disconnected: {ip}:{port} at {disconnect_time}")

async def handle_http(reader, writer):
    addr = writer.get_extra_info('peername')
    logging.info(f"[HTTP] HTTP client connected: {addr}")
    try:
        header_buffer = b""
        x_session_id = None
        method = ""
        url = ""
        while True:
            line = await reader.readline()
            if not line:
                break
            header_buffer += line
            decoded = line.decode(errors='ignore')
            if decoded.lower().startswith('x-session-id:'):
                x_session_id = decoded.split(':', 1)[1].strip()
            if not method and decoded.split():
                parts = decoded.split()
                if len(parts) >= 2 and parts[0].isalpha():
                    method = parts[0]
                    url = parts[1]
            if line == b'\r\n':
                break

        if not header_buffer:
            await _send_and_close(writer, b'HTTP/1.1 400 Bad Request\r\nContent-Length: 11\r\n\r\nBad Request')
            return

        # 1. Check sessions for active session
        client = None
        session_obj = None
        if x_session_id:
            async with sessions_lock:
                session = sessions.get(x_session_id)
                if session and session.destroy_time is None:
                    client = session.client
                session_obj = session

        # 2. If no client, poll the clients queue
        if client is None:
            async with clients_lock:
                for _ in range(len(clients)):
                    candidate = clients[0]
                    clients.rotate(-1)
                    if candidate.disconnect_time is None:
                        client = candidate
                        break

        if client is None:
            await _send_and_close(writer, b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nNo client available')
            return

        # 3. Record sessions if not exist
        if x_session_id and (not session_obj or session_obj.destroy_time is not None):
            async with sessions_lock:
                session_obj = SessionInfo(
                    session=x_session_id,
                    client=client,
                    init_time=datetime.datetime.now(),
                    destroy_time=None
                )
                sessions[x_session_id] = session_obj

        # 4. Record request
        request_obj = None
        if session_obj:
            request_obj = RequestInfo(
                session=session_obj,
                method=method,
                url=url,
                request_time=datetime.datetime.now(),
                response_time=None,
                status_code=None
            )
            async with requests_lock:
                requests.append(request_obj)

        # 5. Forward header and establish data channels
        d_reader, d_writer = client.reader, client.writer
        d_writer.write(header_buffer)
        await d_writer.drain()
        req_to_client = asyncio.create_task(http_client_pipe(reader, d_writer))
        resp_to_http = asyncio.create_task(client_http_pipe(d_reader, writer))
        done, pending = await asyncio.wait([req_to_client, resp_to_http], return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        try:
            d_writer.close()
            await d_writer.wait_closed()
        except Exception as e:
            pass
        # On session end, record destroy_time
        if x_session_id:
            async with sessions_lock:
                if x_session_id in sessions:
                    sessions[x_session_id].destroy_time = datetime.datetime.now()
        # On request end, record response_time
        if request_obj:
            async with requests_lock:
                request_obj.response_time = datetime.datetime.now()

    except Exception as e:
        logging.error(f"[HTTP] Error handling HTTP client: {e}")
        await _send_and_close(writer, b'HTTP/1.1 500 Internal Server Error\r\nContent-Length: 21\r\n\r\nInternal server error')
    finally:
        writer.close()
        await writer.wait_closed()
        logging.info(f"[HTTP] HTTP client disconnected: {addr}")

async def _send_and_close(writer, response_bytes):
    try:
        writer.write(response_bytes)
        await writer.drain()
    except Exception as e:
        pass
    writer.close()
    await writer.wait_closed()

async def log_status_periodically(interval=10):
    while True:
        async with clients_lock:
            client_infos = [
                f"ip={c.ip}, port={c.port}, connect_time={c.connect_time}, disconnect_time={c.disconnect_time}" for c in clients
            ]
        logging.info(f"[Status] Active clients: {len(clients)}\n" + "\n".join(client_infos))
        async with sessions_lock:
            session_infos = [
                f"session={s.session}, client=({s.client.ip}:{s.client.port}), init_time={s.init_time}, destroy_time={s.destroy_time}" for s in sessions.values()
            ]
        logging.info(f"[Status] Sessions: {len(session_infos)}\n" + "\n".join(session_infos))
        async with requests_lock:
            request_infos = [
                f"session={r.session.session}, method={r.method}, url={r.url}, request_time={r.request_time}, response_time={r.response_time}, status_code={r.status_code}" for r in requests
            ]
        logging.info(f"[Status] Requests: {len(request_infos)}\n" + "\n".join(request_infos))
        await asyncio.sleep(interval)

async def main():
    http_server = await asyncio.start_server(handle_http, '0.0.0.0', HTTP_PORT)
    client_server = await asyncio.start_server(handle_client, '0.0.0.0', CLIENT_PORT)
    log_task = asyncio.create_task(log_status_periodically(10))
    async with http_server, client_server:
        logging.info(f"[Client] Server started. HTTP on 0.0.0.0:{HTTP_PORT}, client on 0.0.0.0:{CLIENT_PORT}")
        await asyncio.gather(http_server.serve_forever(), client_server.serve_forever(), log_task)

if __name__ == '__main__':
    asyncio.run(main()) 