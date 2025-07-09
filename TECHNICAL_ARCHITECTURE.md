# Technical Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Applications                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Web UI    │  │   Mobile    │  │   Desktop   │  │   Scripts   │         │
│  │  Dashboard  │  │    Apps     │  │    Apps     │  │   (demo.py) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Service Layer                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Application (Port 8000)                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐     │    │
│  │  │   HTTP      │  │  WebSocket  │  │   Session   │  │   UIA   │     │    │
│  │  │   API       │  │   Handler   │  │  Manager    │  │ Handler │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Process Management
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Chrome Browser Layer                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Chrome Browser Instances                         │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐     │    │
│  │  │  Session 1  │  │  Session 2  │  │  Session 3  │  │   ...   │     │    │
│  │  │  Chrome     │  │  Chrome     │  │  Chrome     │  │         │     │    │
│  │  │  Instance   │  │  Instance   │  │  Instance   │  │         │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Chrome Extension Layer                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    UIA Extension                                    │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐     │    │
│  │  │ Background  │  │   Content   │  │   Popup     │  │  Debug  │     │    │
│  │  │   Script    │  │   Script    │  │   Interface │  │ Protocol│     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Database
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Storage Layer                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        MySQL Database                               │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐     │    │
│  │  │crawler_info │  │crawler_     │  │crawler_     │  │api_log  │     │    │
│  │  │             │  │status       │  │session      │  │         │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

### 1. Session Initialization Flow

```
Client Request → Agent Service → Chrome Process Creation → Extension Loading → WebSocket Connection → Session Ready
     │              │                    │                      │                    │
     ▼              ▼                    ▼                      ▼                    ▼
HTTP POST        Session ID         Chrome Instance        Extension         WebSocket
/api/start      Generation         with UIA Ext          Auto-load         Connection
```

### 2. Navigation Flow

```
Client Request → Agent Service → Chrome Window → URL Navigation → Page Load → UIA Scan → Response
     │              │              │              │              │           │
     ▼              ▼              ▼              ▼              ▼           ▼
HTTP POST        Find Window    Send Keys      Wait for       Element      Return
/api/go         (UIA)         (Ctrl+L+URL)   Load Event     Discovery    Elements
```

### 3. Element Interaction Flow

```
Client Request → Agent Service → Element Search → UIA Action → Response
     │              │              │              │
     ▼              ▼              ▼              ▼
HTTP POST        Find Element   Click/Input    Return
/api/click      by ID          (UIA)          Result
```

### 4. Network Monitoring Flow

```
Chrome Extension → WebSocket → Agent Service → Response Storage → Client Request → Data Return
      │              │              │              │              │
      ▼              ▼              ▼              ▼              ▼
Debugger Event   JSON Message   Event Handler   Cache Store    HTTP GET
Network/Page     to Agent       Process Event   Response       /api/download
```

## Component Interaction Details

### Agent Service Internal Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Service                                  │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   HTTP API      │  │   WebSocket     │  │   Session       │              │
│  │   Endpoints     │  │   Handler       │  │   Manager       │              │
│  │                 │  │                 │  │                 │              │
│  │ • /api/start    │  │ • /ws/ext       │  │ • sessionS_     │              │
│  │ • /api/go       │  │ • Event         │  │   processO      │              │
│  │ • /api/click    │  │   Processing    │  │ • sessionS_     │              │
│  │ • /api/input    │  │ • Response      │  │   websocketO    │              │
│  │ • /api/download │  │   Caching       │  │ • sessionS_     │              │
│  │ • /api/destroy  │  │                 │  │   tabN_*        │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│           │                     │                     │                     │
│           └─────────────────────┼─────────────────────┘                     │
│                                 │                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Chrome        │  │   UIA           │  │   Network       │              │
│  │   Manager       │  │   Handler       │  │   Handler       │              │
│  │                 │  │                 │  │                 │              │
│  │ • Process       │  │ • Element       │  │ • Response      │              │
│  │   Creation      │  │   Discovery     │  │   Storage       │              │
│  │ • Instance      │  │ • Click         │  │ • Request       │              │
│  │   Management    │  │   Simulation    │  │   Tracking      │              │
│  │ • Cleanup       │  │ • Input         │  │ • Download      │              │
│  │                 │  │   Simulation    │  │   Handler       │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Chrome Extension Internal Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Chrome Extension                                  │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Background    │  │   Content       │  │   Popup         │              │
│  │   Script        │  │   Script        │  │   Interface     │              │
│  │                 │  │                 │  │                 │              │
│  │ • WebSocket     │  │ • Page          │  │ • User          │              │
│  │   Connection    │  │   Interaction   │  │   Interface     │              │
│  │ • Debugger      │  │ • DOM           │  │ • Settings      │              │
│  │   Events        │  │   Monitoring    │  │ • Status        │              │
│  │ • Tab Events    │  │ • Network       │  │   Display       │              │
│  │ • Navigation    │  │   Events        │  │                 │              │
│  │   Events        │  │                 │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│           │                     │                     │                     │
│           └─────────────────────┼─────────────────────┘                     │
│                                 │                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Debugger      │  │   Network       │  │   Event         │              │
│  │   Protocol      │  │   Monitoring    │  │   Handlers      │              │
│  │                 │  │                 │  │                 │              │
│  │ • Network.      │  │ • Response      │  │ • Tab Events    │              │
│  │   enable        │  │   Received      │  │ • Navigation    │              │
│  │ • Page.enable   │  │ • Loading       │  │   Events        │              │
│  │ • Event         │  │   Finished      │  │ • WebRequest    │              │
│  │   Listeners     │  │ • Request       │  │   Events        │              │
│  │                 │  │   Tracking      │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## State Management

