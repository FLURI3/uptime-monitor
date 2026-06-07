import asyncio
import time
import aiosqlite
import aiohttp
import smtplib
import yaml
import json
from email.message import EmailMessage
from typing import Dict, Any

CONFIG_PATH = "config.yaml"
DB_PATH = "monitor.db"

class Notifier:
    def __init__(self, cfg):
        self.cfg = cfg

    async def send_telegram(self, text: str):
        tcfg = self.cfg.get("telegram", {})
        if not tcfg.get("enabled"): return
        token = tcfg["bot_token"]
        chat_id = tcfg["chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)

    async def notify(self, title: str, text: str):
        await self.send_telegram(f"🔔 {title}\n{text}")

class Monitor:
    def __init__(self, cfg):
        self.cfg = cfg
        self.interval = cfg.get("interval", 30)
        self.notifier = Notifier(cfg.get("notify", {}))
        self._running = True

    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER,
                status INTEGER,
                rtt_ms INTEGER,
                timestamp INTEGER
            )""")
            await db.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                url TEXT,
                timeout INTEGER
            )""")
            await db.execute("""
            CREATE TABLE IF NOT EXISTS site_state (
                site_id INTEGER PRIMARY KEY,
                last_status INTEGER,
                last_ts INTEGER
            )""")
            await db.commit()

    async def get_sites(self):
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await db.execute_fetchall("SELECT id, name, url, timeout FROM sites")
            return [{"id": r[0], "name": r[1], "url": r[2], "timeout": r[3]} for r in rows]

    async def record(self, site_id, status, rtt):
        ts = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO checks (site_id, status, rtt_ms, timestamp) VALUES (?, ?, ?, ?)",
                             (site_id, status, rtt, ts))
            await db.execute(
                "INSERT OR REPLACE INTO site_state (site_id, last_status, last_ts) VALUES (?, ?, ?)",
                (site_id, status, ts))
            await db.commit()

    async def get_last_status(self, site_id):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT last_status FROM site_state WHERE site_id = ?", (site_id,))
            row = await cur.fetchone()
            return row[0] if row else None

    async def check_site(self, session, site):
        url = site["url"]
        timeout = site["timeout"] or 10
        name = site["name"]
        sid = site["id"]
        start = time.time()
        try:
            async with session.get(url, timeout=timeout) as resp:
                status = resp.status
                rtt = int((time.time() - start) * 1000)
        except:
            status, rtt = 0, -1
        last = await self.get_last_status(sid)
        await self.record(sid, status, rtt)
        if last is not None:
            was_down = last == 0 or last >= 500
            is_down = status == 0 or status >= 500
            if was_down != is_down:
                state = "ONLINE" if not is_down else "OFFLINE"
                await self.notifier.notify(f"{name} {state}", f"{url} -> {status} ({rtt}ms)")

    async def worker(self):
        await self.init_db()
        async with aiohttp.ClientSession() as session:
            while self._running:
                sites = await self.get_sites()
                if not sites:
                    print("No sites configured.")
                    await asyncio.sleep(10)
                    continue
                await asyncio.gather(*(self.check_site(session, s) for s in sites))
                await asyncio.sleep(self.interval)

async def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    mon = Monitor(cfg)
    await mon.worker()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
