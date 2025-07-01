import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# NOTSET:0,DEBUG:10,INFO:20,WARNING:30,ERROR:40,CRITICAL:50
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ==========  ========== data ==========  ==========
sessionS_processO:dict = {}          # session_id -> {process}
sessionS_websocketO:dict = {}        # session_id -> {websocket}
replyS_textS:dict = {}               # reply_id -> text
sessionS_tabN_responseLS:dict = {}     # session_id -> tab_id -> [text]
sessionS_tabN_loadedLS:dict = {}       # session_id -> tab_id -> [text]

# ==========  ========== function ==========  ==========
async def fun_wait_reply(id:str,wait:int=0.200,times:int=10) -> str:
    if(not id):
        return
    #
    text=None
    import asyncio
    for i in range(times):
        await asyncio.sleep(wait)
        if(id in replyS_textS):
             text=replyS_textS[id]
             del replyS_textS[id]
             break
    #
    return text

def fun_session_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8]

def fun_message_id() -> str:
    import uuid
    return str(uuid.uuid4())

def fun_user_path(session_id:str) -> str:
    #
    user_base = r'H:'
    #import tempfile
    #session_base = tempfile.gettempdir()
    #
    import os
    user_path =os.path.join(user_base,f'chrome_{session_id}')
    #
    return user_path

def fun_clear_data(session_id:str) -> str:
    user_path = fun_user_path(session_id)
    import os
    if os.path.exists(user_path):
        if os.path.isdir(user_path):
            import shutil
            shutil.rmtree(user_path)
            return session_id
    return

async def fun_chrome_start(session_id:str):
    #
    user_path = fun_user_path(session_id)
    #
    chrome_path = r'D:\Program Files\Chrome\chrome.exe'
    ext_path = r'E:\crawler\code\uia_extension'
    #
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
            # r'--proxy-server='http://127.0.0.1:8888'',
            # r'--remote-debugging-port=9222',
            # r'--auto-open-devtools-for-tabs',
            # url,
            # r'http://127.0.0.1:8000/empty.html'
        ]
    )
    #
    sessionS_processO[session_id]=chrome_process
    #
    websocket_cfm=False
    import asyncio
    for i in range(10):
        await asyncio.sleep(0.200)
        if(session_id in sessionS_websocketO):
             websocket_cfm=True
             break
    #
    if(websocket_cfm):
        return chrome_process
    else:
        chrome_process.terminate()
        del sessionS_processO[session_id]
        return

async def fun_query_tabs(session_id:str):
    if(not session_id):
        return
    chrome_websocket = sessionS_websocketO[session_id]
    if(not chrome_websocket):
        return
    #
    id=fun_message_id()
    req={r'id':id,r'command':r'Request.queryTabs'}
    import json
    text=json.dumps(req)
    await chrome_websocket.send_text(text)
    logger.debug(f'websocket send:{chrome_websocket.client.host} {chrome_websocket.client.port}\r\n{text}')
    #
    text=await fun_wait_reply(id)
    rsp=json.loads(text)
    #
    return rsp[r'data']

def fun_find_window(session_id:str):
    if(not session_id):
        return
    chrome_process = sessionS_processO[session_id]
    if(not chrome_process):
        return
    #
    chrome_window=None
    import uiautomation as uia
    desktop_windows = uia.GetRootControl().GetChildren()
    for win in desktop_windows:
        if win.ProcessId == chrome_process.pid:
            chrome_window=win
    #
    return chrome_window

async def fun_session_go(session_id:str,url:str) -> str:
    if(not session_id or not url):
        return
    #
    chrome_window=fun_find_window(session_id)
    if(not chrome_window):
        return
    #
    chrome_window.SetFocus()
    chrome_window.Maximize()
    #
    chrome_window.SendKeys(r'{Ctrl}L')
    chrome_window.SendKeys(url)
    #import asyncio
    #await asyncio.sleep(0.200)
    chrome_window.SendKeys(r'{Enter}')
    #
    loaded_cfm=False
    import asyncio
    for i in range(10):
        await asyncio.sleep(0.200)
        try:
            reload_button=chrome_window.ToolBarControl().GetChildren()[2].GetChildren()[2]
            if(reload_button.Name in reload_button.GetLegacyIAccessiblePattern().Description):
                loaded_cfm=True
                logger.info("reload button ready")
                break
        except Exception as e:
            logger.info("check reload button error")
    #
    title=None
    if(loaded_cfm):
        chrome_document=chrome_window.DocumentControl()
        title=chrome_document.Name
    return title
    
