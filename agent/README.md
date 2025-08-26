# Agent Documentation

## Environment
- Python 3.8 or higher
- Windows OS (requires UIAutomation)

## Dependencies
- fastapi
- uvicorn[standard]
- psutil
- uiautomation

Install dependencies:
```bash
pip install fastapi "uvicorn[standard]" psutil uiautomation
```

## Initialization & How to Run
1. Install dependencies (see above)
2. Start the service from the project root:
   ```bash
   python agent.py
   ```
   By default, it listens on 127.0.0.1:8020

## API Endpoints

### 1. POST /api/start
- **Description**: Start a new Chrome session
- **Request Header**:
  - `X-Session-Id` (str, optional): Session ID (if provided and alive, will be reused)
- **Request Body**:
  - `proxy` (str, optional): Proxy URL. Supports `scheme://username:password@host:port`
  - `extension` (bool, optional): Whether to load the bundled extension. Default `true`
- **Response/Header**:
  - Header `X-Session-Id`: The active session ID
  - Body `{ session_id }`

### 2. POST /api/go
- **Description**: Navigate the browser to a specified URL
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Request Body**:
  - `url` (str): Target URL
- **Response**:
  - `url` (str)
  - `title` (str, optional)

### 3. POST /api/maximize
- **Description**: Maximize the browser window
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Response**:
  - `title` (str, optional): Current page title

### 4. POST /api/view
- **Description**: Get the current page UI tree
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Response**:
  - `elements` (tree): UI tree structure of the page

### 5. POST /api/network
- **Description**: List network responses for the active tab
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Response**:
  - `responses` (list): Each item may include `tab_id`, `request_id`, `url`, `status`, `content_type`, `content_length`

### 6. POST /api/download
- **Description**: Download the response body of a specific request
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Request Body**:
  - `tab_id` (int): Tab ID
  - `request_id` (str): Request ID
- **Response**:
  - `tab_id` (int)
  - `request_id` (str)
  - `data` (object): Response body content

### 7. POST /api/click
- **Description**: Click a page element
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Request Body**:
  - `element_id` (str): Element ID
- **Response**:
  - `element_id` (str)
  - `text` (str): Name of the element after click

### 8. POST /api/input
- **Description**: Input text into a page element
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Request Body**:
  - `element_id` (str): Element ID
  - `keys` (str): Input text
- **Response**:
  - `element_id` (str)
  - `keys` (str): Actual input text

### 9. POST /api/destroy
- **Description**: Destroy a session, close the browser, and clean up data
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Response**:
  - `session_id` (str): The destroyed session ID

### 10. WebSocket /ws/ext
- **Description**: WebSocket channel for browser extension to communicate with agent
- **Usage**: The extension will be automatically bound to the corresponding session after connecting

---

## Notes
- On start, if a proxy with credentials is provided, the agent auto-fills HTTP auth dialogs.
- Paths like `CONST_USER_BASE`, `CONST_CHROME_BASE`, and `CONST_EXTENSION_BASE` are configured in `agent.py`.
- A demo client is available in `demo.py` showing start → go → input → click → destroy.

---

For more details, please refer to the `agent.py` source code.

## Quickstart
1. Start the server:
   ```bash
   python agent.py
   ```
2. In another terminal, run the demo flow (start → go → input → click → destroy):
   ```bash
   python demo.py
   ```

## cURL examples

Note: Replace the placeholder `SESSION_ID` with the value returned by `/api/start`.

### Start session
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"proxy":"http://user:pass@127.0.0.1:8888","extension":true}' \
  http://127.0.0.1:8020/api/start
```

### Navigate
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{"url":"http://127.0.0.1:8020/demo.html"}' \
  http://127.0.0.1:8020/api/go
```

### Maximize window
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{}' \
  http://127.0.0.1:8020/api/maximize
```

### View UI tree
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{}' \
  http://127.0.0.1:8020/api/view
```

### List network responses (active tab)
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{}' \
  http://127.0.0.1:8020/api/network
```

### Download a response body
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{"tab_id":TAB_ID,"request_id":"REQUEST_ID"}' \
  http://127.0.0.1:8020/api/download
```

### Click an element
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{"element_id":"LEFT_TOP_RIGHT_BOTTOM"}' \
  http://127.0.0.1:8020/api/click
```

### Input text into an element
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{"element_id":"LEFT_TOP_RIGHT_BOTTOM","keys":"abcdef{tab}123456"}' \
  http://127.0.0.1:8020/api/input
```

### Destroy session
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: SESSION_ID" \
  -d '{}' \
  http://127.0.0.1:8020/api/destroy
```