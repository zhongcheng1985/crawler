#
# pip install mysql-connector-python
#
#==========  IMPORTS AND CONFIGURATION  ==========
import asyncio
import socket
import logging
from dataclasses import dataclass
import datetime
from typing import Any, Optional, Dict, List, Tuple, Union
import uuid
import mysql.connector
from mysql.connector import pooling
import os
import json

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

#==========  CONSTANTS AND CONFIGURATION  ==========
HTTP_PORT = 8000
CLIENT_PORT = 8010

# Database configuration
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "dashboard"),
    "pool_name": "crawler_pool",
    "pool_size": 5
}

# Message delimiter
MESSAGE_DELIMITER = b'\x00\x01\x02\x03'

# Global connection pool
connection_pool = None

#==========  DATABASE FUNCTIONS  ==========
def get_db_connection() -> Optional[Union[mysql.connector.MySQLConnection, mysql.connector.pooling.PooledMySQLConnection]]:
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = pooling.MySQLConnectionPool(**db_config)
        except Exception as e:
            logging.error(f"[SERVER][DB] Failed to create connection pool: {e}")
            return None
    
    try:
        connection = connection_pool.get_connection()
        return connection
    except Exception as e:
        logging.error(f"[SERVER][DB] Failed to get connection: {e}")
        return None

#==========  JSON MESSAGE HANDLING  ==========
async def read_json_message(reader: asyncio.StreamReader) -> Optional[Dict[str, Any]]:
    """Read a JSON message from the stream reader using delimiter"""
    try:
        # Read until we find the delimiter
        buffer = b""
        while True:
            char = await reader.read(1)
            if not char:
                return None
            
            buffer += char
            
            # Check if we have the delimiter
            if buffer.endswith(MESSAGE_DELIMITER):
                # Remove delimiter and decode
                json_data = buffer[:-len(MESSAGE_DELIMITER)]
                try:
                    message = json.loads(json_data.decode('utf-8', errors='ignore'))
                    
                    # Log the received message
                    logging.info(f"[SERVER][JSON] Received: {json.dumps(message, ensure_ascii=False)}")
                    
                    return message
                except json.JSONDecodeError as e:
                    logging.error(f"[SERVER][JSON] Error parsing JSON: {e}")
                    return None
                    
    except Exception as e:
        logging.error(f"[SERVER][JSON] Error reading JSON message: {e}")
        return None

async def write_json_message(writer: asyncio.StreamWriter, msg_id: str, msg_type: str, data: Any, reply_to: Optional[str] = None) -> None:
    """Write a JSON message to the stream writer with delimiter"""
    try:
        # 直接在这里构造 JSON message
        message = {
            "id": msg_id,
            "type": msg_type,
            "time": datetime.datetime.now().isoformat(),
            "data": data
        }
        if reply_to:
            message["reply"] = reply_to
        message_str = json.dumps(message, ensure_ascii=False)
        writer.write(message_str.encode('utf-8') + MESSAGE_DELIMITER)
        await writer.drain()
        
        # Log the sent message
        addr = writer.get_extra_info('peername')
        logging.info(f"[SERVER][JSON] Sent to {addr}: {message_str}")
    except Exception as e:
        logging.error(f"[SERVER][JSON] Error writing JSON message: {e}")

#==========  DATA STRUCTURES  ==========
@dataclass
class ClientInfo:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    ip: str
    port: int
    connect_time: datetime.datetime
    disconnect_time: Optional[datetime.datetime] = None
    max_browser_count: int = 5

@dataclass
class SessionInfo:
    session_id: str
    client_ip: str
    init_time: datetime.datetime
    url: Optional[str] = None
    destroy_time: Optional[datetime.datetime] = None
    id: Optional[int] = None

@dataclass
class RequestInfo:
    session: SessionInfo
    api: Optional[str]
    request_time: datetime.datetime
    response_time: Optional[datetime.datetime] = None
    status_code: Optional[int] = None
    id: Optional[int] = None

#==========  GLOBAL STATE  ==========
clients: Dict[str, ClientInfo] = {}
clients_lock = asyncio.Lock()

sessions: Dict[Optional[str], SessionInfo] = {}
sessions_lock = asyncio.Lock()

requests: List[RequestInfo] = []
requests_lock = asyncio.Lock()

