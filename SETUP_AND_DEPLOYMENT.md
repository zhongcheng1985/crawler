# Setup and Deployment Guide

## Prerequisites

### System Requirements
- **Operating System**: Windows 10/11 (required for UIA support)
- **Python**: 3.8 or higher
- **Chrome Browser**: Latest stable version
- **MySQL**: 8.0 or higher
- **Memory**: Minimum 4GB RAM, 8GB recommended
- **Storage**: At least 2GB free space

### Software Dependencies
- **Chrome Browser**: Must be installed and accessible via command line
- **MySQL Server**: For dashboard database
- **Python Dependencies**: Listed in requirements.txt

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd crawler
```

### 2. Install Python Dependencies

Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

Install required packages:
```bash
pip install fastapi uvicorn uiautomation mysql-connector-python pydantic
```

Or install from requirements file (if available):
```bash
pip install -r requirements.txt
```

### 3. Database Setup

#### Install MySQL
1. Download and install MySQL Server 8.0+
2. Set root password during installation
3. Ensure MySQL service is running

#### Create Database
```bash
mysql -u root -p < dashboard/create_table.sql
```

#### Insert Test Data (Optional)
```bash
mysql -u root -p dashboard < dashboard/test_data.sql
```

### 4. Chrome Extension Setup

#### Load Extension in Chrome
1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `uia_extension/` directory

#### Verify Extension
- The extension should appear in the extensions list
- Check that it shows as "Enabled"

## Configuration

### 1. Agent Service Configuration

Edit `agent/agent.py` and update the following paths:

```python
# Chrome executable path
chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

# Extension path (relative to project root)
ext_path = r'path\to\your\project\uia_extension'

# User data base directory
user_base = r'C:\temp\chrome_sessions'  # or your preferred location
```

### 2. Database Configuration

Set environment variables for the dashboard:

```bash
# Windows
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=your_password
set DB_NAME=dashboard

# Linux/Mac
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=dashboard
```

Or create a `.env` file in the dashboard directory:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=dashboard
```

### 3. Network Configuration

#### Firewall Settings
- **Agent Service**: Port 8000 (HTTP and WebSocket)
- **Dashboard**: Port 8001 (HTTP)
- **MySQL**: Port 3306 (TCP)

#### Windows Firewall
```bash
# Allow agent service
netsh advfirewall firewall add rule name="Crawler Agent" dir=in action=allow protocol=TCP localport=8000

# Allow dashboard
netsh advfirewall firewall add rule name="Crawler Dashboard" dir=in action=allow protocol=TCP localport=8001
```

## Running the System

### 1. Start Agent Service

```bash
cd agent
python agent.py
```

The service will start on `http://localhost:8000`

### 2. Start Dashboard (Optional)

```bash
cd dashboard
python dashboard.py
```

The dashboard will start on `http://localhost:8001`

### 3. Test the System

#### Quick Test
```bash
cd agent
python demo.py
```

This will run a complete workflow demonstration.

#### Manual Test
```bash
# Start a session
curl -X POST http://localhost:8000/api/start \
  -H "Content-Type: application/json" \
  -d '{}'

# Navigate to a page
curl -X POST http://localhost:8000/api/go \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your_session_id",
    "url": "https://example.com"
  }'
```

## Production Deployment

### 1. Systemd Service (Linux)

Create `/etc/systemd/system/crawler-agent.service`:
```ini
[Unit]
Description=Crawler Agent Service
After=network.target

[Service]
Type=simple
User=crawler
WorkingDirectory=/opt/crawler/agent
Environment=PATH=/opt/crawler/venv/bin
ExecStart=/opt/crawler/venv/bin/python agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/crawler-dashboard.service`:
```ini
[Unit]
Description=Crawler Dashboard Service
After=network.target mysql.service

[Service]
Type=simple
User=crawler
WorkingDirectory=/opt/crawler/dashboard
Environment=PATH=/opt/crawler/venv/bin
Environment=DB_HOST=localhost
Environment=DB_USER=crawler_user
Environment=DB_PASSWORD=secure_password
Environment=DB_NAME=dashboard
ExecStart=/opt/crawler/venv/bin/python dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl enable crawler-agent
sudo systemctl enable crawler-dashboard
sudo systemctl start crawler-agent
sudo systemctl start crawler-dashboard
```

### 2. Windows Service

