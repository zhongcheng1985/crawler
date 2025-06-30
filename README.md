## 1. Extension
Attach the debugger to monitor Chrome events. Chrome will display a debugging prompt.

### 1.1 tag events
- `onCreate`: Reserved
- `onUpdate`: Attach debugger  
- `onActive`: Reserved  
- `onRemove`: Reserved

### 1.2 network events:  
- `Network.requestWillBeSent`: Reserved.  
- `Network.responseReceived`: Retrieves response information.  
- `Network.loadingFinished`: Reserved.  

### 1.3 page events:
- `Page.frameNavigated`: Indicates when page navigation begins
- `Page.domContentEventFired`: Reserved
- `Page.loadEventFired`: Indicates when page loading is complete

### 1.4 available interfaces:
- `Request.toUrl`: Reserved
- `Request.executeScript`: Reserved 
- `Request.queryTabs`: Retrieves tab list information
- `Request.Network.getResponseBody`: Fetches response body content

## 2. agent：
Listens on port 8000 with WebSocket for extension communication and HTTP for external APIs.

### 2.1 environment:
- `chrome_path`: chrome executable file path
- `ext_path`: chrome extension base path
- `user_base`: user data base path

### 2.2 API:

#### 2.2.1.  /
- **Description**: index page
- **method**: get

#### 2.2.2.  /api
- **Description**: api description page
- **method**: get

#### 2.2.3.  /ws
- **Description**: websocket test page
- **method**: get

#### 2.2.4. /api/start
- **Description**: start session
- **method**: post
- **content-type**: application/json
- **parms**:
```
    {
        "session_id": "string (optional)"
    }
```
- **return**：
```
    {
        "session_id": "string (optional)"
    }
```
If session_id is empty: creates new session and returns session_id.
If session_id provided: resumes existing session (useful for Chrome crash recovery)

#### 2.2.5. /api/go
- **Description**: UIA-based navigation in current tab
- **method**: post
- **content-type**: application/json
- **parms**:
```
    {
        "session_id": "string (required)",
        "url": "string (required)"
    } 
```
- **return**：
```
    {
    "session_id": "string",
    "url": "string",
    "title": "string (optional)",
    "elements": [
        {
            "element_id": "string",
            "name": "string",
            "control_type": "string",
            "children": "list"
        }
    ],
    "responses": [
            {
                "request_id": "string",
                "url": "string",
                "content_type": "string",
                "content_length": "string",
                "status": "string"
            }
        ]
    }
```

#### 2.2.6. /api/input
- **method**: post
- **content-type**: application/json
- **parms**:
```
    {
        "session_id": "string (required)",
        "element_id": "string (required)",
        "keys": "string (required eg: abc{tab}123)"
    }
```
- **return**：
```
    {
    "session_id": "string",
    "url": "string",
    "title": "string (optional)",
    "elements": [
        {
            "element_id": "string",
            "name": "string",
            "control_type": "string",
            "children": "list"
        }
    ],
    "responses": {
        "session_id": "string",
        "element_id": "string",
        "keys": "string"
    }
```

#### 2.2.7. /api/click
- **method**: post
- **content-type**: application/json
- **parms**:
```
    {
        "session_id": "string (required)",
        "element_id": "string (required)"
    }
```
- **return**：
```
    {
        "session_id": "string",
        "element_id": "string",
        "text": "string (UIA element name)"
    }
```

#### 2.2.8. /api/download
- **method**: post
- **content-type**: application/json
- **parms**:
```
    {
        "session_id": "string (required)",
        "tab_id": "int (required)",
        "request_id": "string (required)"
    }
```
- **return**：
```
    {
        "session_id": "string",
        "tab_id": "int",
        "request_id": "string",
        "data": "string (base64)"
    }
```

#### 2.2.9. /api/destory
- **method**: post
- **content-type**: application/json
- **parms**:
```
    {
        "session_id": "string (required)"
    }
```
- **return**：
```
    {
        "session_id": "string"
    }
```

## 2.3. websocket

#### 2.3.1 /ws/ext 
- **Description**: extension access
- **method**: websocket
- **data**: 
```
    {
        "id":"str",
        "reply":"str",
        "command":"str",
        "source":"str",
        "params":"str",
        "data":"str",
        "error":"str"
    }
```
