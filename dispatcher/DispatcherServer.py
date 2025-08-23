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
    connect_time: datetime.datetime
    disconnect_time: Optional[datetime.datetime] = None
    max_browser_count: int = 5
    # Fields corresponding to crawler_info table
    uuid: Optional[str] = None
    host_name: Optional[str] = None
    internal_ip: Optional[str] = None
    external_ip: Optional[str] = None
    os: Optional[str] = None
    agent: Optional[str] = None
    last_heartbeat: Optional[datetime.datetime] = None
    status: int = 10  # 10:online, 20:offline, 30:shutdown
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None

@dataclass
class SessionInfo:
    uuid: str
    client_uuid: str
    init_time: datetime.datetime
    url: Optional[str] = None
    destroy_time: Optional[datetime.datetime] = None

@dataclass
class LogInfo:
    uuid: str
    session_uuid: str
    url: Optional[str]
    request_time: datetime.datetime
    response_time: Optional[datetime.datetime] = None
    status_code: Optional[int] = None
    id: Optional[int] = None

#==========  GLOBAL STATE  ==========
clients: Dict[str, ClientInfo] = {}
clients_lock = asyncio.Lock()

sessions: Dict[Optional[str], SessionInfo] = {}
sessions_lock = asyncio.Lock()

logs: List[LogInfo] = []
logs_lock = asyncio.Lock()

# Store pending HTTP requests waiting for response
pending_requests: Dict[str, Tuple[asyncio.StreamWriter, LogInfo]] = {}
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

async def _read_until_delimiter(reader: asyncio.StreamReader, delimiter: str = '\r\n', timeout: float = 10.0, max_size: int = 8192) -> Optional[bytes]:
    """Read data until a specific delimiter is found with timeout and maximum buffer size"""
    try:
        delimiter_bytes = delimiter.encode('utf-8')
        buffer = b""
        
        # Use asyncio.wait_for to add timeout
        while True:
            # Read one byte at a time to find delimiter
            char = await asyncio.wait_for(reader.read(1), timeout=timeout)
            if not char:
                return buffer if buffer else None  # Return buffer if we have data, None if empty
                
            # Add char to buffer
            buffer += char
            
            # Check if buffer length reaches max_size or ends with delimiter
            if len(buffer) >= max_size or buffer.endswith(delimiter_bytes):
                return buffer
                
    except Exception as e:
        logging.error(f"[SERVER][HTTP] Error reading data: {e}")
        return buffer if buffer else None

