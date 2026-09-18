import os, json, time, traceback, requests
from playwright.sync_api import sync_playwright

SUPA_URL = os.environ["SUPA_URL"].rstrip("/")
SUPA_KEY = os.environ["SUPA_KEY"]
HEAD = {
    "apikey": SUPA_KEY,
    "Authorization": "Bearer " + SUPA_KEY,
    "Content-Type": "application/json",
}

ONESHOT = os.environ.get("ONESHOT", "") == "1"
HEADLESS = ONESHOT or os.environ.get("HEADLESS", "") == "1"

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--renderer-process-limit=1",
    "--js-flags=--max-old-space-size=256",
    "--autoplay-policy=user-gesture-required",
    "--mute-audio",
    "--window-size=960,540",
]

def fetch_job():
    r = requests.get(SUPA_URL + "/rest/v1/browser_jobs", headers=HEAD,
        params={"status": "eq.pending", "order": "id.asc", "limit": "1"}, timeout=30)
    rows = r.json()
    return rows[0] if rows else None

def write_back(job_id, data):
    requests.patch(SUPA_URL + "/rest/v1/browser_jobs", headers=HEAD,
        params={"id": "eq." + str(job_id)}, json=data, timeout=30)

def fetch_state():
    r = requests.get(SUPA_URL + "/rest/v1/browser_jobs", headers=HEAD,
        params={"status": "eq.state", "order": "id.desc", "limit": "1"}, timeout=30)
    rows = r.json()
    return rows[0]["cmd"] if rows else None

def restore_state(ctx, state_json):
    st = json.loads(state_json)
    try:
        ctx.add_cookies(st.get("cookies", []))
    except Exception as e:
        print("cookies failed:", e)
    for origin in st.get("origins", []):
        try:
            page = ctx.new_page()
            page.goto(origin["origin"], timeout=60000)
            for kv in origin.get("localStorage", []):
                page.evaluate("([k, v]) => localStorage.setItem(k, v)",
                              [kv["name"], kv["value"]])
            page.close()
        except Exception as e:
            print("origin failed:", origin.get("origin"), e)

def main():
    state_json = fetch_state()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=CHROME_ARGS)
        ctx = browser.new_context(viewport={"width": 960, "height": 540})
        if state_json:
            restore_state(ctx, state_json)

        pg = ctx.new_page()
        pg.set_default_timeout(30000)

        while True:
            try:
                if pg.is_closed():
                    print("page crashed, reopening")
                    pg = ctx.new_page()
                    pg.set_default_timeout(30000)

                job = fetch_job()
                if not job:
                    if ONESHOT:
                        print("no pending job")
                        break
                    time.sleep(2)
                    continue

                try:
                    exec(job["cmd"], {"pg": pg, "ctx": ctx, "browser": browser})
                    write_back(job["id"], {"status": "done", "result": "ok"})
                except Exception:
                    write_back(job["id"], {"status": "done",
                                           "result": traceback.format_exc()})

                if ONESHOT:
                    break

            except Exception as e:
                print("loop error:", e)
                if ONESHOT:
                    break
                time.sleep(5)

        browser.close()

if __name__ == "__main__":
    main()