async def fun_http_data(session_id:str,tab_id:int):
    if(not session_id or not tab_id):
        return
    #
    loaded_cfm=False
    import asyncio
    for i in range(10):
        await asyncio.sleep(0.200)
        if(session_id in sessionS_tabN_loadedLS):
            if(tab_id in sessionS_tabN_loadedLS[session_id]):
                if(sessionS_tabN_loadedLS[session_id][tab_id]):
                    loaded_cfm=True
                    break
    #
    if(not loaded_cfm):
        return
    #
    dataLO=[]
    try:
        import json
        for text in sessionS_tabN_responseLS[session_id][tab_id]:
            data=json.loads(text)
            headers=data[r'params'][r'responseHeaders']
            dataO={
                r'tab_id':data[r'params'][r'tabId'],
                r'request_id':data[r'params'][r'requestId'],
                r'url': data[r'params'][r'url'],
                r'status': data[r'params'][r'statusCode'],
            }
            if(r'content-type' in headers):
                dataO[r'content_type']=headers[r'content-type']
            if(r'content-length' in headers):
                dataO[r'content_length']=headers[r'content-length']
            dataLO.append(dataO)
    except Exception as e:
        logger.info("get http data error")
    #
    return dataLO

def fun_element_tree(element):
    try:
        rect = element.BoundingRectangle
        tree = {
            r'element_id': f'{rect.left}_{rect.top}_{rect.right}_{rect.bottom}',
            r'name': element.Name,
            r'control_type': element.ControlTypeName,
        }
        for child in element.GetChildren():
            e = fun_element_tree(child)
            if(e):
                children=tree.get(r'children',[])
                children.append(e)
                tree.update({r'children':children})
        return tree
    except Exception as e:
        return

def fun_element_search(element,id:str):
    try:
        rect = element.BoundingRectangle
        element_id=f'{rect.left}_{rect.top}_{rect.right}_{rect.bottom}'
        if(element_id==id):
            return element
        else:
            for child in element.GetChildren():
                ele=fun_element_search(child,id)
                if(None!=ele):
                    return ele
    except Exception as e:
        return

def fun_uia_data(session_id:str):
    if(not session_id):
        return
    #
    chrome_window=fun_find_window(session_id)
    if(not chrome_window):
        return
    #
    chrome_document=chrome_window.DocumentControl()
    tree=fun_element_tree(chrome_document)
    #
    return tree

async def fun_session_download(session_id:str,tab_id:int,request_id:str):
    if(not session_id or not tab_id or not request_id):
        return
    chrome_websocket = sessionS_websocketO[session_id]
    if(not chrome_websocket):
        return
    #
    id=fun_message_id()
    req={r'id':id,r'command':r'Request.Network.getResponseBody',r'params':{r'tabId':tab_id,r'requestId':request_id}}
    import json
    text=json.dumps(req)
    await chrome_websocket.send_text(text)
    logger.debug(f'websocket send:{chrome_websocket.client.host} {chrome_websocket.client.port}\r\n{text}')
    #
    text=await fun_wait_reply(id)
    rsp=json.loads(text)
    #
    return rsp[r'data']

def fun_session_click(session_id:str,element_id:str) -> str:
    if(not session_id or not element_id):
        return
    #
    chrome_window=fun_find_window(session_id)
    if(not chrome_window):
        return
    #
    text=None
    try:
        chrome_window.SetFocus()
        chrome_window.Maximize()
        chrome_document=chrome_window.DocumentControl()
        element=fun_element_search(chrome_document,element_id)
        if(element):
            element.Click()
            text=element.Name
    except Exception as e:
        pass
    #
    return text

def fun_session_input(session_id:str,element_id:str,keys:str) -> str:
    if(not session_id or not element_id or not keys):
        return
    #
    chrome_window=fun_find_window(session_id)
    if(not chrome_window):
        return
    #
    text=None
    try:
        chrome_window.SetFocus()
        chrome_window.Maximize()
        chrome_document=chrome_window.DocumentControl()
        element=fun_element_search(chrome_document,element_id)
        if(element):
            element.SendKeys(keys)
            text=element.Name
    except Exception as e:
        pass
    #
    return text

async def fun_session_destroy(session_id:str) -> str:
    if(not session_id):
        return
    #
    if(session_id in sessionS_processO):
        try:
            chrome_process = sessionS_processO[session_id]
            chrome_process.terminate()
            del sessionS_processO[session_id]
        except Exception as e:
            pass
    #
    if(session_id in sessionS_tabN_responseLS):
        del sessionS_tabN_responseLS[session_id]
    if(session_id in sessionS_tabN_loadedLS):
        del sessionS_tabN_loadedLS[session_id]
    #
    import asyncio 
    await asyncio.sleep(0.200)
    fun_clear_data(session_id)
    #
    return session_id