### Session State Variables

```python
# Global state management in agent.py
sessionS_processO:dict = {}          # session_id -> {process}
sessionS_websocketO:dict = {}        # session_id -> {websocket}
replyS_textS:dict = {}               # reply_id -> text
sessionS_tabN_responseLS:dict = {}     # session_id -> tab_id -> [text]
sessionS_tabN_loadedLS:dict = {}       # session_id -> tab_id -> [text]
```

### State Transitions

```
Session Lifecycle:
┌─────────────┐    start    ┌─────────────┐    navigate    ┌─────────────┐
│   Idle      │ ──────────► │  Active     │ ────────────►  │  Working    │
│             │             │             │                │             │
└─────────────┘             └─────────────┘                └─────────────┘
       ▲                           │                           │
       │                           │                           │
       └───────────────────────────┼───────────────────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │  Destroyed  │
                            │             │
                            └─────────────┘
```

## Error Handling Architecture

### Error Types and Handling

1. **Chrome Process Errors**
   - Process creation failure
   - Extension loading failure
   - WebSocket connection failure

2. **UIA Interaction Errors**
   - Element not found
   - Element not clickable
   - Input validation errors

3. **Network Errors**
   - WebSocket disconnection
   - HTTP request failures
   - Response parsing errors

4. **Session Errors**
   - Invalid session ID
   - Session timeout
   - Resource cleanup failures

### Error Recovery Mechanisms

```python
# Example error recovery in agent.py
async def fun_chrome_start(session_id:str):
    try:
        chrome_process = subprocess.Popen(...)
        # Wait for WebSocket connection
        websocket_cfm = False
        for i in range(10):
            await asyncio.sleep(0.200)
            if(session_id in sessionS_websocketO):
                websocket_cfm = True
                break
        if(websocket_cfm):
            return chrome_process
        else:
            chrome_process.terminate()
            del sessionS_processO[session_id]
            return None
    except Exception as e:
        logger.error(f"Chrome start failed: {e}")
        return None
```

## Performance Considerations

### Memory Management
- **Session Isolation**: Each session uses separate Chrome user data directory
- **Response Caching**: Network responses cached with cleanup mechanisms
- **Process Cleanup**: Automatic termination of Chrome processes on session end

### Concurrency Handling
- **Async/Await**: Full async support for non-blocking operations
- **WebSocket Management**: Concurrent WebSocket connections per session
- **Database Pooling**: Connection pooling for database operations

### Scalability Features
- **Session Reuse**: Ability to resume existing sessions
- **Parallel Processing**: Support for multiple concurrent sessions
- **Resource Monitoring**: Real-time resource usage tracking

## Security Architecture

### Session Security
- **Session Isolation**: Complete isolation between sessions
- **User Data Cleanup**: Automatic cleanup of session data
- **Access Control**: Session ID validation for all operations

### Network Security
- **WebSocket Encryption**: Secure WebSocket connections
- **Request Validation**: Input validation and sanitization
- **Error Masking**: Sensitive error information not exposed

### Data Security
- **Database Encryption**: MySQL data encryption
- **Log Sanitization**: Sensitive data removed from logs
- **Access Logging**: Complete audit trail of all operations 