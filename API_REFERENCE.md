# API Reference

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API does not require authentication. All endpoints are accessible without authentication tokens.

## Common Response Format
All API responses follow this format:
```json
{
  "session_id": "string",
  "status": "success|error",
  "message": "string (optional)",
  "data": "object (optional)"
}
```

## HTTP API Endpoints

### 1. Start Session

**Endpoint:** `POST /api/start`

**Description:** Creates a new Chrome browser session or resumes an existing one.

**Request Body:**
```json
{
  "session_id": "string (optional)"
}
```

**Response:**
```json
{
  "session_id": "abc12345"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Notes:**
- If `session_id` is not provided, a new session will be created
- If `session_id` is provided and exists, the session will be resumed
- Each session creates an isolated Chrome instance with its own user data directory

### 2. Navigate to URL

**Endpoint:** `POST /api/go`

**Description:** Navigates to a specified URL and returns page elements and network responses.

**Request Body:**
```json
{
  "session_id": "string (required)",
  "url": "string (required)"
}
```

**Response:**
```json
{
  "session_id": "abc12345",
  "url": "https://example.com",
  "title": "Example Domain",
  "elements": [
    {
      "element_id": "10_185_222_213",
      "name": "Search Input",
      "control_type": "Edit",
      "children": []
    },
    {
      "element_id": "445_185_485_213",
      "name": "Submit Button",
      "control_type": "Button",
      "children": []
    }
  ],
  "responses": [
    {
      "request_id": "12345.1",
      "url": "https://example.com/",
      "content_type": "text/html",
      "content_length": "1234",
      "status": "200"
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/go \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc12345",
    "url": "https://example.com"
  }'
```

**Notes:**
- The system waits for the page to fully load before returning elements
- Elements are discovered using Windows UIA (UI Automation)
- Network responses are captured and returned for analysis

### 3. Click Element

**Endpoint:** `POST /api/click`

**Description:** Clicks on a UI element identified by its element ID.

**Request Body:**
```json
{
  "session_id": "string (required)",
  "element_id": "string (required)"
}
```

**Response:**
```json
{
  "session_id": "abc12345",
  "element_id": "445_185_485_213",
  "text": "Submit Button"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/click \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc12345",
    "element_id": "445_185_485_213"
  }'
```

**Notes:**
- Element ID must be obtained from a previous `/api/go` call
- Uses Windows UIA for reliable element interaction
- Returns the element name for confirmation

### 4. Input Text/Keys

**Endpoint:** `POST /api/input`

**Description:** Inputs text or keyboard sequences into a UI element.

**Request Body:**
```json
{
  "session_id": "string (required)",
  "element_id": "string (required)",
  "keys": "string (required)"
}
```

**Response:**
```json
{
  "session_id": "abc12345",
  "element_id": "10_185_222_213",
  "keys": "abcdef{tab}123456"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/input \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc12345",
    "element_id": "10_185_222_213",
    "keys": "hello{tab}world"
  }'
```

**Special Keys:**
- `{tab}` - Tab key
- `{enter}` - Enter key
- `{ctrl}` - Ctrl key
- `{alt}` - Alt key
- `{shift}` - Shift key
- `{space}` - Space key
- `{backspace}` - Backspace key
- `{delete}` - Delete key
- `{home}` - Home key
- `{end}` - End key
- `{pageup}` - Page Up key
- `{pagedown}` - Page Down key

**Notes:**
- Supports complex keyboard sequences
- Can combine text and special keys
- Uses Windows UIA for reliable input simulation

### 5. Download Response Body

**Endpoint:** `POST /api/download`

**Description:** Downloads the response body for a specific network request.

**Request Body:**
```json
{
  "session_id": "string (required)",
  "tab_id": "integer (required)",
  "request_id": "string (required)"
}
```

**Response:**
```json
{
  "session_id": "abc12345",
  "tab_id": 123,
  "request_id": "12345.1",
  "data": "base64_encoded_content"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc12345",
    "tab_id": 123,
    "request_id": "12345.1"
  }'
```

**Notes:**
- `tab_id` and `request_id` are obtained from network responses in `/api/go`
- Response body is base64 encoded
- Only available for requests that have completed loading

### 6. Destroy Session

**Endpoint:** `POST /api/destroy`

**Description:** Terminates a Chrome session and cleans up resources.

**Request Body:**
```json
{
  "session_id": "string (required)"
}
```

**Response:**
```json
{
  "session_id": "abc12345"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/destroy \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc12345"
  }'
```

**Notes:**
- Terminates the Chrome process
- Cleans up user data directory
- Removes session from memory
- Should be called to prevent resource leaks

## WebSocket API

### WebSocket Connection

**URL:** `ws://localhost:8000/ws/ext`

**Description:** Real-time communication channel between Chrome extension and agent service.

### Message Format

**Request:**
```json
{
  "id": "unique_message_id",
  "command": "command_name",
  "params": "object (optional)",
  "data": "object (optional)"
}
```

**Response:**
```json
{
  "id": "unique_message_id",
  "reply": "original_message_id",
  "command": "response_command",
  "data": "object (optional)",
  "error": "string (optional)"
}
```

### Available Commands

#### 1. Request.queryTabs
**Description:** Get list of all tabs in the current window.

**Request:**
```json
{
  "id": "msg123",
  "command": "Request.queryTabs"
}
```

**Response:**
```json
{
  "id": "msg456",
  "reply": "msg123",
  "command": "Response.queryTabs",
  "data": [
    {
      "id": 123,
      "url": "https://example.com",
      "title": "Example Domain",
      "active": true
    }
  ]
}
```

#### 2. Request.Network.getResponseBody
**Description:** Get response body for a specific network request.

**Request:**
```json
{
  "id": "msg123",
  "command": "Request.Network.getResponseBody",
  "params": {
    "tabId": 123,
    "requestId": "12345.1"
  }
}
```

**Response:**
```json
{
  "id": "msg456",
  "reply": "msg123",
  "command": "Response.Network.getResponseBody",
  "data": {
    "body": "response_content",
    "base64Encoded": false
  }
}
```

## Dashboard API Endpoints

### Base URL
```
http://localhost:8001 (or configured port)
```

### 1. Crawler Grid

**Endpoint:** `POST /crawler/grid`

**Description:** Get paginated list of crawler instances.

**Request Body:**
```json
{
  "pagination": {
    "page_num": 1,
    "page_size": 10
  },
  "keyword": "string (optional)"
}
```

**Response:**
```json
{
  "total": 5,
  "rows": [
    {
      "id": 1,
      "host_name": "crawler-01",
      "alias": "Primary Crawler",
      "ip": "192.168.1.100",
      "os": "Windows 10",
      "agent": "Chrome/91.0",
      "last_heartbeat": "2024-01-15T10:30:00",
      "status": 10
    }
  ]
}
```

### 2. Modify Crawler

**Endpoint:** `POST /crawler/modify`

**Description:** Update crawler configuration.

**Request Body:**
```json
{
  "id": 1,
  "alias": "Updated Alias",
  "max_browser_count": 5
}
```

**Response:**
```json
{
  "id": 1,
  "host_name": "crawler-01",
  "alias": "Updated Alias",
  "ip": "192.168.1.100",
  "os": "Windows 10",
  "agent": "Chrome/91.0",
  "last_heartbeat": "2024-01-15T10:30:00",
  "status": 10
}
```

### 3. Session Grid

**Endpoint:** `POST /session/grid`

**Description:** Get paginated list of crawler sessions.

**Request Body:**
```json
{
  "pagination": {
    "page_num": 1,
    "page_size": 10
  },
  "keyword": "string (optional)",
  "crawler_id": 1,
  "session_id": "abc12345"
}
```

**Response:**
```json
{
  "total": 3,
  "rows": [
    {
      "id": 1,
      "crawler_id": 1,
      "session": "abc12345",
      "init_time": "2024-01-15T10:30:00",
      "url": "https://example.com",
      "title": "Example Domain",
      "destroy_time": null
    }
  ]
}
```

### 4. Log Grid

**Endpoint:** `POST /log/grid`

**Description:** Get paginated list of API logs.

**Request Body:**
```json
{
  "pagination": {
    "page_num": 1,
    "page_size": 10
  },
  "keyword": "string (optional)",
  "crawler_id": 1,
  "session_id": "abc12345"
}
```

**Response:**
```json
{
  "total": 10,
  "rows": [
    {
      "id": 1,
      "crawler_session_id": 1,
      "api": "/api/go",
      "request_time": "2024-01-15T10:30:00",
      "response_time": "2024-01-15T10:30:05",
      "status_code": 200
    }
  ]
}
```

## Error Codes

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (session or element not found)
- `500` - Internal Server Error

### Common Error Responses

**Invalid Session:**
```json
{
  "error": "Session not found",
  "session_id": "invalid_session"
}
```

**Element Not Found:**
```json
{
  "error": "Element not found",
  "element_id": "invalid_element"
}
```

**Chrome Process Error:**
```json
{
  "error": "Failed to start Chrome process",
  "session_id": "abc12345"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. However, it's recommended to:
- Limit concurrent sessions per client
- Implement appropriate delays between requests
- Monitor resource usage

## Best Practices

### Session Management
1. Always call `/api/destroy` when done with a session
2. Reuse sessions when possible to avoid overhead
3. Monitor session count to prevent resource exhaustion

### Element Interaction
1. Wait for page load before interacting with elements
2. Use unique element IDs from `/api/go` responses
3. Handle dynamic content that may change element IDs

### Error Handling
1. Always check for error responses
2. Implement retry logic for transient failures
3. Log errors for debugging

### Performance
1. Use appropriate page load wait times
2. Minimize unnecessary navigation
3. Clean up sessions promptly

## Examples

### Complete Workflow Example

```python
import requests
import json

# 1. Start session
response = requests.post('http://localhost:8000/api/start', json={})
session_id = response.json()['session_id']

# 2. Navigate to page
response = requests.post('http://localhost:8000/api/go', json={
    'session_id': session_id,
    'url': 'https://example.com'
})
elements = response.json()['elements']

# 3. Find and click a button
button_element = next(e for e in elements if 'Submit' in e['name'])
response = requests.post('http://localhost:8000/api/click', json={
    'session_id': session_id,
    'element_id': button_element['element_id']
})

# 4. Input text into a field
input_element = next(e for e in elements if e['control_type'] == 'Edit')
response = requests.post('http://localhost:8000/api/input', json={
    'session_id': session_id,
    'element_id': input_element['element_id'],
    'keys': 'Hello World{enter}'
})

# 5. Clean up
requests.post('http://localhost:8000/api/destroy', json={
    'session_id': session_id
})
```

### JavaScript Example

```javascript
// Start session
const startResponse = await fetch('http://localhost:8000/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
});
const { session_id } = await startResponse.json();

// Navigate to page
const goResponse = await fetch('http://localhost:8000/api/go', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_id,
        url: 'https://example.com'
    })
});
const { elements } = await goResponse.json();

// Click element
const buttonElement = elements.find(e => e.name.includes('Submit'));
await fetch('http://localhost:8000/api/click', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_id,
        element_id: buttonElement.element_id
    })
});

// Clean up
await fetch('http://localhost:8000/api/destroy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id })
});
``` 