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

def find_element_by_id(obj, target_id):
    if not isinstance(obj, dict):
        return None
    if obj.get('element_id') == target_id:
        return obj
    children = obj.get('children', [])
    for child in children:
        result = find_element_by_id(child, target_id)
        if result is not None:
            return result
    return None

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
    # ----------  ---------- 2. go ----------  ----------
    tip("2. go")
    data = {"url":"https://radar.cloudflare.com/domains"}
    dataS = json.dumps(data)
    req = Request('http://104.238.234.115:8000/api/go', data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("go => "+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("go <= "+str(rsp))

    # ----------  ---------- 3. view & 4. click ----------  ----------
    domains=[]
    if rsp.get('title')!=None:
        for i in range(10):
            #
            tip("3. view")
            data = {}
            dataS = json.dumps(data)
            req = Request('http://104.238.234.115:8000/api/view', data=dataS.encode('utf-8'), method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('x-session-id', session_id)
            with urlopen(req) as response:
                print("view => "+str(dataS))
                rsp = json.loads(response.read().decode('utf-8'))
                #
                table = find_element_by_id(rsp.get("elements"),"309_360_1057_819")
                for c in table.get("children")[0].get("children")[1:]:
                    print("["+c.get("children")[1].get("name")+"]")
                    domains.append(c.get("children")[1].get("name"))

                #print("view <= "+str(rsp))
            #
            tip("4. click")
            data = {"element_id":"359_850_397_889"}
            dataS = json.dumps(data)
            req = Request('http://104.238.234.115:8000/api/click', data=dataS.encode('utf-8'), method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('x-session-id', session_id)
            with urlopen(req) as response:
                print("click => "+str(dataS))
                rsp = json.loads(response.read().decode('utf-8'))
                print("click <= "+str(rsp))

    # ----------  ---------- 5. check ----------  ----------
    for d in domains:
        tip("5. check")
        data = {"url":d}
        dataS = json.dumps(data)
        req = Request('http://104.238.234.115:8000/api/go', data=dataS.encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('x-session-id', session_id)
        with urlopen(req) as response:
            print("go => "+str(dataS))
            rsp = json.loads(response.read().decode('utf-8'))
            print("go <= "+str(rsp))

    # ----------  ---------- 6. close session ----------  ----------
    tip("6. close session")
    data = {}
    dataS = json.dumps(data)
    req = Request('http://104.238.234.115:8000/api/destroy', data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("close => "+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("close <= "+str(rsp))
