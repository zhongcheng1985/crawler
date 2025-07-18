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
pip install fastapi uvicorn[standard] psutil uiautomation
```

## Initialization & How to Run
1. Install dependencies (see above)
2. Enter the agent directory:
   ```bash
   cd agent
   ```
3. Start the service:
   ```bash
   python agent.py
   ```
   By default, it listens on 127.0.0.1:8020

## API Endpoints

### 1. POST /api/start
- **Description**: Start a new browser session
- **Request Header**:
  - `X-Session-Id` (str, optional): Session ID
- **Request Body**:
  - `proxy` (str, optional): Proxy server address
- **Response**:
  - `session_id` (str): The new or reused session ID

### 2. POST /api/go
- **Description**: Navigate the browser to a specified URL
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Request Body**:
  - `url` (str): Target URL
- **Response**:
  - `url` (str): Target URL
  - `title` (str): Page title
  - `elements` (tree): UI tree structure of the page
  - `responses` (list): HTTP response info of the active tab

### 3. POST /api/view
- **Description**: Get the current page UI tree and HTTP responses
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Response**:
  - `elements` (tree): UI tree structure of the page
  - `responses` (list): HTTP response info of the active tab

### 4. POST /api/download
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

### 5. POST /api/click
- **Description**: Click a page element
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Request Body**:
  - `element_id` (str): Element ID
- **Response**:
  - `element_id` (str)
  - `text` (str): Name of the element after click

### 6. POST /api/input
- **Description**: Input text into a page element
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Request Body**:
  - `element_id` (str): Element ID
  - `keys` (str): Input text
- **Response**:
  - `element_id` (str)
  - `keys` (str): Actual input text

### 7. POST /api/destroy
- **Description**: Destroy a session, close the browser, and clean up data
- **Request Header**:
  - `X-Session-Id` (str): Session ID
- **Response**:
  - `session_id` (str): The destroyed session ID

### 8. WebSocket /ws/ext
- **Description**: WebSocket channel for browser extension to communicate with agent
- **Usage**: The extension will be automatically bound to the corresponding session after connecting

---

For more details, please refer to the agent.py source code. 