# Store pending HTTP requests waiting for response
pending_requests: Dict[str, Tuple[asyncio.StreamWriter, RequestInfo]] = {}
pending_requests_lock = asyncio.Lock()

#==========  HTTP UTILITY FUNCTIONS  ==========
async def _send_response(writer: asyncio.StreamWriter, response_bytes: bytes) -> None:
    """Send HTTP response without closing the connection"""
    try:
        # Check if writer is still open before writing
        if not writer.is_closing():
            writer.write(response_bytes)
            await writer.drain()
        else:
            logging.warning("[SERVER][HTTP] Cannot send response: writer is already closing")
    except Exception as e:
        logging.error(f"[SERVER][HTTP] Error in _send_response: {e}")

async def _close_writer(writer: asyncio.StreamWriter) -> None:
    """Close the writer connection"""
    try:
        if not writer.is_closing():
            writer.close()
            await writer.wait_closed()
    except Exception as e:
        logging.error(f"[SERVER][HTTP] Error closing writer: {e}")

#==========  CLIENT CONNECTION HANDLER  ==========
async def handle_client(clint_reader: asyncio.StreamReader,  client_writer: asyncio.StreamWriter) -> None:
    #
    sock = client_writer.get_extra_info('socket')
    if sock is not None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    #
    addr = client_writer.get_extra_info('peername')
    ip, port = addr if addr else ('unknown', 0)
    connect_time = datetime.datetime.now()
    client_info = ClientInfo(clint_reader, client_writer, ip, port, connect_time)
    logging.info(f"[SERVER][CLIENT] Client connected: {ip}:{port} at {connect_time}")
    async with clients_lock:
        clients[ip] = client_info
    #
    try:
        while True:
            # Wait for JSON request from server
            request_msg = await read_json_message(clint_reader)
            #
            if not request_msg:
                break
            #
            if request_msg.get("type") == "http.response":
                # Handle HTTP response from client
                response_msg_id = request_msg.get("reply", "")
                #
                async with pending_requests_lock:
                    if response_msg_id in pending_requests:
                        http_writer, request_obj = pending_requests.pop(response_msg_id)
                        # Decode base64 response data
                        if http_writer and request_obj:
                            try:
                                response_body_b64 = request_msg.get("data", "")
                                import base64
                                response_body = base64.b64decode(response_body_b64)
                                # Update request status (try to extract status code from response)
                                async with requests_lock:
                                    request_obj.response_time = datetime.datetime.now()
                                    # Try to extract status code from binary response
                                    try:
                                        status_line = response_body.split(b'\r\n')[0]
                                        status_code = int(status_line.split(b' ')[1])
                                        request_obj.status_code = status_code
                                    except (IndexError, ValueError):
                                        request_obj.status_code = 200  # Default status code
                                
                                # Check if writer is still open before writing
                                if not http_writer.is_closing():
                                    # Send binary HTTP response back to client
                                    await _send_response(http_writer, response_body)
                                else:
                                    logging.warning(f"[SERVER][HTTP] HTTP writer is closed, cannot send response for request: {response_msg_id}")
                                    
                            except Exception as e:
                                logging.error(f"[SERVER][HTTP] Error processing response for request {response_msg_id}: {e}")
                                # Try to send error response if writer is still open
                                try:
                                    if not http_writer.is_closing():
                                        await _send_response(http_writer, b'HTTP/1.1 500 Internal Server Error\r\nContent-Length: 21\r\n\r\nInternal server error')
                                        await _close_writer(http_writer)
                                except Exception as close_error:
                                    logging.error(f"[SERVER][HTTP] Error sending error response: {close_error}")
                        else:
                            logging.warning(f"[SERVER][HTTP] Invalid http_writer or request_obj for response: {response_msg_id}")
                    else:
                        logging.warning(f"[SERVER][HTTP] Received response for unknown request: {response_msg_id}")
            else:
                logging.warning(f"[SERVER][JSON] Unknown message type: {request_msg.get('type')}")
    except Exception as e:
        logging.error(f"[SERVER][CLIENT] Error handling client {ip}:{port}: {e}")
    finally:
        # Close client writer
        await _close_writer(client_writer)
        
        # Update client info
        disconnect_time = datetime.datetime.now()
        client_info.disconnect_time = disconnect_time
        logging.info(f"[SERVER][CLIENT] Client disconnected: {ip}:{port} at {disconnect_time}")

