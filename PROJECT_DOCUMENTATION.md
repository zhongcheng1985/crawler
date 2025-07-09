# Crawler Project Documentation

## Overview

This project is a comprehensive web automation and crawling system that combines Chrome browser automation with UIA (UI Automation) for advanced web interaction capabilities. The system consists of three main components:

1. **Chrome Extension** (`uia_extension/`) - Monitors browser events and network traffic
2. **Agent Service** (`agent/`) - Core automation engine with HTTP API and WebSocket communication
3. **Dashboard** (`dashboard/`) - Web-based monitoring and management interface

## Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Chrome        │◄──────────────► │   Agent         │
│   Extension     │                 │   Service       │
│   (UIA)         │                 │   (Port 8000)   │
└─────────────────┘                 └─────────────────┘
                                              │
                                              │ HTTP API
                                              ▼
                                    ┌─────────────────┐
                                    │   Dashboard     │
                                    │   (MySQL)       │
                                    └─────────────────┘
```

## Component Details

### 1. Chrome Extension (`uia_extension/`)

**Purpose**: Monitors Chrome browser events and network traffic, communicates with the agent service via WebSocket.

**Key Files**:
- `manifest.json` - Extension configuration and permissions
- `background.js` - Service worker that handles WebSocket communication and debugger events
- `content.js` - Content script for page interaction
- `popup.html/js` - Extension popup interface

**Features**:
- **Debugger Integration**: Attaches Chrome DevTools Protocol debugger to monitor network events
- **Event Monitoring**: Tracks tab updates, navigation events, and network responses
- **WebSocket Communication**: Real-time communication with agent service
- **Network Monitoring**: Captures HTTP responses and request details

**Event Types Monitored**:
- `Network.responseReceived` - HTTP response headers
- `Page.loadEventFired` - Page load completion
- `tabs.onUpdated` - Tab status changes
- `webNavigation.onCompleted` - Navigation completion
- `webRequest.onResponseStarted` - Response initiation

### 2. Agent Service (`agent/`)

**Purpose**: Core automation engine that manages Chrome browser instances and provides HTTP API for external control.

**Key Files**:
- `agent.py` - Main service with FastAPI endpoints and WebSocket handling
- `demo.py` - Example usage demonstrating the API workflow

**Core Functionality**:

#### Session Management
- **Session Creation**: Each automation session gets a unique session ID
- **Chrome Instance Management**: Isolated Chrome instances per session
- **User Data Isolation**: Separate user data directories for each session

#### HTTP API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/api/start` | POST | Start new session | `session_id` (optional) |
| `/api/go` | POST | Navigate to URL | `session_id`, `url` |
| `/api/click` | POST | Click UI element | `session_id`, `element_id` |
| `/api/input` | POST | Input text/keys | `session_id`, `element_id`, `keys` |
| `/api/download` | POST | Download response body | `session_id`, `tab_id`, `request_id` |
| `/api/destroy` | POST | End session | `session_id` |

#### UIA Integration
- **Element Discovery**: Automatically discovers UI elements using Windows UIA
- **Element Interaction**: Click, input, and navigate through UI elements
- **Element Tree**: Hierarchical representation of UI elements

#### WebSocket Communication
- **Extension Communication**: Real-time communication with Chrome extension
- **Event Processing**: Handles browser events from extension
- **Response Caching**: Stores network responses for later retrieval

### 3. Dashboard (`dashboard/`)

**Purpose**: Web-based monitoring and management interface for the crawling system.

**Key Files**:
- `dashboard.py` - FastAPI application with dashboard endpoints
- `create_table.sql` - Database schema
- `test_data.sql` - Sample data for testing

**Database Schema**:

#### Tables
1. **crawler_info** - Crawler configuration and metadata
2. **crawler_status** - Real-time status of crawler instances
3. **crawler_session** - Session tracking and history
4. **api_log** - API call logging and monitoring

#### Dashboard Features
- **Crawler Management**: View and modify crawler configurations
- **Session Monitoring**: Track active and historical sessions
- **Log Analysis**: Monitor API calls and performance
- **Status Tracking**: Real-time crawler health monitoring

## Workflow Example

The `demo.py` file demonstrates a typical automation workflow:

1. **Start Session**: Create new Chrome instance
2. **Navigate**: Go to target URL
3. **Input Data**: Enter text into form fields
4. **Click Elements**: Interact with UI elements
5. **Cleanup**: Destroy session and cleanup resources

```python
# Example workflow from demo.py
session_id = start_session()
navigate_to_url(session_id, "http://example.com")
input_text(session_id, "element_id", "text{tab}more_text")
click_element(session_id, "button_element_id")
destroy_session(session_id)
```

## Technical Details

### Chrome Configuration
- **Isolated Instances**: Each session uses separate Chrome user data directory
- **Extension Loading**: UIA extension automatically loaded for each instance
- **Debugger Protocol**: Chrome DevTools Protocol for network monitoring
- **UIA Support**: Windows UI Automation for element interaction

### Network Monitoring
- **Response Capture**: Stores HTTP response bodies for analysis
- **Request Tracking**: Monitors all network requests and responses
- **Content Analysis**: Enables downloading and analyzing response content

### Element Interaction
- **UIA Integration**: Uses Windows UI Automation for reliable element detection
- **Element Identification**: Unique element IDs for precise targeting
- **Keyboard Simulation**: Supports complex keyboard input sequences
- **Click Simulation**: Native mouse click simulation

## Configuration

### Environment Variables
- `chrome_path`: Chrome executable path
- `ext_path`: Extension directory path
- `user_base`: User data base directory

### Database Configuration
- `DB_HOST`: MySQL host (default: localhost)
- `DB_USER`: MySQL username (default: root)
- `DB_PASSWORD`: MySQL password
- `DB_NAME`: Database name (default: dashboard)

## Security Considerations

1. **Session Isolation**: Each session uses isolated Chrome instances
2. **User Data Cleanup**: Automatic cleanup of session data
3. **Network Monitoring**: All network traffic is logged and monitored
4. **Access Control**: API endpoints require valid session IDs

## Performance Features

1. **Connection Pooling**: Database connection pooling for better performance
2. **Response Caching**: Network responses cached for quick access
3. **Session Reuse**: Ability to resume existing sessions
4. **Parallel Processing**: Support for multiple concurrent sessions

## Monitoring and Logging

1. **API Logging**: All API calls logged with timestamps
2. **Session Tracking**: Complete session lifecycle monitoring
3. **Performance Metrics**: Response times and status codes tracked
4. **Error Handling**: Comprehensive error logging and reporting

## Use Cases

1. **Web Scraping**: Automated data extraction from websites
2. **Form Automation**: Automated form filling and submission
3. **Testing**: Automated UI testing for web applications
4. **Monitoring**: Real-time website monitoring and alerting
5. **Data Collection**: Large-scale data collection from multiple sources

## Dependencies

### Agent Service
- FastAPI
- uvicorn
- uiautomation (Windows)
- asyncio
- subprocess

### Dashboard
- FastAPI
- mysql-connector-python
- pydantic

### Chrome Extension
- Chrome Extensions API
- WebSocket API
- Chrome Debugger Protocol

## Deployment

1. **Agent Service**: Run on port 8000 with WebSocket support
2. **Dashboard**: Run on separate port with MySQL database
3. **Chrome Extension**: Load into Chrome browser instances
4. **Database**: MySQL server with provided schema

This system provides a powerful foundation for web automation, scraping, and monitoring with enterprise-grade features for session management, monitoring, and scalability. 