import os, time, json, requests
from playwright.sync_api import sync_playwright

URL = os.environ["SUPA_URL"].rstrip("/") + "/rest/v1/browser_jobs"
KEY = os.environ["SUPA_KEY"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

def take():
    r = requests.get(URL, headers=H, params={"status": "eq.pending", "order": "id.asc", "limit": 1})
    d = r.json()
    return d[0] if d else None

def done(jid, res):
    requests.patch(URL, headers=H, params={"id": "eq." + str(jid)}, json={"status": "done", "result": str(res)[:6000]})

def load_state():
    r = requests.get(URL, headers=H, params={"status": "eq.state", "order": "id.desc", "limit": 1})
    d = r.json()
    return json.loads(d[0]["cmd"]) if d else None

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    st = load_state()
    if st:
        ctx.add_cookies(st["cookies"])
        for o in st.get("origins", []):
            try:
                pg.goto(o["origin"])
                for kv in o.get("localStorage", []):
                    pg.evaluate("([k,v]) => localStorage.setItem(k,v)", [kv["name"], kv["value"]])
            except Exception as e:
                print("origin 跳过", o.get("origin"), e, flush=True)
        print("登录态已加载", flush=True)
    print("cloud worker 已启动", flush=True)
    while True:
        j = take()
        if j:
            g = {"pg": pg, "ctx": ctx, "b": b}
            try:
                try:
                    res = eval(j["cmd"], g)
                except SyntaxError:
                    exec(j["cmd"], g)
                    res = g.get("R", "ok")
                if res is None:
                    res = "ok"
            except Exception as e:
                res = "错误: " + str(e)
            done(j["id"], res)
            print("完成:", j["id"], str(res)[:200], flush=True)
        time.sleep(4)