#==========  HTTP REQUEST HANDLER  ==========
async def handle_http(http_reader: asyncio.StreamReader,  http_writer: asyncio.StreamWriter) -> None:
    #
    addr = http_writer.get_extra_info('peername')
    logging.info(f"[SERVER][HTTP] HTTP client connected: {addr}")
    #
    try:
        while True:  # Keep connection open to handle multiple requests
            # Read HTTP request and parse content-length
            header_lines = []
            url = None
            x_session_id = None
            content_length = 0
            while True:
                line = await http_reader.readline()
                if not line:
                    break
                decoded = line.decode(errors='ignore')
                if not url and decoded.split():
                    parts = decoded.split()
                    if len(parts) >= 2 and parts[0].isalpha():
                        url = parts[1]
                if decoded.lower().startswith('x-session-id:'):
                    x_session_id = decoded.split(':', 1)[1].strip()
                if decoded.lower().startswith('content-length:'):
                    try:
                        content_length = int(decoded.split(':', 1)[1].strip())
                    except ValueError:
                        pass
                header_lines.append(line)
                if line == b'\r\n':
                    break
            
            # Check if connection is closed (no data read)
            if not header_lines:
                logging.info(f"[SERVER][HTTP] HTTP client disconnected: {addr}")
                break
            
            # Read body if present
            body_data = b""
            if content_length > 0:
                body_data = await http_reader.readexactly(content_length)

            # If there is no x_session_id in the header, generate one using uuid4
            session=None
            if url==r'/api/start' and not x_session_id :
                client = None
                async with clients_lock:
                    # Count sessions per client IP
                    client_session_counts = {}
                    async with sessions_lock:
                        for session in sessions.values():
                            if session.destroy_time is None:  # Only count active sessions
                                client_ip = session.client_ip
                                client_session_counts[client_ip] = client_session_counts.get(client_ip, 0) + 1
                    
                    # Find available client that doesn't exceed max_browser_count
                    min_session_count = float('inf')
                    for c in clients.values():
                        if c.disconnect_time is None:
                            current_count = client_session_counts.get(c.ip, 0)
                            if current_count < c.max_browser_count and current_count < min_session_count:
                                min_session_count = current_count
                                client = c
                if client is None:
                    await _send_response(http_writer, b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nNo client available')
                    await _close_writer(http_writer)
                    return

                x_session_id = str(uuid.uuid4())
                # Find the position to insert X-Session-Id header
                insert_pos = len(header_lines)  # Default: insert at the end
                for i, l in enumerate(header_lines):
                    if l == b'\r\n':
                        insert_pos = i  # Insert before the empty line
                        break
                
                # Insert X-Session-Id header
                header_lines.insert(insert_pos, f"X-Session-Id: {x_session_id}\r\n".encode())
                async with sessions_lock:
                    session = SessionInfo(
                        session_id=x_session_id,
                        client_ip=client.ip,
                        init_time=datetime.datetime.now(),
                        url=url
                    )
                    sessions[x_session_id] = session
            else:
                async with sessions_lock:
                    session = sessions.get(x_session_id)
                # Check if session is missing or destroyed
                if not session or session.destroy_time is not None:
                    await _send_response(http_writer, b'HTTP/1.1 440 Session Expired\r\nContent-Length: 16\r\n\r\nSession Expired')
                    await _close_writer(http_writer)
                    return

            # Get client and send JSON request
            client = clients.get(session.client_ip)
            if client is None:
                await _send_response(http_writer, b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nNo client available')
                await _close_writer(http_writer)
                return

            # Record request
            request_obj = RequestInfo(
                session=session,
                api=url,
                request_time=datetime.datetime.now(),
                response_time=None,
                status_code=None
            )
            async with requests_lock:
                requests.append(request_obj)

            # Create binary HTTP request data
            request_buffer = b""
            for line in header_lines:
                request_buffer += line
            if body_data:
                request_buffer += body_data
            
            # Encode binary data as base64
            import base64
            request_data = base64.b64encode(request_buffer).decode('utf-8')  # Send base64 encoded HTTP request data directly
            
            # Send JSON request to client
            msg_id = str(uuid.uuid4())
            await write_json_message(client.writer, msg_id, "http.request", request_data)
            
            # Store request info for later response handling
            async with pending_requests_lock:
                pending_requests[msg_id] = (http_writer, request_obj)

    except Exception as e:
        logging.error(f"[SERVER][HTTP] Error handling HTTP client: {e}")
        await _send_response(http_writer, b'HTTP/1.1 500 Internal Server Error\r\nContent-Length: 21\r\n\r\nInternal server error')
    finally:
        await _close_writer(http_writer)
        logging.info(f"[SERVER][HTTP] HTTP client disconnected: {addr}")

#==========  DATABASE LOGGING  ==========
async def log_status_periodically(interval: int = 10) -> None:
    """Execute database logging periodically"""
    while True:
        try:
            # Update client max_browser_count from database and update status
            async with clients_lock:
                for client in clients.values():
                    logging.info(f"[SERVER][DB] Processing client: ip={client.ip}, port={client.port}, connect_time={client.connect_time}, disconnect_time={client.disconnect_time}, max_browser_count={client.max_browser_count}")
                    try:
                        connection = get_db_connection()
                        if connection is None:
                            continue
                        cursor = connection.cursor()
                        
                        # Get or create crawler_info record
                        cursor.execute(
                            "SELECT cs.crawler_id, ci.max_browser_count FROM crawler_status cs LEFT JOIN crawler_info ci ON cs.crawler_id = ci.id WHERE cs.ip = %s",
                            (client.ip,)
                        )
                        result = cursor.fetchone()
                        
                        if result:
                            crawler_id = int(result[0])  # type: ignore
                            client.max_browser_count = int(result[1])  # type: ignore
                        else:
                            # Create new crawler_info
                            cursor.execute(
                                "INSERT INTO crawler_info (max_browser_count) VALUES (%s)",
                                (client.max_browser_count,)  # Default max_browser_count
                            )
                            connection.commit()
                            crawler_id = cursor.lastrowid
                            
                            # Immediately insert crawler_status record for new crawler_info
                            status = 10 if client.disconnect_time is None else 20  # 10: online, 20: offline
                            cursor.execute("""
                                INSERT INTO crawler_status (crawler_id, ip, last_heartbeat, status)
                                VALUES (%s, %s, %s, %s)
                            """, (crawler_id, client.ip, datetime.datetime.now(), status))
                            connection.commit()
                        
                        # Update crawler_status for existing records
                        status = 10 if client.disconnect_time is None else 20  # 10: online, 20: offline
                        
                        # Update existing record
                        cursor.execute("""
                            UPDATE crawler_status 
                            SET ip = %s, last_heartbeat = %s, status = %s, update_time = CURRENT_TIMESTAMP
                            WHERE crawler_id = %s
                        """, (client.ip, datetime.datetime.now(), status, crawler_id))
                        
                        connection.commit()
                        
                        cursor.close()
                        connection.close()
                        
                    except Exception as e:
                        logging.error(f"[SERVER][DB] Error updating client {client.ip}:{client.port} in database: {e}")
                        try:
                            if 'cursor' in locals():
                                cursor.close()
                            if 'connection' in locals() and connection:
                                connection.close()
                        except:
                            pass
            
            # Update sessions in database
            async with sessions_lock:
                # Create a copy of the values to avoid modification during iteration
                sessions_to_process = list(sessions.values())
                for session in sessions_to_process:
                    logging.info(f"[SERVER][DB] Processing session: id={session.id}, session_id={session.session_id}, client_ip={session.client_ip}, init_time={session.init_time}, url={session.url}, destroy_time={session.destroy_time}")
                    try:
                        connection = get_db_connection()
                        if connection is None:
                            continue
                        cursor = connection.cursor()
                        
                        if session.id is None:
                            # Session doesn't exist in database, get crawler_id and insert
                            cursor.execute(
                                "SELECT cs.crawler_id FROM crawler_status cs WHERE cs.ip = %s",
                                (session.client_ip,)
                            )
                            result = cursor.fetchone()
                            
                            if result:
                                crawler_id = int(result[0])  # type: ignore
                                # Insert new session
                                cursor.execute("""
                                    INSERT INTO crawler_session (crawler_id, session_id, init_time, url)
                                    VALUES (%s, %s, %s, %s)
                                """, (crawler_id, session.session_id, session.init_time, session.url))
                                connection.commit()
                                # Update the session ID in memory
                                session.id = cursor.lastrowid
                                logging.info(f"[SERVER][DB] Created new session with ID: {session.id}")
                        else:
                            # Session exists, update destroy_time if needed
                            if session.destroy_time is not None:
                                cursor.execute("""
                                    UPDATE crawler_session 
                                    SET destroy_time = %s, update_time = CURRENT_TIMESTAMP
                                    WHERE id = %s
                                """, (session.destroy_time, session.id))
                                connection.commit()
                                logging.info(f"[SERVER][DB] Updated session with ID: {session.id}")
                            
                            # If session is destroyed, remove from memory
                            if session.destroy_time is not None:
                                sessions.pop(session.session_id, None)
                                logging.info(f"[SERVER][DB] Removed destroyed session from memory: ID {session.id}")
                        
                        cursor.close()
                        connection.close()
                        
                    except Exception as e:
                        logging.error(f"[SERVER][DB] Error updating session {session.session_id} in database: {e}")
                        try:
                            if 'cursor' in locals():
                                cursor.close()
                            if 'connection' in locals() and connection:
                                connection.close()
                        except:
                            pass

                        # Update API logs in database
            async with requests_lock:
                # Create a copy of the list to avoid modification during iteration
                requests_to_process = requests.copy()
                for request in requests_to_process:
                    logging.info(f"[SERVER][DB] Processing request: id={request.id}, session_id={request.session.session_id}, api={request.api}, request_time={request.request_time}, response_time={request.response_time}, status_code={request.status_code}")
                    try:
                        connection = get_db_connection()
                        if connection is None:
                            continue
                        cursor = connection.cursor()
                        
                        # Get crawler_session_id for this request
                        cursor.execute(
                            "SELECT id FROM crawler_session WHERE session_id = %s",
                            (request.session.session_id,)
                        )
                        session_result = cursor.fetchone()
                        
                        if session_result:
                            session_id = int(session_result[0])  # type: ignore
                            
                            if request.id is None:
                                # Insert new API log
                                cursor.execute("""
                                    INSERT INTO api_log (crawler_session_id, api, request_time, response_time, status_code)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (session_id, request.api, request.request_time, request.response_time, request.status_code))
                                connection.commit()
                                # Update the request ID in memory
                                request.id = cursor.lastrowid
                                logging.info(f"[SERVER][DB] Created new API log with ID: {request.id}")
                            else:
                                # Update existing API log by ID
                                cursor.execute("""
                                    UPDATE api_log 
                                    SET response_time = %s, status_code = %s, update_time = CURRENT_TIMESTAMP
                                    WHERE id = %s
                                """, (request.response_time, request.status_code, request.id))
                                connection.commit()
                                logging.info(f"[SERVER][DB] Updated API log with ID: {request.id}")
                            
                            # If request is complete (has response_time), remove from memory
                            if request.response_time is not None:
                                requests.remove(request)
                                logging.info(f"[SERVER][DB] Removed completed request from memory: ID {request.id}")
                        
                        cursor.close()
                        connection.close()

                    except Exception as e:
                        logging.error(f"[SERVER][DB] Error updating API log for request {request.api} in database: {e}")
                        try:
                            if 'cursor' in locals():
                                cursor.close()
                            if 'connection' in locals() and connection:
                                connection.close()
                        except:
                            pass

        except Exception as e:
            logging.error(f"[SERVER][DB] Error in log_status_periodically: {e}")
        
        await asyncio.sleep(interval)

#==========  MAIN FUNCTION  ==========
async def main() -> None:
    client_server = await asyncio.start_server(handle_client, '0.0.0.0', CLIENT_PORT)
    http_server = await asyncio.start_server(handle_http, '0.0.0.0', HTTP_PORT)
    
    async with http_server, client_server:
        logging.info(f"[SERVER][MAIN] Server started. HTTP(0.0.0.0:{HTTP_PORT}), Client(0.0.0.0:{CLIENT_PORT})")
        await asyncio.gather(http_server.serve_forever(), client_server.serve_forever(),log_status_periodically(10))

if __name__ == '__main__':
    asyncio.run(main()) 