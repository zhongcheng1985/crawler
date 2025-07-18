import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ===== Global session and state storage =====
sessionS_processO: dict = {}          # session_id -> process object
sessionS_websocketO: dict = {}        # session_id -> websocket object
replyS_textS: dict = {}               # reply_id -> text
sessionS_tabN_responseLS: dict = {}   # session_id -> tab_id -> [text]
sessionS_tabN_loadedLS: dict = {}     # session_id -> tab_id -> [text]

from typing import Optional
from functools import wraps
from fastapi import HTTPException

def require_params(*param_names):
    """Decorator to check required parameters in kwargs or data body."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check header/query/path parameters
            for name in param_names:
                if name in kwargs and not kwargs.get(name):
                    raise HTTPException(status_code=400, detail=f"Missing parameter: {name}")
            # Check data body parameters
            data = kwargs.get('data')
            if isinstance(data, dict):
                for name in param_names:
                    if name not in kwargs and not data.get(name):
                        raise HTTPException(status_code=400, detail=f"Missing parameter in body: {name}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def fun_wait_reply(id: str, wait: float = 0.200, times: int = 10) -> Optional[str]:
    """Wait for a reply with the given id, polling up to 'times' times with 'wait' seconds interval."""
    if not id:
        return
    text = None
    import asyncio
    for _ in range(times):
        await asyncio.sleep(wait)
        if id in replyS_textS:
            text = replyS_textS[id]
            del replyS_textS[id]
            break
    return text

def fun_session_id() -> str:
    """Generate a unique session id."""
    import uuid
    return str(uuid.uuid4())[:8]

def fun_message_id() -> str:
    """Generate a unique message id."""
    import uuid
    return str(uuid.uuid4())

def fun_user_path(session_id: str) -> str:
    """Get the user data directory path for a session."""
    user_base = r'H:'
    import os
    user_path = os.path.join(user_base, f'chrome_{session_id}')
    return user_path

def fun_clear_data(session_id: str) -> Optional[str]:
    """Remove the user data directory for a session if it exists."""
    user_path = fun_user_path(session_id)
    import os
    if os.path.exists(user_path):
        if os.path.isdir(user_path):
            import shutil
            shutil.rmtree(user_path)
            return session_id
    return

async def fun_chrome_start(session_id: str, proxy: Optional[str]):
    """Start a Chrome browser instance for a given session."""
    user_path = fun_user_path(session_id)
    chrome_path = r'D:\Program Files\Chrome\chrome.exe'
    ext_path = r'E:\crawler\code\uia_extension'
    import subprocess
    chrome_process = subprocess.Popen(
        executable=chrome_path,
        args=[
            r'--new-instance',
            r'--no-first-run',
            r'--no-default-browser-check',
            r'--start-maximized',
            r'--force-renderer-accessibility',
            r'--disable-background-networking',
            f'--user-data-dir={user_path}',
            f'--load-extension={ext_path}',
            f'--proxy-server={proxy}' if proxy else r'--no-proxy',
            # r'--remote-debugging-port=9222',
            # r'--auto-open-devtools-for-tabs',
            # url,
            # r'http://127.0.0.1:8000/empty.html'
        ]
    )
    sessionS_processO[session_id] = chrome_process
    websocket_cfm = False
    import asyncio
    for _ in range(10):
        await asyncio.sleep(0.200)
        if session_id in sessionS_websocketO:
            websocket_cfm = True
            break
    if websocket_cfm:
        return chrome_process
    else:
        chrome_process.terminate()
        del sessionS_processO[session_id]
        return

async def fun_query_tabs(session_id: str):
    """Query the currently active tabs for a given session."""
    if not session_id:
        return
    chrome_websocket = sessionS_websocketO.get(session_id)
    if not chrome_websocket:
        return
    id = fun_message_id()
    req = {r'id': id, r'command': r'Request.queryTabs'}
    import json
    text = json.dumps(req)
    await chrome_websocket.send_text(text)
    logger.debug(f'websocket send:{chrome_websocket.client.host} {chrome_websocket.client.port}\r\n{text}')
    text = await fun_wait_reply(id)
    if text is None:
        logger.error("fun_wait_reply did not return a response for id: %s", id)
        return None
    rsp = json.loads(text)
    return rsp[r'data']

def fun_find_window(session_id: str):
    """Find the Chrome browser window for a given session."""
    if not session_id:
        return
    chrome_process = sessionS_processO.get(session_id)
    if not chrome_process:
        return
    chrome_window = None
    import uiautomation as uia
    desktop_windows = uia.GetRootControl().GetChildren()
    for win in desktop_windows:
        if win.ProcessId == chrome_process.pid:
            chrome_window = win
    return chrome_window

async def fun_session_go(session_id: str, url: str) -> Optional[str]:
    """Navigate to a URL in the Chrome browser for a given session."""
    if not session_id or not url:
        return
    chrome_window = fun_find_window(session_id)
    if not chrome_window:
        return
    chrome_window.SetFocus()
    try:
        chrome_window.Maximize()  # type: ignore
    except AttributeError:
        logger.warning("chrome_window has no Maximize method")
    chrome_window.SendKeys(r'{Ctrl}L')
    chrome_window.SendKeys(url)
    chrome_window.SendKeys(r'{Enter}')
    loaded_cfm = False
    import asyncio
    for _ in range(10):
        await asyncio.sleep(0.200)
        try:
            reload_button = chrome_window.ToolBarControl().GetChildren()[2].GetChildren()[2]
            if reload_button.Name in reload_button.GetLegacyIAccessiblePattern().Description:
                loaded_cfm = True
                logger.info("reload button ready")
                break
        except Exception as e:
            logger.info("check reload button error")
    title = None
    if loaded_cfm:
        chrome_document = chrome_window.DocumentControl()
        title = chrome_document.Name
    return title

async def fun_http_data(session_id: str, tab_id: int):
    """Retrieve HTTP data for a specific tab in a session."""
    if not session_id or not tab_id:
        return
    loaded_cfm = False
    import asyncio
    for _ in range(10):
        await asyncio.sleep(0.200)
        if session_id in sessionS_tabN_loadedLS:
            if tab_id in sessionS_tabN_loadedLS[session_id]:
                if sessionS_tabN_loadedLS[session_id][tab_id]:
                    loaded_cfm = True
                    break
    if not loaded_cfm:
        return
    dataLO = []
    try:
        import json
        for text in sessionS_tabN_responseLS[session_id][tab_id]:
            data = json.loads(text)
            headers = data[r'params'][r'responseHeaders']
            dataO = {
                r'tab_id': data[r'params'][r'tabId'],
                r'request_id': data[r'params'][r'requestId'],
                r'url': data[r'params'][r'url'],
                r'status': data[r'params'][r'statusCode'],
            }
            if r'content-type' in headers:
                dataO[r'content_type'] = headers[r'content-type']
            if r'content-length' in headers:
                dataO[r'content_length'] = headers[r'content-length']
            dataLO.append(dataO)
    except Exception as e:
        logger.info("get http data error")
    return dataLO

def fun_element_tree(element):
    """Recursively traverse the UI automation tree and return a dictionary representation."""
    try:
        rect = element.BoundingRectangle
        tree = {
            r'element_id': f'{rect.left}_{rect.top}_{rect.right}_{rect.bottom}',
            r'name': element.Name,
            r'control_type': element.ControlTypeName,
        }
        for child in element.GetChildren():
            e = fun_element_tree(child)
            if e:
                children = tree.get(r'children', [])
                children.append(e)
                tree.update({r'children': children})
        return tree
    except Exception as e:
        return

def fun_element_search(element, id: str):
    """Search for an element by its ID in the UI automation tree."""
    try:
        rect = element.BoundingRectangle
        element_id = f'{rect.left}_{rect.top}_{rect.right}_{rect.bottom}'
        if element_id == id:
            return element
        else:
            for child in element.GetChildren():
                ele = fun_element_search(child, id)
                if ele is not None:
                    return ele
    except Exception as e:
        return

def fun_uia_data(session_id: str):
    """Retrieve the UI automation tree for a given session."""
    if not session_id:
        return
    chrome_window = fun_find_window(session_id)
    if not chrome_window:
        return
    chrome_document = chrome_window.DocumentControl()
    tree = fun_element_tree(chrome_document)
    return tree

async def fun_session_download(session_id: str, tab_id: int, request_id: str):
    """Download the response body for a specific request in a tab."""
    if not session_id or not tab_id or not request_id:
        return
    chrome_websocket = sessionS_websocketO[session_id]
    if not chrome_websocket:
        return
    id = fun_message_id()
    req = {r'id': id, r'command': r'Request.Network.getResponseBody', r'params': {r'tabId': tab_id, r'requestId': request_id}}
    import json
    text = json.dumps(req)
    await chrome_websocket.send_text(text)
    logger.debug(f'websocket send:{chrome_websocket.client.host} {chrome_websocket.client.port}\r\n{text}')
    text = await fun_wait_reply(id)
    if text is None:
        logger.error("fun_wait_reply did not return a response for id: %s", id)
        return None
    rsp = json.loads(text)
    return rsp[r'data']

async def fun_session_click(session_id: str, element_id: str) -> Optional[str]:
    """Click on an element in the Chrome browser for a given session."""
    if not session_id or not element_id:
        return
    chrome_window = fun_find_window(session_id)
    if not chrome_window:
        return
    text = None
    try:
        chrome_window.SetFocus()
        try:
            chrome_window.Maximize()  # type: ignore
        except AttributeError:
            logger.warning("chrome_window has no Maximize method")
        chrome_document = chrome_window.DocumentControl()
        element = fun_element_search(chrome_document, element_id)
        if element:
            element.Click()
            text = element.Name
    except Exception as e:
        pass
    return text

async def fun_session_input(session_id: str, element_id: str, keys: str) -> Optional[str]:
    """Send keys to an element in the Chrome browser for a given session."""
    if not session_id or not element_id or not keys:
        return
    chrome_window = fun_find_window(session_id)
    if not chrome_window:
        return
    text = None
    try:
        chrome_window.SetFocus()
        try:
            chrome_window.Maximize()  # type: ignore
        except AttributeError:
            logger.warning("chrome_window has no Maximize method")
        chrome_document = chrome_window.DocumentControl()
        element = fun_element_search(chrome_document, element_id)
        if element:
            element.SendKeys(keys)
            text = element.Name
    except Exception as e:
        pass
    return text

async def fun_session_destroy(session_id: str) -> str:
    """Destroy a session by terminating the Chrome process and clearing data."""
    if session_id in sessionS_processO:
        try:
            chrome_process = sessionS_processO[session_id]
            chrome_process.terminate()
            del sessionS_processO[session_id]
        except Exception as e:
            pass
    if session_id in sessionS_tabN_responseLS:
        del sessionS_tabN_responseLS[session_id]
    if session_id in sessionS_tabN_loadedLS:
        del sessionS_tabN_loadedLS[session_id]
    import asyncio
    await asyncio.sleep(0.500)
    fun_clear_data(session_id)
    return session_id

# ==========  ========== web server ==========  ==========
from fastapi import FastAPI, BackgroundTasks, Header
from fastapi.responses import HTMLResponse, Response
from typing import Dict, Any
from functools import wraps
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import status
import threading
import time
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ----------  ---------- root ----------  ----------
root_html = '''
<!DOCTYPE html>
<html>
    <head>
        <title>Agent</title>
    </head>
    <body>
        <div>
            <a href='/api'><h1>/api</h1></a>
        </div>
        <div>
            <a href='/ws'><h1>/ws</h1></a>
        </div>
        <div>
            <a href='/demo.html'><h1>/demo</h1></a>
        </div>
    </body>
</html>
'''
@app.get('/')
def root():
    return HTMLResponse(root_html)
# ----------  ---------- api ----------  ----------
api_html = '''
<!DOCTYPE html>
<html>
    <head>
        <title>API</title>
    </head>
    <body>
        <div>
            <h1>/api/start</h1>
        </div>
        <div>
            <h1>/api/go</h1>
        </div>
        <div>
            <h1>/api/view</h1>
        </div>
        <div>
            <h1>/api/download</h1>
        </div>
        <div>
            <h1>/api/click</h1>
        </div>
        <div>
            <h1>/api/input</h1>
        </div>
        <div>
            <h1>/api/destroy</h1>
        </div>
    </body>
</html>
'''
@app.get(r'/api')
async def api():
    return HTMLResponse(api_html)

@app.post(r'/api/start')
async def api_start(response: Response, data: Optional[Dict[str, Any]], session_id: Optional[str] = Header(None, alias="X-Session-Id")):
    proxy = data.get('proxy') if data else None
    if not session_id:
        session_id = fun_session_id()
    if session_id not in sessionS_processO:
        chrome_process = await fun_chrome_start(session_id, proxy)
        if chrome_process is None:
            session_id = None
    # 设置 header
    rsp = {r'session_id': session_id}
    if session_id:
        response.headers['X-Session-Id'] = session_id
        rsp[r'session_id'] = session_id
    return rsp

@app.post(r'/api/go')
@require_params('session_id', 'url')
async def api_go(data: Dict[str, Any], session_id: str = Header(None, alias="X-Session-Id")):
    url = data.get('url')
    rsp = {r'url': url}
    title = await fun_session_go(session_id, url)
    if title is not None:
        rsp[r'title'] = title
    return rsp

@app.post(r'/api/view')
@require_params('session_id')
async def api_view(data: Dict[str, Any], session_id: str = Header(None, alias="X-Session-Id")):
    rsp = {}
    rsp[r'elements'] = fun_uia_data(session_id)
    return rsp

@app.post(r'/api/network')
@require_params('session_id')
async def api_network(data: Dict[str, Any], session_id: str = Header(None, alias="X-Session-Id")):
    rsp = {}
    tabs = await fun_query_tabs(session_id)
    if tabs:
        tab_id = None
        for tab in tabs:
            if tab[r'active']:
                tab_id = tab[r'id']
                break
        if tab_id is not None:
            rsp[r'responses'] = await fun_http_data(session_id, tab_id)
    return rsp

@app.post(r'/api/download')
@require_params('request_id', 'tab_id')
async def api_download(data: Dict[str, Any], session_id: str = Header(None, alias="X-Session-Id")):
    tab_id = data.get('tab_id')
    request_id = data.get('request_id')
    data_rsp = await fun_session_download(session_id, tab_id, request_id)
    rsp = {r'tab_id': tab_id, r'request_id': request_id, r'data': data_rsp}
    return rsp

@app.post(r'/api/click')
@require_params('session_id', 'element_id')
async def api_click(data: Dict[str, Any], session_id: str = Header(None, alias="X-Session-Id")):
    element_id = data.get('element_id')
    text = await fun_session_click(session_id, element_id)
    rsp = {r'element_id': element_id, r'text': text}
    return rsp

@app.post(r'/api/input')
@require_params('session_id', 'element_id', 'keys')
async def api_input(data: Dict[str, Any], session_id: str = Header(None, alias="X-Session-Id")):
    element_id = data.get('element_id')
    keys = data.get('keys')
    keys_rsp = await fun_session_input(session_id, element_id, keys)
    rsp = {r'element_id': element_id, r'keys': keys_rsp}
    return rsp

@app.post(r'/api/destroy')
@require_params('session_id')
async def api_destroy(response: Response, data: Dict[str, Any], session_id: str = Header(None, alias="X-Session-Id")):
    session_id = await fun_session_destroy(session_id)
    response.headers['X-Session-Id'] = session_id
    rsp = {r'session_id': session_id}
    return rsp

# ==========  ========== websocket ==========  ==========
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

ws_html = '''
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Test</title>
    </head>
    <body>
        <h1>WebSocket Test</h1>
        <div>
            <input type='text' id='urlText' autocomplete='off' value='ws://localhost:8020/ws/ext'/>
            <button id='connButton' onClick='connect()'>Connect</button>
        </div>
        <div>
            <input type='text' id='messageText' autocomplete='off'/>
            <button id='sendButton' onClick='sendMessage()' disabled='true'>Send</button>
        </div>
        <div>
            <div>Messages:</div>
            <ul id='messages'>
            </ul>
        </div>
        <script>
            var ws;
            function connect(){
                if(ws&&WebSocket.OPEN===ws.readyState){
                    ws.close()
                }else{
                    var input = document.getElementById('urlText')
                    var url=input.value
                    event.preventDefault()
                    if(!url) return
                    
                    ws = new WebSocket(url);
                    ws.onopen = function(event) {
                        var connButton = document.getElementById('connButton')
                        connButton.innerText='disConnect'
                        var sendButton = document.getElementById('sendButton')
                        sendButton.disabled=false
                        //
                        var messages = document.getElementById('messages')
                        var message = document.createElement('li')
                        var content = document.createTextNode('=='+'WebSocket open')
                        message.appendChild(content)
                        messages.appendChild(message)
                    }
                    ws.onmessage = function(event) {
                        var messages = document.getElementById('messages')
                        var message = document.createElement('li')
                        var content = document.createTextNode('<='+event.data)
                        message.appendChild(content)
                        messages.appendChild(message)
                    }
                    ws.onerror = function(error) {
                        var connButton = document.getElementById('connButton')
                        connButton.innerText='Connect'
                        var sendButton = document.getElementById('sendButton')
                        sendButton.disabled=true
                        //
                        var messages = document.getElementById('messages')
                        var message = document.createElement('li')
                        var content = document.createTextNode('=='+'WebSocket error')
                        message.appendChild(content)
                        messages.appendChild(message)
                    }
                    ws.onclose = function(event) {
                        var connButton = document.getElementById('connButton')
                        connButton.innerText='Connect'
                        var sendButton = document.getElementById('sendButton')
                        sendButton.disabled=true
                        //
                        var messages = document.getElementById('messages')
                        var message = document.createElement('li')
                        var content = document.createTextNode('=='+'WebSocket close')
                        message.appendChild(content)
                        messages.appendChild(message)
                    }
                }

            }
            function sendMessage() {
                if(ws&&WebSocket.OPEN===ws.readyState){
                    var input = document.getElementById('messageText')
                    var text=input.value
                    input.value = ''
                    ws.send(text)
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode('=>'+text)
                    message.appendChild(content)
                    messages.appendChild(message)
                }
            }
        </script>
    </body>
</html>
'''
@app.get(r'/ws')
async def get():
    return HTMLResponse(ws_html)

@app.websocket(r'/ws/ext')
async def ws_ext(websocket: WebSocket):
    await websocket.accept()
    logger.info(f'websocket accept:{websocket.client.host} {websocket.client.port}')
    #
    import asyncio
    await asyncio.sleep(0.200)
    #
    import psutil
    session_id = None
    for sessionS in sessionS_processO:
        try:
            connectionLO = []
            processO = sessionS_processO[sessionS]
            processO = psutil.Process(processO.pid)
            connectionLO.extend(processO.net_connections())
            for processO in processO.children(recursive=True):
                connectionLO.extend(processO.net_connections())
            for connection_obj in connectionLO:
                if (connection_obj.status == psutil.CONN_ESTABLISHED and connection_obj.laddr.port == websocket.client.port):
                    sessionS_websocketO[sessionS] = websocket
                    session_id = sessionS
        except psutil.NoSuchProcess:
            del sessionS_processO[sessionS]
    #
    if not session_id:
        await websocket.close()
        logger.info(f'websocket map to process failure. close:{websocket.client.host} {websocket.client.port}')
        return
    #
    try:
        import json
        while True:
            text = str(await websocket.receive_text())
            logger.debug(f'websocket received:{websocket.client.host} {websocket.client.port}\r\n{text}')
            data = json.loads(text)
            #
            if data.get(r'reply', None):
                replyS_textS[data[r'reply']] = text
            #
            if r'Event.webNavigation.onBeforeNavigate' == data.get(r'command', None):
                tab_id = data[r'params'][r'tabId']
                #
                tabN_responseLS = sessionS_tabN_responseLS.get(session_id, {})
                tabN_responseLS.update({tab_id: []})
                sessionS_tabN_responseLS.update({session_id: tabN_responseLS})
                logger.info(f'session_tab_response cleared:{session_id} {tab_id}')
                #
                tabN_loadedLS = sessionS_tabN_loadedLS.get(session_id, {})
                tabN_loadedLS.update({tab_id: []})
                sessionS_tabN_loadedLS.update({session_id: tabN_loadedLS})
                logger.info(f'session_tab_loaded cleared:{session_id} {tab_id}')
            #
            if r'Event.Network.responseReceived' == data.get(r'command', None):
                tab_id = data[r'source'][r'tabId']
                tabN_responseLS = sessionS_tabN_responseLS.get(session_id, {})
                responseLS = tabN_responseLS.get(tab_id, [])
                responseLS.append(text)
                tabN_responseLS.update({tab_id: responseLS})
                sessionS_tabN_responseLS.update({session_id: tabN_responseLS})
                logger.info(f'session_tab_response append:{session_id} {tab_id}')
            #
            if r'Event.webRequest.onResponseStarted' == data.get(r'command', None):
                tab_id = data[r'params'][r'tabId']
                tabN_responseLS = sessionS_tabN_responseLS.get(session_id, {})
                responseLS = tabN_responseLS.get(tab_id, [])
                responseLS.append(text)
                tabN_responseLS.update({tab_id: responseLS})
                sessionS_tabN_responseLS.update({session_id: tabN_responseLS})
                logger.info(f'session_tab_response append:{session_id} {tab_id}')
            #
            if r'Event.webNavigation.onCompleted' == data.get(r'command', None):
                tab_id = data[r'params'][r'tabId']
                tabN_loadedLS = sessionS_tabN_loadedLS.get(session_id, {})
                loadedLS = tabN_loadedLS.get(tab_id, [])
                loadedLS.append(text)
                tabN_loadedLS.update({tab_id: loadedLS})
                sessionS_tabN_loadedLS.update({session_id: tabN_loadedLS})
                logger.info(f'session_tab_loaded append:{session_id} {tab_id}')
    except WebSocketDisconnect:
        logger.info(f'websocket close:{websocket.client.host} {websocket.client.port}')
        key = None
        for k in sessionS_websocketO:
            if websocket == sessionS_websocketO[k]:
                key = k
                break
        if key:
            del sessionS_websocketO[key]
    #
    return
# ----------  ---------- empty ----------  ----------
empty_html = '''
<!DOCTYPE html>
<html>
    <body>
    </body>
</html>
'''
@app.get('/empty.html')
def emptyHtml():
    return HTMLResponse(empty_html)

# ----------  ---------- demo ----------  ----------
demo_html = '''
<!DOCTYPE html>
<html>
	<head><title>demo</title></head>
    <link rel="stylesheet" href="demo.css"></link>
	<script src="demo.js"></script>
    <body>
            <input id="a" />
            <input id="b" />
            <input id="c" type="button" value="=>" onclick="document.getElementById('d').value=document.getElementById('a').value+document.getElementById('b').value" />
            <input id="d" value="" />
    </body>
</html>
'''
@app.get('/demo.html')
def demoHtml():
    return HTMLResponse(demo_html)

demo_js = '''
function demo(){
    console.log("hello")
}
demo()
'''
@app.get('/demo.js')
def demoJs():
    return Response(content=demo_js, media_type="application/javascript")

demo_css = '''
body{
    width:100%;
    height:100%;
}
'''
@app.get('/demo.css')
def demoCss():
    return Response(content=demo_css, media_type="text/css")

# ==========  ========== uvicorn ==========  ==========
def uvicorn_run():
    #
    import uvicorn
    uvicorn.run(
        app,
        host=r'127.0.0.1',  # 只监听本地
        port=8020,
        log_level=r'info',
        access_log=True
    )

# ==========  ========== main ==========  ==========
if __name__ == '__main__':
    logger.info(r'正在启动')
    uvicorn_run()
    logger.info(r'正在关闭')
