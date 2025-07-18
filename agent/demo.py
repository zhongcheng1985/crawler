def tip(message:str):
    import tkinter as tk
    from tkinter import ttk

    win=tk.Tk()
    win.overrideredirect(True)
    win.attributes("-alpha", 0.9)
    win.attributes("-topmost", True)
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Popup.TFrame", background="#f0f0f0")
    style.configure("Popup.TLabel", background="#f0f0f0", foreground="#ff6666", font=('Arial', 30, 'bold'))
    frame = ttk.Frame(win, style="Popup.TFrame", padding=10)
    frame.pack()
    label = ttk.Label(frame, text=message, style="Popup.TLabel",wraplength=300)
    label.pack()
    win.update_idletasks()
    win.geometry(f"+{win.winfo_screenwidth()-win.winfo_width()-20}+{win.winfo_screenheight()-win.winfo_height()-50}")
    win.update()
    time.sleep(1)
    win.destroy()

# ==========  ========== main ==========  ==========
if __name__ == '__main__':
    #
    from urllib.request import Request, urlopen
    import json
    import time

    # ----------  ---------- 0. ----------  ----------
    session_id=None

    # ----------  ---------- 1. start session ----------  ----------
    tip("1. start session")
    url = 'http://127.0.0.1:8020/api/start'
    data = {}
    dataS = json.dumps(data)
    req = Request(url, data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    with urlopen(req) as response:
        print("=>"+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("<="+str(rsp))
        session_id=rsp['session_id']
    # ----------  ---------- 2. go ----------  ----------
    tip("2. go")
    url = 'http://127.0.0.1:8020/api/go'
    data = {"url":"http://127.0.0.1:8020/demo.html"}
    dataS = json.dumps(data)
    req = Request(url, data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("=>"+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("<="+str(rsp))
    # ----------  ---------- 3. input ----------  ----------
    tip("3. input")
    url = 'http://127.0.0.1:8020/api/input'
    data = {"element_id":"10_185_222_213","keys":"abcdef{tab}123456"}
    dataS = json.dumps(data)
    req = Request(url, data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("=>"+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("<="+str(rsp))
    # ----------  ---------- 4. click ----------  ----------
    tip("4. click")
    url = 'http://127.0.0.1:8020/api/click'
    data = {"element_id":"445_185_485_213"}
    dataS = json.dumps(data)
    req = Request(url, data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("=>"+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("<="+str(rsp))
    # ----------  ---------- 5. close session ----------  ----------
    tip("5. close session")
    url = 'http://127.0.0.1:8020/api/destroy'
    data = {}
    dataS = json.dumps(data)
    req = Request(url, data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("=>"+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("<="+str(rsp))
