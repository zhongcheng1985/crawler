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

def extract_hyperlinks(elements, url):
    """Extract all hyperlink URLs from element tree"""
    from urllib.parse import urlparse, urljoin
    
    if not elements:
        print(f"No elements found for {url}")
        return []
    
    # Parse the base URL to get schema and host
    base_parsed = urlparse(url)
    base_scheme = base_parsed.scheme
    base_host = base_parsed.netloc
    
    all_urls = []
    
    # Convert to list if it's a single dict
    if isinstance(elements, dict):
        elements = [elements]
    
    # Process all elements in the tree
    element_stack = elements.copy()
    
    while element_stack:
        element = element_stack.pop()
        
        if not isinstance(element, dict):
            continue
        
        # Check if current element is a hyperlink
        if element.get('control_type') == 'HyperlinkControl':
            value = element.get('value', '')
            if value:
                # Process the hyperlink name as URL
                if value.startswith(('http://', 'https://')):
                    # Absolute URL - check if same domain
                    url_parsed = urlparse(value)
                    if url_parsed.netloc == base_host:
                        all_urls.append(value)
                elif value.startswith('/'):
                    # Relative URL - construct full URL
                    full_url = f"{base_scheme}://{base_host}{value}"
                    all_urls.append(full_url)
                elif value.startswith('#'):
                    # Anchor link - skip
                    pass
                elif ':' in value:
                    # Other protocols - skip
                    pass
                else:
                    # Try to construct URL from relative path or text
                    try:
                        full_url = urljoin(f"{base_scheme}://{base_host}/", value)
                        url_parsed = urlparse(full_url)
                        if url_parsed.netloc == base_host:
                            all_urls.append(full_url)
                    except:
                        pass
        
        # Add children to stack for processing
        children = element.get('children', [])
        if children:
            element_stack.extend(children)
    
    return all_urls

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
    req = Request('http://127.0.0.1:8020/api/start', data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    with urlopen(req) as response:
        print("start => "+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("start <= "+str(rsp))
        session_id=rsp['session_id']
    # ----------  ---------- 2. go ----------  ----------
    # urls=[
    #     "https://www.thruwaynissan.com",
    #     "https://www.motorwerkshonda.com", 
    #     "https://www.capitalfordrockymount.com",
    #     "https://www.cityautotrucks.com",
    #     "https://www.kirklandhonda.com",
    #     "https://www.1autoliquidators.com",
    #     "https://www.0to60motorsportsct.com",
    #     "https://www.039autosale.com",
    #     "https://www.1autodmv.com",
    #     "https://www.1oakautos.com",
    #     "https://www.1ownerautosales.net",
    #     "https://www.my1stopauto.com",
    #     "https://www.1800autoapproved.com",
    #     "https://www.1easyrideautosale.com",
    #     "https://www.1uniquemotorsllc.com"
    # ]

    urls=["http://127.0.0.1:8020/demo.html"]

    # ----------  ---------- 3. view ----------  ----------
    for url in urls:
        to_visit = [url]  # Queue of URLs to visit
        all_found_urls = [url]  # Collect all found URLs (including visited ones)
        
        while to_visit:
            current_url = to_visit.pop(0)  # Get URL from front of queue
            
            # Visit the page
            tip("2. go")
            data = {"url": current_url}
            dataS = json.dumps(data)
            req = Request('http://127.0.0.1:8020/api/go', data=dataS.encode('utf-8'), method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('x-session-id', session_id)
            with urlopen(req) as response:
                print("go => "+str(dataS))
                rsp = json.loads(response.read().decode('utf-8'))
                print("go <= "+str(rsp))

            # Get page elements and extract hyperlinks
            tip("3. view")
            data = {}
            dataS = json.dumps(data)
            req = Request('http://127.0.0.1:8020/api/view', data=dataS.encode('utf-8'), method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('x-session-id', session_id)
            with urlopen(req) as response:
                print("view => "+str(dataS))
                rsp = json.loads(response.read().decode('utf-8'))
                
                if 'elements' in rsp:
                    elements = rsp['elements']
                    found_hyperlinks = extract_hyperlinks(elements, current_url)
                    
                    # Add newly found URLs to the visit queue
                    for new_url in found_hyperlinks:
                        if new_url not in all_found_urls and new_url not in to_visit:
                            to_visit.append(new_url)
                            all_found_urls.append(new_url)
                else:
                    print(f"No elements found for {current_url}")
                
                print("view <= "+str(rsp))
        
        print(f"URLs for {url} == {all_found_urls}")

    # ----------  ---------- 4. close session ----------  ----------
    tip("4. close session")
    data = {}
    dataS = json.dumps(data)
    req = Request('http://127.0.0.1:8020/api/destroy', data=dataS.encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-session-id', session_id)
    with urlopen(req) as response:
        print("close => "+str(dataS))
        rsp = json.loads(response.read().decode('utf-8'))
        print("close <= "+str(rsp))
