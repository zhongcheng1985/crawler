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
    data = {}
    dataS = json.dumps(data)
    req = Request('http://104.238.234.115:8000/api/start', data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    with urlopen(req) as response:
        print("start => "+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("start <= "+str(rsp))
        session_id=rsp['session_id']

    req = Request('http://104.238.234.115:8000/api/maximize', data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("maximize => "+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("maximize <= "+str(rsp))

    # ----------  ---------- 2. go ----------  ----------
    urls=[
        "thruwaynissan.com", 
        "motorwerkshonda.com", 
        "capitalfordrockymount.com",
        "cityautotrucks.com",
        "kirklandhonda.com", 
        "1autoliquidators.com", 
        "0to60motorsportsct.com", 
        "039autosale.com", 
        "1autodmv.com", 
        "1oakautos.com", 
        "1ownerautosales.net", 
        "my1stopauto.com", 
        "1800autoapproved.com", 
        "1easyrideautosale.com",
        "1uniquemotorsllc.com",
    ]
    tip("2. go")
    for url in urls:
        data = {"url":url}
        dataS = json.dumps(data)
        req = Request('http://104.238.234.115:8000/api/go', data=dataS.encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('x-session-id', session_id)
        with urlopen(req) as response:
            print("go => "+str(dataS))
            rsp = json.loads(response.read().decode('utf-8'))
            if rsp.get('title')!=None:
                print(f"websites [{rsp.get('url')}] alive")
            print("go <= "+str(rsp))

    # ----------  ---------- 3. close session ----------  ----------
    tip("3. close session")
    data = {}
    dataS = json.dumps(data)
    req = Request('http://104.238.234.115:8000/api/destroy', data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("close => "+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("close <= "+str(rsp))
