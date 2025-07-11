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
│                              Dispatcher Layer                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Load Balancer (Port 8080)                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐     │    │
│  │  │   Request   │  │   Session   │  │   Client    │  │   Log   │     │    │
│  │  │   Router    │  │  Manager    │  │  Manager    │  │ Handler │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Service Layer                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Application (Port 8020)                  │    │
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
Client Request → Dispatcher → Agent Service → Chrome Process Creation → Extension Loading → WebSocket Connection → Session Ready
     │              │              │                    │                      │                    │
     ▼              ▼              ▼                    ▼                      ▼                    ▼
HTTP POST        Route to       Session ID         Chrome Instance        Extension         WebSocket
/api/start      Available      Generation         with UIA Ext          Auto-load         Connection
                Agent
```

### 2. Navigation Flow

```
Client Request → Dispatcher → Agent Service → Chrome Window → URL Navigation → Page Load → UIA Scan → Response
     │              │              │              │              │              │           │
     ▼              ▼              ▼              ▼              ▼              ▼           ▼
HTTP POST        Route to       Find Window    Send Keys      Wait for       Element      Return
/api/go         Available      (UIA)         (Ctrl+L+URL)   Load Event     Discovery    Elements
                Agent
```

### 3. Element Interaction Flow

```
Client Request → Dispatcher → Agent Service → Element Search → UIA Action → Response
     │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼
HTTP POST        Route to       Find Element   Click/Input    Return
/api/click      Available      by ID          (UIA)          Result
                Agent
```

### 4. Network Monitoring Flow

```
Chrome Extension → WebSocket → Agent Service → Response Storage → Dispatcher → Client Request → Data Return
      │              │              │              │              │              │
      ▼              ▼              ▼              ▼              ▼              ▼
Debugger Event   JSON Message   Event Handler   Cache Store    Route Request  HTTP GET
Network/Page     to Agent       Process Event   Response       to Agent       /api/download
```

## Component Interaction Details

### Dispatcher Internal Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Dispatcher Service                              │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   HTTP Proxy    │  │   Session       │  │   Client        │              │
│  │   Handler       │  │   Manager       │  │   Manager       │              │
│  │                 │  │                 │  │                 │              │
│  │ • Request       │  │ • sessionS_     │  │ • clients       │              │
│  │   Routing       │  │   mapping       │  │   queue         │              │
│  │ • Header        │  │ • session       │  │ • health        │              │
│  │   Parsing       │  │   tracking      │  │   monitoring    │              │
│  │ • Response      │  │ • request       │  │ • failover      │              │
│  │   Forwarding    │  │   logging       │  │   handling      │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│           │                     │                     │                     │
│           └─────────────────────┼─────────────────────┘                     │
│                                 │                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Load          │  │   Health        │  │   Logging       │              │
│  │   Balancer      │  │   Monitor       │  │   System        │              │
│  │                 │  │                 │  │                 │              │
│  │ • Round-robin   │  │ • Client        │  │ • Request       │              │
│  │   distribution  │  │   status        │  │   logging       │              │
│  │ • Session       │  │   tracking      │  │ • Response      │              │
│  │   affinity      │  │ • Connection    │  │   logging       │              │
│  │ • Failover      │  │   monitoring    │  │ • Error         │              │
│  │   logic         │  │ • Auto-recovery │  │   tracking      │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

### Dashboard Frontend Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Dashboard Frontend                                │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Vue Router    │  │   Pinia Store   │  │   API Client    │              │
│  │                 │  │                 │  │                 │              │
│  │ • Route         │  │ • State         │  │ • HTTP Client   │              │
│  │   Management    │  │   Management    │  │ • Request       │              │
│  │ • Navigation    │  │ • Session       │  │   Interceptors  │              │
│  │   Guards        │  │   Storage       │  │ • Response      │              │
│  │ • Lazy          │  │ • Real-time     │  │   Handling      │              │
│  │   Loading       │  │   Updates       │  │ • Error         │              │
│  │                 │  │                 │  │   Handling      │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│           │                     │                     │                     │
│           └─────────────────────┼─────────────────────┘                     │
│                                 │                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Views         │  │   Components    │  │   Utils         │              │
│  │                 │  │                 │  │                 │              │
│  │ • Crawler       │  │ • Common        │  │ • Date          │              │
│  │   Management    │  │   Components    │  │   Formatting    │              │
│  │ • Session       │  │ • Charts        │  │ • Validation    │              │
│  │   Monitoring    │  │ • Tables        │  │ • API           │              │
│  │ • Log           │  │ • Forms         │  │   Helpers       │              │
│  │   Analysis      │  │ • Modals        │  │ • Constants     │              │
│  │                 │  │                 │  │                 │              │
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

### Dispatcher State Variables

```python
# Global state management in DispatcherServer.py
clients: deque = deque()                    # Active client connections
sessions: dict = {}                        # session_id -> SessionInfo
requests: list = []                        # List of RequestInfo objects

