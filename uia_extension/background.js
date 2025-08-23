console.log('Background service worker running!');

// ==========  ========== common ==========  ==========
function generateId() {
  return crypto.randomUUID();
}

// ==========  ========== WebSocket ==========  ==========
let webSocket;
// ----------
function connectWebSocket() {
  webSocket = new WebSocket("ws://127.0.0.1:8020/ws/ext");
  // onopen
  webSocket.onopen = () => {
    console.log("WebwebSocket connected");
  };
  // onmessage
  webSocket.onmessage = (event) => {
    console.log("<=", event.data);
    // {id,command,source,params,data,error,reply}
    const req = JSON.parse(event.data);
    const origId = req.id;
    const command = req.command;
    if (!origId || !command) return;
    //
    if ("Request.Network.getResponseBody" === command) {
      if (!req.params) return;
      const tabId = req.params.tabId;
      const requestId = req.params.requestId;
      if (!tabId || !requestId) return;

      chrome.debugger.sendCommand(
        { tabId: tabId },
        "Network.getResponseBody",
        { requestId: requestId },
        (response) => {
          const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "reply": origId, "command": "Response.Network.getResponseBody" };
          if (chrome.runtime.lastError) {
            rsp.error = chrome.runtime.lastError.message;
          } else {
            rsp.data = response.body;
          }
          webSocket.send(JSON.stringify(rsp));
          console.log("=>", rsp);
        }
      );
    }
    //
    if ("Request.queryTabs" === command) {
      chrome.tabs.query(
        { currentWindow: true },
        (tabs) => {
          const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "reply": origId, "command": "Response.queryTabs" };
          rsp.data = tabs;
          webSocket.send(JSON.stringify(rsp));
          console.log("=>", rsp);
        }
      );
    }
    //
    // if ("Request.toUrl" === command) {
    //   if (!req.params) return;
    //   const tabId = req.params.tabId;
    //   const url = req.params.url;
    //   if (!tabId || !url) return;

    //   chrome.tabs.update(
    //     tabId,
    //     { url: url },
    //     (results) => {
    //       if (chrome.runtime.lastError) {
    //         console.log("=#", chrome.runtime.lastError);
    //       } else {
    //         console.log("=#", results);
    //       }
    //     }
    //   );
    // }
    //
    // if ("Request.executeScript" === command) {
    //   if (!req.params) return;
    //   const tabId = req.params.tabId;
    //   const script = req.params.script;
    //   if (!tabId || !script) return;

    //   chrome.scripting.executeScript(
    //     {
    //       target: { tabId: tabId },
    //       args: [script],
    //       func: (script) => {
    //         eval(script);
    //         return document.title;
    //       }
    //     },
    //     (results) => {
    //       if (chrome.runtime.lastError) {
    //         console.log("=#", chrome.runtime.lastError);
    //       } else {
    //         console.log("=#", results);
    //       }
    //     }
    //   );
    // }
  };

  webSocket.onclose = () => {
    console.log("WebwebSocket disconnected");
    setTimeout(connectWebSocket, 100);
  };

  webSocket.onerror = (error) => {
    console.log("WebwebSocket error:", error);
    setTimeout(connectWebSocket, 100);
  };
}
// ==========  ========== connect websocket ==========  ==========
connectWebSocket();

// ==========  ========== debugger ==========  ==========
// ----------
function handleDebuggerEvent(source, method, params) {
  // 用户输入URL、点击链接或调用 location.href 跳转
  if ("Page.frameStartedLoading" === method) {
    const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.Page.frameStartedLoading", "source": source, "params": params };
    webSocket.send(JSON.stringify(rsp));
    console.log("=>", rsp);
  }
  // 请求发起
  // if ("Network.requestWillBeSent" === method) {
  //   const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.Network.requestWillBeSent", "source": source, "params": params };
  //   webSocket.send(JSON.stringify(rsp));
  //   console.log("=>", rsp);
  // }
  // 浏览器接收到 HTTP 响应头（此时响应体可能还未开始传输）
  if ("Network.responseReceived" === method) {
    const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.Network.responseReceived", "source": source, "params": params };
    webSocket.send(JSON.stringify(rsp));
    console.log("=>", rsp);
  }
  // ********** 浏览器边下载边解析 HTML,遇到 <script>, <link>, <img> 等标签时立即发起子资源请求 **********
  // 响应体完全加载完成（包括所有数据包接收完毕）
  // if ("Network.loadingFinished" === method) {
  //   const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.Network.loadingFinished", "source": source, "params": params };
  //   webSocket.send(JSON.stringify(rsp));
  //   console.log("=>", rsp);
  // }
  // DOM加载完成。阻塞渲染的CSS和同步JS必须已完成加载和执行，非阻塞资源（如async脚本、图片）可能仍在加载
  // if ("Page.domContentEventFired" === method) {
  //   const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.Page.domContentEventFired", "source": source, "params": params };
  //   webSocket.send(JSON.stringify(rsp));
  //   console.log("=>", rsp);
  // }
  // 页面完全加载。所有同步资源必须加载完成，异步资源（如defer脚本、懒加载图片）可能仍在加载
  if ("Page.frameStoppedLoading" === method) {
    const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.Page.frameStoppedLoading", "source": source, "params": params };
    webSocket.send(JSON.stringify(rsp));
    console.log("=>", rsp);
  }
}
// ----------
async function attachDebugger(tabId) {
  try {
    // 附加调试器（协议版本 "1.3"）
    await chrome.debugger.attach({ tabId: tabId }, "1.3");
    console.log(`已附加调试器到标签页: ${tabId}`);
    // 启用网络请求监听
    await chrome.debugger.sendCommand({ tabId: tabId }, "Network.enable");
    await chrome.debugger.sendCommand({ tabId: tabId }, "Page.enable");
    // 监听调试器事件（如网络请求）
    await chrome.debugger.onEvent.addListener(handleDebuggerEvent);
  } catch (error) {
    console.log("附加调试器失败:", error);
  }
}

