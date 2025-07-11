import asyncio
import socket
import logging
import json
import uuid
import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

DISPATCHER_HOST = '127.0.0.1'
DISPATCHER_PORT = 8010
HTTP_HOST = '127.0.0.1'
HTTP_PORT = 8020

# Message delimiter
MESSAGE_DELIMITER = b'\x00\x01\x02\x03'

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
                    logging.info(f"[CLIENT][JSON] Received: {json.dumps(message, ensure_ascii=False)}")
                    return message
                except json.JSONDecodeError as e:
                    logging.error(f"[CLIENT][JSON] Error parsing JSON: {e}")
                    return None
    except Exception as e:
        logging.error(f"[CLIENT][JSON] Error reading JSON message: {e}")
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
        logging.info(f"[CLIENT][JSON] Sent to {addr}: {message_str}")
    except Exception as e:
        logging.error(f"[CLIENT][JSON] Error writing JSON message: {e}")

async def handle_http_request(request_body: bytes) -> bytes:
    """Handle HTTP request from dispatcher and forward to HTTP server, return response buffer"""
    http_reader = None
    http_writer = None
    try:
        # Connect to HTTP server
        http_reader, http_writer = await asyncio.open_connection(HTTP_HOST, HTTP_PORT)
        
        # Debug: Log the binary HTTP request
        logging.info(f"[CLIENT][HTTP] Sending binary HTTP request, original size: {len(request_body)} bytes")
        
        # Write binary HTTP request directly to HTTP server
        http_writer.write(request_body)
        await http_writer.drain()
        
        # Read HTTP response as binary data
        response_buffer = b""
        while True:
            chunk = await http_reader.read(1024)
            if not chunk:
                break
            response_buffer += chunk
        
        logging.info(f"[CLIENT][HTTP] Received binary HTTP response, size: {len(response_buffer)} bytes")
        
        return response_buffer
        
    except Exception as e:
        logging.error(f"[CLIENT][HTTP] Error handling HTTP request: {e}")
        raise
    finally:
        # Ensure HTTP connection is properly closed
        if http_writer:
            try:
                if not http_writer.is_closing():
                    http_writer.close()
                    await http_writer.wait_closed()
            except Exception as e:
                logging.error(f"[CLIENT][HTTP] Error closing HTTP connection: {e}")

async def handle_dispatcher_connection():
    while True:
        server_reader = None
        server_writer = None
        try:
            server_reader, server_writer = await asyncio.open_connection(DISPATCHER_HOST, DISPATCHER_PORT)
            sock = server_writer.get_extra_info('socket')
            if sock is not None:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            logging.info(f"[CLIENT][CONN] Connected to dispatcher({DISPATCHER_HOST}:{DISPATCHER_PORT}) <==> Http({HTTP_HOST}:{HTTP_PORT})")
            
            while True:
                # Wait for JSON request from dispatcher
                request_msg = await read_json_message(server_reader)
                if not request_msg:
                    logging.info("[CLIENT][CONN] Dispatcher connection closed, reconnecting...")
                    break
                    
                if request_msg.get("type") == "http.request":
                    # Extract and decode request data
                    request_body_b64 = request_msg.get("data", "")
                    request_msg_id = request_msg.get("id", "")
                    
                    # Decode base64 request data
                    import base64
                    try:
                        request_body = base64.b64decode(request_body_b64)
                        # Handle HTTP request
                        response_buffer = await handle_http_request(request_body)
                        # Send response back to dispatcher
                        response_data = base64.b64encode(response_buffer).decode('utf-8')
                        msg_id = str(uuid.uuid4())
                        await write_json_message(server_writer, msg_id, "http.response", response_data, request_msg_id)
                    except Exception as e:
                        logging.error(f"[CLIENT][HTTP] Error handling HTTP request: {e}")
                        # Send error response
                        error_response = base64.b64encode(b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\nContent-Length: 21\r\n\r\nInternal Server Error").decode('utf-8')
                        msg_id = str(uuid.uuid4())
                        await write_json_message(server_writer, msg_id, "http.response", error_response, request_msg_id)
                else:
                    logging.warning(f"[CLIENT][JSON] Unknown message type: {request_msg.get('type')}")
                    
        except Exception as e:
            logging.error(f"[CLIENT][CONN] Connection error: {e}. Reconnecting in 1s...")
        finally:
            # Ensure dispatcher connection is properly closed
            if server_writer:
                try:
                    if not server_writer.is_closing():
                        server_writer.close()
                        await server_writer.wait_closed()
                except Exception as e:
                    logging.error(f"[CLIENT][CONN] Error closing dispatcher connection: {e}")
            
            await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(handle_dispatcher_connection()) 