# ==========  ========== web server ==========  ==========
from fastapi import FastAPI,BackgroundTasks
from fastapi.responses import HTMLResponse,Response
from typing import Dict, Any
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
            <div>Method: Post</div>
            <div>Content-Type: application/json</div>
            <div>
                <div>Request Body:</div>
                <ul>
                    <li>session_id:str (opt)</li>
                </ul>
            </div>
            <div>
                <div>Response Body:</div>
                <ui>
                    <li>session_id:str</li>
                </ui>
            </div>
        </div>
        <div>
            <h1>/api/go</h1>
            <div>Method: Post</div>
            <div>Content-Type: application/json</div>
            <div>
                <div>Request Body:</div>
                <ul>
                    <li>session_id:str</li>
                    <li>url:str</li>
                </ul>
            </div>
            <div>
                <div>Response Body:</div>
                <ui>
                    <li>session_id:str</li>
                    <li>url:str</li>
                    <li>title:str</li>
                    <li>elements:tree</li>
                    <li>responses:list</li>
                </ui>
            </div>
        </div>
        <div>
            <h1>/api/download</h1>
            <div>Method: Post</div>
            <div>Content-Type: application/json</div>
            <div>
                <div>Request Body:</div>
                <ul>
                    <li>request_id:str</li>
                    <li>tab_id:int</li>
                    <li>request_id:str</li>
                </ul>
            </div>
            <div>
                <div>Response Body:</div>
                <ui>
                <ul>
                    <li>session_id:str</li>
                    <li>tab_id:int</li>
                    <li>request_id:str</li>
                    <li>data:{}</li>
                </ul>
                </ui>
            </div>
        </div>
        <div>
            <h1>/api/click</h1>
            <div>Method: Post</div>
            <div>Content-Type: application/json</div>
            <div>
                <div>Request Body:</div>
                <ul>
                    <li>session_id:str</li>
                    <li>element_id:str</li>
                </div>
            </div>
            <div>
                <div>Response Body:</div>
                <ui>
                    <li>session_id:str</li>
                    <li>element_id:str</li>
                    <li>text:str</li>
                </ui>
            </div>
        </div>
        <div>
            <h1>/api/input</h1>
            <div>Method: Post</div>
            <div>Content-Type: application/json</div>
            <div>
                <div>Request Body:</div>
                <ui>
                    <li>session_id:str</li>
                    <li>element_id:str</li>
                    <li>keys:str</li>
                </ui>
            </div>
            <div>
                <div>Response Body:</div>
                <ui>
                    <li>session_id:str</li>
                    <li>element_id:str</li>
                    <li>keys:str</li>
                </ui>
            </div>
        </div>
        <div>
            <h1>/api/destroy</h1>
            <div>Method: Post</div>
            <div>Content-Type: application/json</div>
            <div>
                <div>Request Body:</div>
                <ui>
                    <li>session_id:str</li>
                </ui>
            </div>
            <div>
                <div>Response Body:</div>
                <ui>
                    <li>session_id:str</li>
                </ui>
            </div>
        </div>
    </body>
