import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

DISPATCHER_HOST = '127.0.0.1'
DISPATCHER_PORT = 8010
HTTP_HOST = '127.0.0.1'
HTTP_PORT = 80
BUFFER_SIZE = 65536

async def pipe(reader, writer):
    try:
        while True:
            data = await reader.read(BUFFER_SIZE)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def handle_dispatcher_connection():
    while True:
        try:
            reader, writer = await asyncio.open_connection(DISPATCHER_HOST, DISPATCHER_PORT)
            logging.info(f"[Client] dispatcher server {DISPATCHER_HOST}:{DISPATCHER_PORT} connected, Forwarding to HTTP server {HTTP_HOST}:{HTTP_PORT}")
            while True:
                first_byte = await reader.read(1)
                if not first_byte:
                    break
                try:
                    local_reader, local_writer = await asyncio.open_connection(HTTP_HOST, HTTP_PORT)
                except Exception as e:
                    logging.error(f"[Client] Error connecting to HTTP server: {e}")
                    await drain_request(reader)
                    writer.write(b'HTTP/1.1 502 Bad Gateway\r\nContent-Length: 11\r\n\r\nBad Gateway')
                    await writer.drain()
                    continue
                local_writer.write(first_byte)
                await local_writer.drain()
                req_to_local = asyncio.create_task(pipe(reader, local_writer))
                resp_to_server = asyncio.create_task(pipe(local_reader, writer))
                done, pending = await asyncio.wait([req_to_local, resp_to_server], return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                try:
                    local_writer.close()
                    await local_writer.wait_closed()
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"[Client] Connection error: {e}. Reconnecting in 1s...")
            await asyncio.sleep(1)

def drain_request(reader):
    async def _drain():
        try:
            while True:
                data = await reader.read(BUFFER_SIZE)
                if not data:
                    break
        except Exception:
            pass
    return _drain()

if __name__ == '__main__':
    asyncio.run(handle_dispatcher_connection()) 