#==========  CLIENT CONNECTION HANDLER  ==========
async def handle_client(clint_reader: asyncio.StreamReader,  client_writer: asyncio.StreamWriter) -> None:
    # Immediately read and check MESSAGE_DELIMITER
    try:
        delimiter = await clint_reader.readexactly(len(MESSAGE_DELIMITER))
        if delimiter != MESSAGE_DELIMITER:
            logging.warning(f"[SERVER][CLIENT] Invalid initial delimiter, closing connection.")
            await _close_writer(client_writer)
            return
    except Exception as e:
        logging.error(f"[SERVER][CLIENT] Error reading initial delimiter: {e}")
        await _close_writer(client_writer)
        return
    
    # Read heartbeat message after MESSAGE_DELIMITER
    try:
        heartbeat_msg = await read_json_message(clint_reader)
        if not heartbeat_msg or heartbeat_msg.get("type") != "dispatcher.heartbeat":
            logging.warning(f"[SERVER][CLIENT] Invalid or missing heartbeat message, closing connection.")
            await _close_writer(client_writer)
            return
        
        heartbeat_data = heartbeat_msg.get("data", {})
        logging.info(f"[SERVER][CLIENT] Received heartbeat: {json.dumps(heartbeat_data, ensure_ascii=False)}")
    except Exception as e:
        logging.error(f"[SERVER][CLIENT] Error reading heartbeat message: {e}")
        await _close_writer(client_writer)
        return
    
    #
    sock = client_writer.get_extra_info('socket')
    if sock is not None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    #
    addr = client_writer.get_extra_info('peername')
    ip, port = addr if addr else ('unknown', 0)
    connect_time = datetime.datetime.now()
    client_info = ClientInfo(clint_reader, client_writer, connect_time)
    
    # Update client info with heartbeat data
    client_uuid = heartbeat_data.get("uuid")
    client_info.uuid = client_uuid
    client_info.os = heartbeat_data.get("os")
    client_info.agent = heartbeat_data.get("agent")
    client_info.host_name = heartbeat_data.get("host_name")
    client_info.internal_ip = heartbeat_data.get("ip")
    client_info.external_ip = ip
    client_info.cpu_usage = heartbeat_data.get("cpu_usage")
    client_info.memory_usage = heartbeat_data.get("memory_usage")
    client_info.last_heartbeat = connect_time
    
    logging.info(f"[SERVER][CLIENT] Client connected: {ip}:{port} at {connect_time}")
    async with clients_lock:
        clients[client_uuid] = client_info
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
                                                        # Update log status (try to extract status code from response)
                                async with logs_lock:
                                    request_obj.response_time = datetime.datetime.now()
                                    # Try to extract status code from binary response
                                    try:
                                        status_line = response_body.split(b'\r\n')[0]
                                        status_code = int(status_line.split(b' ')[1])
                                        request_obj.status_code = status_code
                                    except (IndexError, ValueError):
                                        request_obj.status_code = 200  # Default status code
                                
                                # --- New logic: update session destroy_time if api is /api/destroy ---
                                if request_obj.url == "/api/destroy":
                                    async with sessions_lock:
                                        session = sessions.get(request_obj.session_uuid)
                                        if session and session.destroy_time is None:
                                            session.destroy_time = datetime.datetime.now()
                                            logging.info(f"[SERVER][SESSION] Set destroy_time for session {session.uuid} due to /api/destroy response.")
                                # ---------------------------------------------------------------
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
            elif request_msg.get("type") == "dispatcher.heartbeat":
                # Handle heartbeat message from client and update ClientInfo
                heartbeat_data = request_msg.get("data", {})
                now = datetime.datetime.now()
                # Update client_info fields with new heartbeat data
                client_info.os = heartbeat_data.get("os")
                client_info.agent = heartbeat_data.get("agent")
                client_info.host_name = heartbeat_data.get("host_name")
                client_info.internal_ip = heartbeat_data.get("ip")
                # external_ip is set at connect time and not updated here
                client_info.cpu_usage = heartbeat_data.get("cpu_usage")
                client_info.memory_usage = heartbeat_data.get("memory_usage")
                client_info.last_heartbeat = now
                # Log the heartbeat update
                logging.info(f"[SERVER][CLIENT] Heartbeat updated for client {client_info.uuid} at {now}: {json.dumps(heartbeat_data, ensure_ascii=False)}")
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
            request_lines = []
            
            # Read request line first and validate HTTP protocol start
            url = None
            try:
                line = await _read_until_delimiter(http_reader, delimiter='\r\n', timeout=10.0, max_size=8192)
                if not line:
                    logging.info(f"[SERVER][HTTP] HTTP client disconnected: {addr}")
                    break
                
                # Simple parse: get method and url
                parts = line.decode(errors='ignore').strip().split()
                if len(parts) < 2:
                    logging.warning(f"[SERVER][HTTP] Invalid request format from {addr}")
                    await _close_writer(http_writer)
                    break
                
                method, url = parts[0], parts[1]
                
                # Check if method is supported (only GET and POST allowed)
                if method.upper() not in ['GET', 'POST']:
                    logging.warning(f"[SERVER][HTTP] Unsupported HTTP method '{method}' from {addr}")
                    await _close_writer(http_writer)
                    break
                
                request_lines.append(line)
                
            except Exception as e:
                logging.error(f"[SERVER][HTTP] Error parsing request from {addr}: {e}")
                await _close_writer(http_writer)
                break
            
            # Read headers
            x_session_id = None
            content_length = 0
            connection_close = None
            while True:
                line = await _read_until_delimiter(http_reader, delimiter='\r\n', timeout=10.0, max_size=8192)
                if not line:
                    logging.warning(f"[SERVER][HTTP] Connection closed while reading headers from {addr}")
                    break
                
                decoded = line.decode(errors='ignore')
                
                # Check for end of headers
                if line == b'\r\n':
                    if connection_close is None:
                        request_lines.append(b'Connection: close\r\n')
                    request_lines.append(line)
                    break
                
                # Parse specific headers
                if decoded.lower().startswith('x-session-id:'):
                    x_session_id = decoded.split(':', 1)[1].strip()
                elif decoded.lower().startswith('content-length:'):
                    try:
                        content_length = int(decoded.split(':', 1)[1].strip())
                    except ValueError:
                        pass
                elif decoded.lower().startswith('connection:'):
                    connection_close = decoded[len('connection:'):].strip()
                    request_lines.append(b'Connection: close\r\n')
                    continue
                
                request_lines.append(line)
            
            # Check if connection is closed
            if not request_lines:
                logging.info(f"[SERVER][HTTP] HTTP client disconnected: {addr}")
                break

            # Read body if present
            body_data = b""
            if content_length > 0:
                try:
                    body_data = await asyncio.wait_for(http_reader.readexactly(content_length), timeout=10.0)
                except Exception as e:
                    logging.error(f"[SERVER][HTTP] Error reading body from {addr}: {e}")
                    await _close_writer(http_writer)
                    return

            # If there is no x_session_id in the header, generate one using uuid4
            session=None
            if url==r'/api/start' and not x_session_id :
                client = None
                async with clients_lock:
                    # Count sessions per client UUID
                    client_session_counts = {}
                    async with sessions_lock:
                        for session in sessions.values():
                            if session.destroy_time is None:  # Only count active sessions
                                client_uuid = session.client_uuid
                                client_session_counts[client_uuid] = client_session_counts.get(client_uuid, 0) + 1
                    
                    # Find available client that doesn't exceed max_browser_count
                    min_session_count = float('inf')
                    for c in clients.values():
                        if c.disconnect_time is None:
                            current_count = client_session_counts.get(c.uuid, 0)
                            if current_count < c.max_browser_count and current_count < min_session_count:
                                min_session_count = current_count
                                client = c
                if client is None:
                    await _send_response(http_writer, b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nNo client available')
                    await _close_writer(http_writer)
                    return

                x_session_id = str(uuid.uuid4())
                # Find the position to insert X-Session-Id header
                insert_pos = len(request_lines)  # Default: insert at the end
                for i, l in enumerate(request_lines):
                    if l == b'\r\n':
                        insert_pos = i  # Insert before the empty line
                        break
                
                # Insert X-Session-Id header
                request_lines.insert(insert_pos, f"X-Session-Id: {x_session_id}\r\n".encode())
                async with sessions_lock:
                    session = SessionInfo(
                        uuid=x_session_id,
                        client_uuid=client.uuid,  # Use the UUID from the clients dict key
                        init_time=datetime.datetime.now(),
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
                
            if url==r'/api/go' :
                body = json.loads(body_data.decode('utf-8', errors='ignore'))
                session.url=body.get('url')

            # Get client and send JSON request
            client = clients.get(session.client_uuid)
            if client is None:
                await _send_response(http_writer, b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nNo client available')
                await _close_writer(http_writer)
                return

            # Create binary HTTP request data
            request_buffer = b""
            for line in request_lines:
                request_buffer += line
            if body_data:
                request_buffer += body_data
            
            # Encode binary data as base64
            import base64
            request_data = base64.b64encode(request_buffer).decode('utf-8')  # Send base64 encoded HTTP request data directly
            
            # Send JSON request to client
            msg_id = str(uuid.uuid4())
            await write_json_message(client.writer, msg_id, "http.request", request_data)
            
            # Record request
            request_obj = LogInfo(
                uuid=msg_id,  # Use the msg_id as the uuid
                session_uuid=session.uuid,
                url=url,
                request_time=datetime.datetime.now(),
                response_time=None,
                status_code=None
            )
            async with logs_lock:
                logs.append(request_obj)
            
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
                    logging.info(f"[SERVER][DB] Processing client: uuid={client.uuid}, connect_time={client.connect_time}, disconnect_time={client.disconnect_time}, max_browser_count={client.max_browser_count}")
                    try:
                        connection = get_db_connection()
                        if connection is None:
                            continue
                        cursor = connection.cursor()
                        
                        # Try to update existing crawler_info by UUID
                        status = 10 if client.disconnect_time is None else 20  # 10: online, 20: offline
                        cursor.execute(
                            "UPDATE crawler_info SET host_name = %s, internal_ip = %s, external_ip = %s, os = %s, agent = %s, last_heartbeat = %s, status = %s, cpu_usage = %s, memory_usage = %s, update_time = %s WHERE uuid = %s",
                            (client.host_name, client.internal_ip, client.external_ip, client.os, client.agent, client.last_heartbeat, status, client.cpu_usage, client.memory_usage, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client.uuid)
                        )
                        
                        if cursor.rowcount > 0:
                            # Record was updated, get max_browser_count from crawler_setting
                            cursor.execute(
                                "SELECT max_browser_count FROM crawler_setting WHERE crawler_id = (SELECT id FROM crawler_info WHERE uuid = %s)",
                                (client.uuid,)
                            )
                            setting_result = cursor.fetchone()
                            if setting_result and setting_result[0] is not None:
                                try:
                                    client.max_browser_count = int(setting_result[0])  # type: ignore
                                    logging.info(f"[SERVER][DB] Updated max_browser_count to {client.max_browser_count} for client {client.uuid}")
                                except (ValueError, TypeError):
                                    logging.warning(f"[SERVER][DB] Invalid max_browser_count value for client {client.uuid}: {setting_result[0]}")
                            
                            connection.commit()
                            logging.info(f"[SERVER][DB] Updated existing crawler_info with UUID: {client.uuid}")
                        else:
                            # No record was updated, create new crawler_info
                            cursor.execute(
                                "INSERT INTO crawler_info (uuid, host_name, internal_ip, external_ip, os, agent, last_heartbeat, status, cpu_usage, memory_usage, create_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (client.uuid, client.host_name, client.internal_ip, client.external_ip, client.os, client.agent, client.last_heartbeat, status, client.cpu_usage, client.memory_usage, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            )
                            connection.commit()
                            crawler_id = cursor.lastrowid
                            
                            # Create crawler_setting record for new crawler_info
                            cursor.execute(
                                "INSERT INTO crawler_setting (crawler_id, max_browser_count, create_time) VALUES (%s, %s, %s)",
                                (crawler_id, client.max_browser_count, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            )
                            connection.commit()
                            logging.info(f"[SERVER][DB] Created new crawler_info with ID: {crawler_id}")
                        
                        cursor.close()
                        connection.close()
                        
                    except Exception as e:
                        logging.error(f"[SERVER][DB] Error updating client {client.uuid} in database: {e}")
                        try:
                            if 'cursor' in locals():
                                cursor.close()
                            if 'connection' in locals() and connection:
                                connection.close()
                        except Exception as cleanup_error:
                            logging.error(f"[SERVER][DB] Error during cleanup: {cleanup_error}")
            
            # Update sessions in database
            async with sessions_lock:
                # Create a copy of the items to avoid modification during iteration
                for session in sessions.values():
                    logging.info(f"[SERVER][DB] Processing session: uuid={session.uuid}, client_uuid={session.client_uuid}, init_time={session.init_time}, url={session.url}, destroy_time={session.destroy_time}")
                    try:
                        connection = get_db_connection()
                        if connection is None:
                            continue
                        cursor = connection.cursor()
                        
                        # First check if crawler_info exists for this session's client_uuid
                        cursor.execute(
                            "SELECT id FROM crawler_info WHERE uuid = %s",
                            (session.client_uuid,)
                        )
                        crawler_result = cursor.fetchone()
                        
                        if not crawler_result:
                            # crawler_info doesn't exist, skip this session
                            logging.warning(f"[SERVER][DB] Skipping session {session.uuid}: crawler_info not found for client_uuid {session.client_uuid}")
                            cursor.close()
                            connection.close()
                            continue
                        
                        crawler_id = int(crawler_result[0])  # type: ignore
                        
                        # Try to update existing session by UUID
                        cursor.execute(
                            "UPDATE crawler_session SET crawler_id = %s, init_time = %s, url = %s, destroy_time = %s, update_time = %s WHERE uuid = %s",
                            (crawler_id, session.init_time, session.url, session.destroy_time, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session.uuid)
                        )
                        
                        if cursor.rowcount > 0:
                            # Session was updated
                            connection.commit()
                            logging.info(f"[SERVER][DB] Updated session with UUID: {session.uuid}")
                            
                            # Remove destroyed session from memory
                            if session.destroy_time is not None:
                                sessions.pop(session.uuid, None)
                                logging.info(f"[SERVER][DB] Removed destroyed session from memory: UUID {session.uuid}")
                        else:
                            # Session doesn't exist in database, insert new session
                            cursor.execute(
                                "INSERT INTO crawler_session (crawler_id, uuid, init_time, url, destroy_time, create_time) VALUES (%s, %s, %s, %s, %s, %s)",
                                (crawler_id, session.uuid, session.init_time, session.url, session.destroy_time, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            )
                            connection.commit()
                            logging.info(f"[SERVER][DB] Created new session with UUID: {session.uuid}")
                            
                            # Remove destroyed session from memory
                            if session.destroy_time is not None:
                                sessions.pop(session.uuid, None)
                                logging.info(f"[SERVER][DB] Removed destroyed session from memory: UUID {session.uuid}")
                        
                        cursor.close()
                        connection.close()
                        
                    except Exception as e:
                        logging.error(f"[SERVER][DB] Error updating session {session.uuid} in database: {e}")
                        try:
                            if 'cursor' in locals():
                                cursor.close()
                            if 'connection' in locals() and connection:
                                connection.close()
                        except Exception as cleanup_error:
                            logging.error(f"[SERVER][DB] Error during cleanup: {cleanup_error}")

            # Update API logs in database
            async with logs_lock:
                # Create a copy of the list to avoid modification during iteration
                logs_to_process = logs.copy()
                for request in logs_to_process:
                    logging.info(f"[SERVER][DB] Processing request: uuid={request.uuid}, id={request.id}, session={request.session_uuid}, api={request.url}, request_time={request.request_time}, response_time={request.response_time}, status_code={request.status_code}")
                    try:
                        connection = get_db_connection()
                        if connection is None:
                            continue
                        cursor = connection.cursor()
                        
                        # Get crawler_session_id for this request
                        cursor.execute(
                            "SELECT id FROM crawler_session WHERE uuid = %s",
                            (request.session_uuid,)
                        )
                        session_result = cursor.fetchone()
                        
                        if not session_result:
                            # crawler_session doesn't exist, skip this request
                            logging.warning(f"[SERVER][DB] Skipping request {request.uuid}: crawler_session not found for session_uuid {request.session_uuid}")
                            cursor.close()
                            connection.close()
                            continue
                        
                        session_id = int(session_result[0])  # type: ignore
                        
                        if request.id is None:
                            # Insert new API log
                            cursor.execute(
                                "INSERT INTO crawler_log (crawler_session_id, url, request_time, response_time, status_code, create_time) VALUES (%s, %s, %s, %s, %s, %s)",
                                (session_id, request.url, request.request_time, request.response_time, request.status_code, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            )
                            connection.commit()
                            # Save the ID for next update
                            request.id = cursor.lastrowid
                            logging.info(f"[SERVER][DB] Created new API log with ID: {request.id}")
                        else:
                            # Update existing API log by ID
                            cursor.execute(
                                "UPDATE crawler_log SET response_time = %s, status_code = %s, update_time = %s WHERE id = %s",
                                (request.response_time, request.status_code, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request.id)
                            )
                            connection.commit()
                            logging.info(f"[SERVER][DB] Updated API log with ID: {request.id}")
                        
                        # If request is complete (has response_time), remove from memory
                        if request.response_time is not None:
                            logs.remove(request)
                            logging.info(f"[SERVER][DB] Removed completed request from memory: ID {request.id}")
                        
                        cursor.close()
                        connection.close()
                        
                    except Exception as e:
                        logging.error(f"[SERVER][DB] Error updating API log for request {request.uuid} in database: {e}")
                        try:
                            if 'cursor' in locals():
                                cursor.close()
                            if 'connection' in locals() and connection:
                                connection.close()
                        except Exception as cleanup_error:
                            logging.error(f"[SERVER][DB] Error during cleanup: {cleanup_error}")

        except Exception as e:
            logging.error(f"[SERVER][DB] Error in log_status_periodically: {e}")
        
        await asyncio.sleep(interval)

#==========  MAIN FUNCTION  ==========
async def main() -> None:
    client_server = await asyncio.start_server(handle_client, '0.0.0.0', CLIENT_PORT)
    http_server = await asyncio.start_server(handle_http, '0.0.0.0', HTTP_PORT)
    
    async with http_server, client_server:
        logging.info(f"[SERVER][MAIN] Server started. HTTP(0.0.0.0:{HTTP_PORT}), Client(0.0.0.0:{CLIENT_PORT})")
        try:
            await asyncio.gather(http_server.serve_forever(), client_server.serve_forever(), log_status_periodically())
        except KeyboardInterrupt:
            logging.info("[SERVER][MAIN] Received shutdown signal, stopping servers...")
            # Close all client connections
            async with clients_lock:
                for client_uuid, client_info in list(clients.items()):
                    try:
                        if not client_info.writer.is_closing():
                            client_info.writer.close()
                            await client_info.writer.wait_closed()
                        logging.info(f"[SERVER][MAIN] Closed client connection: {client_uuid}")
                    except Exception as e:
                        logging.error(f"[SERVER][MAIN] Error closing client {client_uuid}: {e}")
                clients.clear()
            
            # Close all pending HTTP requests
            async with pending_requests_lock:
                for msg_id, (http_writer, request_obj) in list(pending_requests.items()):
                    try:
                        if not http_writer.is_closing():
                            http_writer.close()
                            await http_writer.wait_closed()
                        logging.info(f"[SERVER][MAIN] Closed pending HTTP request: {msg_id}")
                    except Exception as e:
                        logging.error(f"[SERVER][MAIN] Error closing HTTP request {msg_id}: {e}")
                pending_requests.clear()
                
        except Exception as e:
            logging.error(f"[SERVER][MAIN] Unexpected error: {e}")
        finally:
            logging.info("[SERVER][MAIN] Server shutdown complete.")

def run_server():
    """Run the server with proper signal handling"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[SERVER] Server stopped by user (Ctrl+C)")
    except Exception as e:
        logging.error(f"[SERVER] Server error: {e}")

if __name__ == '__main__':
    run_server()