</html>
'''
@app.get(r'/api')
async def api():
    return HTMLResponse(api_html)

@app.post(r'/api/start')
async def api_start(data: Dict[str, Any]):
    session_id = data.get(r'session_id',None)
    if(not session_id):
        session_id = fun_session_id()
    if(session_id not in sessionS_processO):
        chrome_process = await fun_chrome_start(session_id)
        if(None==chrome_process):
            session_id=None

    rsp = {r'session_id': session_id}
    logger.info(r'api go:'+str(rsp))
    return rsp

@app.post(r'/api/go')
async def api_go(data: Dict[str, Any]):
    session_id = data.get(r'session_id',None)
    url = data.get(r'url',None)
    if(not session_id or not url):
        return
    #
    rsp = {r'session_id': session_id,r'url':url}
    #
    title = await fun_session_go(session_id,url)
    if(None!=title):
        rsp[r'title'] = title
        #
        rsp[r'elements'] = fun_uia_data(session_id)
        #
        tab_id=None
        tabs = await fun_query_tabs(session_id)
        for tab in tabs:
            if(tab[r'active']):
                tab_id=tab[r'id']
                break
        rsp[r'responses'] = await fun_http_data(session_id,tab_id)
    #
    logger.info(r'api go:'+str(rsp))
    #
    return rsp

@app.post(r'/api/download')
async def api_download(data: Dict[str, Any]):
    session_id = data.get(r'session_id',None)
    tab_id = data.get(r'tab_id',None)
    request_id = data.get(r'request_id',None)
    if(not session_id or not tab_id or not request_id):
        return

    data = await fun_session_download(session_id,tab_id,request_id)
    rsp = {r'session_id': session_id,r'tab_id':tab_id,r'request_id':request_id,r'data':data}
    logger.info(r'api download:'+str(rsp))
    return rsp

@app.post(r'/api/click')
async def api_click(data: Dict[str, Any]):
    session_id = data.get(r'session_id',None)
    element_id = data.get(r'element_id',None)
    if(not session_id or not element_id):
        return

    text = fun_session_click(session_id,element_id)
    rsp = {r'session_id': session_id,r'element_id':element_id,r'text':text}
    logger.info(r'api click:'+str(rsp))
    return rsp

@app.post(r'/api/input')
async def api_input(data: Dict[str, Any]):
    session_id = data.get(r'session_id',None)
    element_id = data.get(r'element_id',None)
    keys = data[r'keys']
    if(not session_id or not element_id or not keys):
        return

    keys = fun_session_input(session_id,element_id,keys)
    rsp = {r'session_id': session_id,r'element_id':element_id,r'keys':keys}
    logger.info(r'api input:'+str(rsp))
    return rsp

@app.post(r'/api/destroy')
async def api_destroy(data: Dict[str, Any]):
    session_id = data.get(r'session_id',None)
    if(not session_id):
        return

    session_id= await fun_session_destroy(session_id)
    rsp = {r'session_id': session_id}
    logger.info(r'api destroy:'+str(rsp))

# ==========  ========== websocket ==========  ==========
from fastapi import WebSocket,WebSocketDisconnect
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
            <input type='text' id='urlText' autocomplete='off' value='ws://localhost:8000/ws/ext'/>
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
    session_id=None
    for sessionS in sessionS_processO:
        try:
            connectionLO=[]
            processO=sessionS_processO[sessionS]
            processO=psutil.Process(processO.pid)
            connectionLO.extend(processO.net_connections())
            for processO in processO.children(recursive=True):
                connectionLO.extend(processO.net_connections())
            for connection_obj in connectionLO:
                if (connection_obj.status==psutil.CONN_ESTABLISHED and connection_obj.laddr.port==websocket.client.port):
                    sessionS_websocketO[sessionS]=websocket
                    session_id=sessionS
        except psutil.NoSuchProcess:
            del sessionS_processO[sessionS]
    #
    if(not session_id):
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
            if(data.get(r'reply',None)):
                replyS_textS[data[r'reply']]=text
            #
            if(r'Event.webNavigation.onBeforeNavigate'==data.get(r'command',None)):
                tab_id=data[r'params'][r'tabId']
                #
                tabN_responseLS=sessionS_tabN_responseLS.get(session_id,{})
                tabN_responseLS.update({tab_id:[]})
                sessionS_tabN_responseLS.update({session_id:tabN_responseLS})
                logger.info(f'session_tab_response cleared:{session_id} {tab_id}')
                #
                tabN_loadedLS=sessionS_tabN_loadedLS.get(session_id,{})
                tabN_loadedLS.update({tab_id:[]})
                sessionS_tabN_loadedLS.update({session_id:tabN_loadedLS})
                logger.info(f'session_tab_loaded cleared:{session_id} {tab_id}')
            #
            if(r'Event.Network.responseReceived'==data.get(r'command',None)):
                tab_id=data[r'source'][r'tabId']
                tabN_responseLS=sessionS_tabN_responseLS.get(session_id,{})
                responseLS=tabN_responseLS.get(tab_id,[])
                responseLS.append(text)
                tabN_responseLS.update({tab_id:responseLS})
                sessionS_tabN_responseLS.update({session_id:tabN_responseLS})
                logger.info(f'session_tab_response append:{session_id} {tab_id}')
            #
            if(r'Event.webRequest.onResponseStarted'==data.get(r'command',None)):
                tab_id=data[r'params'][r'tabId']
                tabN_responseLS=sessionS_tabN_responseLS.get(session_id,{})
                responseLS=tabN_responseLS.get(tab_id,[])
                responseLS.append(text)
                tabN_responseLS.update({tab_id:responseLS})
                sessionS_tabN_responseLS.update({session_id:tabN_responseLS})
                logger.info(f'session_tab_response append:{session_id} {tab_id}')
            #
            if(r'Event.webNavigation.onCompleted'==data.get(r'command',None)):
                tab_id=data[r'params'][r'tabId']
                tabN_loadedLS=sessionS_tabN_loadedLS.get(session_id,{})
                loadedLS=tabN_loadedLS.get(tab_id,[])
                loadedLS.append(text)
                tabN_loadedLS.update({tab_id:loadedLS})
                sessionS_tabN_loadedLS.update({session_id:tabN_loadedLS})
                logger.info(f'session_tab_loaded append:{session_id} {tab_id}')
    except WebSocketDisconnect:
        logger.info(f'websocket close:{websocket.client.host} {websocket.client.port}')
        key=None
        for k in sessionS_websocketO:
            if(websocket==sessionS_websocketO[k]):
                key=k
                break
        if(key):
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
        port=8000,
        log_level=r'info'
    )

# ==========  ========== main ==========  ==========
if __name__ == '__main__':
    logger.info(r'正在启动')
    uvicorn_run()
    logger.info(r'正在关闭')