@dataclass
class ClientInfo:
    reader: Any
    writer: Any
    ip: str
    port: int
    connect_time: datetime.datetime
    disconnect_time: Optional[datetime.datetime] = None

@dataclass
class SessionInfo:
    session: str
    client: ClientInfo
    init_time: datetime.datetime
    destroy_time: Optional[datetime.datetime] = None

@dataclass
class RequestInfo:
    session: SessionInfo
    method: str
    url: str
    request_time: datetime.datetime
    response_time: Optional[datetime.datetime] = None
    status_code: Optional[int] = None
```

### Agent Service State Variables

```python
# Global state management in agent.py
sessionS_processO:dict = {}          # session_id -> {process}
sessionS_websocketO:dict = {}        # session_id -> {websocket}
replyS_textS:dict = {}               # reply_id -> text
sessionS_tabN_responseLS:dict = {}     # session_id -> tab_id -> [text]
sessionS_tabN_loadedLS:dict = {}       # session_id -> tab_id -> [text]
```

### Dashboard Frontend State

```javascript
// Pinia store structure
export const useMainStore = defineStore('main', {
  state: () => ({
    crawlers: [],
    sessions: [],
    logs: [],
    loading: false,
    error: null
  }),
  
  actions: {
    async fetchCrawlers() { /* ... */ },
    async fetchSessions() { /* ... */ },
    async fetchLogs() { /* ... */ }
  }
})
```

## State Transitions

### Dispatcher State Transitions

```
Client Lifecycle:
┌─────────────┐    connect    ┌─────────────┐    disconnect    ┌─────────────┐
│   Idle      │ ────────────► │  Connected  │ ───────────────► │ Disconnected│
│             │               │             │                  │             │
└─────────────┘               └─────────────┘                  └─────────────┘
       ▲                              │                              │
       │                              │                              │
       └──────────────────────────────┼──────────────────────────────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │  Available  │
                               │   for Load  │
                               │  Balancing  │
                               └─────────────┘
```

### Session State Transitions

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

1. **Dispatcher Errors**
   - Client connection failures
   - Load balancing failures
   - Session routing errors
   - Health check failures

2. **Chrome Process Errors**
   - Process creation failure
   - Extension loading failure
   - WebSocket connection failure

3. **UIA Interaction Errors**
   - Element not found
   - Element not clickable
   - Input validation errors

4. **Network Errors**
   - WebSocket disconnection
   - HTTP request failures
   - Response parsing errors

5. **Session Errors**
   - Invalid session ID
   - Session timeout
   - Resource cleanup failures

### Error Recovery Mechanisms

```python
# Example error recovery in DispatcherServer.py
async def handle_client(reader, writer):
    try:
        # Handle client connection
        await writer.wait_closed()
    except Exception as e:
        logging.error(f"Client error: {e}")
    finally:
        # Cleanup client resources
        disconnect_time = datetime.datetime.now()
        client_info.disconnect_time = disconnect_time
```

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
- **Client Pool Management**: Efficient client connection pooling in dispatcher

### Concurrency Handling
- **Async/Await**: Full async support for non-blocking operations
- **WebSocket Management**: Concurrent WebSocket connections per session
- **Database Pooling**: Connection pooling for database operations
- **Load Balancing**: Distributed request handling across multiple agents

### Scalability Features
- **Session Reuse**: Ability to resume existing sessions
- **Parallel Processing**: Support for multiple concurrent sessions
- **Resource Monitoring**: Real-time resource usage tracking
- **Horizontal Scaling**: Multiple agent instances with dispatcher load balancing
- **Frontend Optimization**: Vue.js 3 with Vite for fast development and builds

## Security Architecture

### Session Security
- **Session Isolation**: Complete isolation between sessions
- **User Data Cleanup**: Automatic cleanup of session data
- **Access Control**: Session ID validation for all operations
- **Load Balancer Security**: Additional security layer through dispatcher

### Network Security
- **WebSocket Encryption**: Secure WebSocket connections
- **Request Validation**: Input validation and sanitization
- **Error Masking**: Sensitive error information not exposed
- **HTTP Proxy Security**: Secure proxy handling in dispatcher

### Data Security
- **Database Encryption**: MySQL data encryption
- **Log Sanitization**: Sensitive data removed from logs
- **Access Logging**: Complete audit trail of all operations 
- **Frontend Security**: Vue.js security best practices 