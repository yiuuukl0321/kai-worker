import os, time, requests
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

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = b.new_context()
    pg = ctx.new_page()
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
