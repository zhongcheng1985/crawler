## 1. Network

```
┌─────────────────┐ WebSocket(8020)  ┌─────────────────┐
│    Chrome       │ ───────────────► │     agent       │
│ (uia_extension) │ ◄─────────────── │   (FastAPI)     │
└─────────────────┘   UIAutomation   └─────────────────┘
                                              ▲
                                              │ HTTP API(8020)
                                   ┌──────────┴──────────┐
                                   │   DispatcherClient  │
                                   │  (Asyncio Client)   │
                                   └──────────┬──────────┘
                                              │ TCP Socket(8010)
                                              ▼
                                   ┌─────────────────────┐                  ┌─────────────┐
                                   │  DispatcherServer   │ ◄────────────────│    USER     │
                                   │  (Asyncio Server)   │  HTTP API(8000)  │             │
                                   └──────────┬──────────┘                  └─────┬───────┘
                                              │ MySQL(3306)                       │
                                              ▼                                   │
                                       ┌─────────────┐                            │
                                       │    MySQL    │                            │
                                       │  Database   │                            │
                                       └─────────────┘                            │
                                              ▲                                   │Web Browser(80)
                                              │ MySQL(3306)                       ▼
                                     ┌────────┴────────┐                  ┌─────────────────┐
                                     │    dashboard    │ ◄─────────────── │   dashboard-ui  │
                                     │   (Flask API)   │   HTTP API(80)   │    (Vue.js)     │
                                     └─────────────────┘                  └─────────────────┘
```
