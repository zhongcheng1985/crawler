## 1. Network

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│    Chrome       │ ───────────────► │     agent       │
│ (uia_extension) │ ◄─────────────── │   (FastAPI)     │
└─────────────────┘   UIAutomation   └─────────────────┘
                                              ▲
                                              │ HTTP API
                                   ┌──────────┴──────────┐
                                   │   DispatcherClient  │
                                   │  (Asyncio Client)   │
                                   └──────────┬──────────┘
                                              │ TCP Socket
                                              │
                                              │
                                              ▼
                                   ┌─────────────────────┐                ┌─────────────┐
                                   │  DispatcherServer   │ ◄──────────────│    USER     │
                                   │  (Asyncio Server)   │    HTTP API    │             │
                                   └──────────┬──────────┘                └─────┬───────┘
                                              │ MySQL                           │ Web Browser
                                              ▼                                 │
                                       ┌─────────────┐                          │
                                       │    MySQL    │                          │
                                       │  Database   │                          │
                                       └─────────────┘                          │
                                              ▲                                 │
                                              │ MySQL                           ▼
                                     ┌────────┴────────┐                  ┌─────────────────┐
                                     │    dashboard    │ ◄─────────────── │   dashboard-ui  │
                                     │   (Flask API)   │     HTTP API     │    (Vue.js)     │
                                     └─────────────────┘                  └─────────────────┘
```