Create `install_service.bat`:
```batch
@echo off
sc create "CrawlerAgent" binPath= "C:\path\to\python.exe C:\path\to\agent\agent.py" start= auto
sc description "CrawlerAgent" "Crawler Agent Service"
sc start "CrawlerAgent"
```

### 3. Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000 8001

# Start services
CMD ["python", "agent/agent.py"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: dashboard
    volumes:
      - mysql_data:/var/lib/mysql
      - ./dashboard/create_table.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"

  agent:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - mysql
    environment:
      - DB_HOST=mysql
      - DB_USER=root
      - DB_PASSWORD=root_password
      - DB_NAME=dashboard

  dashboard:
    build: .
    command: python dashboard/dashboard.py
    ports:
      - "8001:8001"
    depends_on:
      - mysql
    environment:
      - DB_HOST=mysql
      - DB_USER=root
      - DB_PASSWORD=root_password
      - DB_NAME=dashboard

volumes:
  mysql_data:
```

Run with Docker Compose:
```bash
docker-compose up -d
```

## Monitoring and Logging

### 1. Log Configuration

The system uses Python's logging module. Configure logging in `agent/agent.py`:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)
```

### 2. Health Checks

Create a health check endpoint:

```python
@app.get('/health')
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessionS_processO)
    }
```

### 3. Monitoring Script

Create `monitor.py`:
```python
import requests
import time
import json

def check_health():
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Active Sessions: {data['active_sessions']}")
            return True
        else:
            print(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Health check error: {e}")
        return False

if __name__ == '__main__':
    while True:
        check_health()
        time.sleep(30)
```

## Troubleshooting

### Common Issues

#### 1. Chrome Process Not Starting
**Symptoms**: Session creation fails
**Solutions**:
- Verify Chrome path is correct
- Check Chrome is installed and accessible
- Ensure sufficient system resources

#### 2. WebSocket Connection Failed
**Symptoms**: Extension can't connect to agent
**Solutions**:
- Check firewall settings
- Verify agent service is running
- Check port 8000 is available

#### 3. UIA Elements Not Found
**Symptoms**: Element interaction fails
**Solutions**:
- Ensure Windows UIA is enabled
- Check element IDs are current
- Wait for page to fully load

#### 4. Database Connection Failed
**Symptoms**: Dashboard errors
**Solutions**:
- Verify MySQL is running
- Check database credentials
- Ensure database exists

### Debug Mode

Enable debug logging:
```python
logger.setLevel(logging.DEBUG)
```

### Performance Tuning

#### 1. Chrome Configuration
```python
chrome_args = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-software-rasterizer',
    '--disable-extensions-except=' + ext_path,
    '--load-extension=' + ext_path,
    '--user-data-dir=' + user_path
]
```

#### 2. Database Optimization
```sql
-- Add indexes for better performance
CREATE INDEX idx_session_active ON crawler_session(destroy_time);
CREATE INDEX idx_log_timestamp ON api_log(request_time);
```

#### 3. Memory Management
```python
# Limit concurrent sessions
MAX_SESSIONS = 10

# Cleanup old sessions
async def cleanup_old_sessions():
    # Implementation here
    pass
```

## Security Considerations

### 1. Network Security
- Use HTTPS in production
- Implement API authentication
- Restrict access to trusted IPs

### 2. Data Security
- Encrypt sensitive data
- Implement proper session management
- Regular security updates

### 3. Access Control
- Use dedicated database user
- Implement role-based access
- Audit logging

## Backup and Recovery

### 1. Database Backup
```bash
# Create backup
mysqldump -u root -p dashboard > backup.sql

# Restore backup
mysql -u root -p dashboard < backup.sql
```

### 2. Configuration Backup
```bash
# Backup configuration files
tar -czf config_backup.tar.gz agent/ dashboard/
```

### 3. Session Recovery
The system supports session recovery by providing the session_id in `/api/start`:
```python
# Resume existing session
response = requests.post('/api/start', json={
    'session_id': 'existing_session_id'
})
```

## Scaling Considerations

### 1. Horizontal Scaling
- Deploy multiple agent instances
- Use load balancer
- Implement session distribution

### 2. Vertical Scaling
- Increase system resources
- Optimize Chrome instances
- Database connection pooling

### 3. Monitoring
- Implement metrics collection
- Set up alerting
- Performance monitoring

This setup guide provides a comprehensive approach to deploying the crawler system in various environments, from development to production. 