// ==========  ========== tabs event ==========  ==========
const debuggedTabs = new Set()
// ----------
// chrome.tabs.onCreated.addListener((tab) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.tabs.onCreated", "source": {"tabId":tab.id} };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
// });
// ----------
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'loading') {
    // console.log("标签页开始加载:", tab.url);
  }
  if (changeInfo.status === 'complete') {
    // console.log("标签页加载完成:", tab.url);
  }
  if (!debuggedTabs.has(tabId) && !tab.url.startsWith("chrome://")) {
    attachDebugger(tabId);
    debuggedTabs.add(tabId)
  }
  const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.tabs.onUpdated", "source": {"tabId":tabId}, "params":changeInfo };
  webSocket.send(JSON.stringify(rsp));
  console.log("=>", rsp);
});
// ----------
// chrome.tabs.onActivated.addListener((activeInfo) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.tabs.onActivated", "source": {"tabId":activeInfo.tabId} };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
// });
// ----------
chrome.tabs.onRemoved.addListener((tabId,removeInfo) => {
  const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.tabs.onRemoved", "source": {"tabId":tabId} };
  webSocket.send(JSON.stringify(rsp));
  console.log("=>", rsp);
  if (debuggedTabs.has(tabId)) {
    // chrome.debugger.detach({ tabId: tabId });
    debuggedTabs.delete(tabId);
  }
});

// ==========  ========== webNavigation event ==========  ==========
chrome.webNavigation.onBeforeNavigate.addListener((details) => {
    const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webNavigation.onBeforeNavigate", "params": details };
    webSocket.send(JSON.stringify(rsp));
    console.log("=>", rsp);
});
// chrome.webNavigation.onCommitted.addListener((details) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webNavigation.onCommitted", "params": details };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
// });
// chrome.webNavigation.onDOMContentLoaded.addListener((details) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webNavigation.onDOMContentLoaded", "params": details };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
// });
chrome.webNavigation.onCompleted.addListener((details) => {
    const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webNavigation.onCompleted", "params": details };
    webSocket.send(JSON.stringify(rsp));
    console.log("=>", rsp);
});
// chrome.webNavigation.onErrorOccurred.addListener((details) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webNavigation.onActivated", "params": details };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
// });

// ==========  ========== webRequest event ==========  ==========
// chrome.webRequest.onBeforeRequest.addListener((details) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webRequest.onBeforeRequest", "params": details };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
//   },{ urls: ["<all_urls>"] }
// );
// chrome.webRequest.onResponseStarted.addListener((details) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webRequest.onResponseStarted", "params": details };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
//   },{ urls: ["<all_urls>"] },["responseHeaders"]
// );
chrome.webRequest.onCompleted.addListener((details) => {
    const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webRequest.onCompleted", "params": details };
    webSocket.send(JSON.stringify(rsp));
    console.log("=>", rsp);
  },{ urls: ["<all_urls>"] },["responseHeaders"]
);
// chrome.webRequest.onErrorOccurred.addListener((details) => {
//     const rsp = { "id": generateId(), "time":new Date().toLocaleString(), "command": "Event.webRequest.onErrorOccurred", "params": details };
//     webSocket.send(JSON.stringify(rsp));
//     console.log("=>", rsp);
//   },{ urls: ["<all_urls>"] }
// );
