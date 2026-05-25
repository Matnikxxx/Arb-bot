import asyncio
import aiohttp
import time
from datetime import datetime, timezone
from flask import Flask, render_template_string
import threading

# =========================
# CONFIG
# =========================

API_KEY = "927ebd2cc49dab33d8c8cc345c191dad"
TELEGRAM_TOKEN = "8709562564:AAG2slM8N-ogaT1D0qGKNBcukwqF3mSzvGg"
CHAT_ID = "6670231760"

REGIONS = "eu"
MIN_PROFIT = 1.0
SCAN_DELAY = 10

BANKROLL = 100

SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "basketball_nba",
    "tennis_atp_singles"
]

BOOKS = ["pinnacle", "betonlineag", "1xbet"]

# =========================
# STORAGE
# =========================

LIVE_OPPORTUNITIES = []
SEEN_ARBS = {}

# =========================
# FLASK APP
# =========================

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>PRE-GAME ARB DASHBOARD</title>
<meta http-equiv="refresh" content="5">

<style>
body { font-family: Arial; background:#0b1220; color:white; margin:0; }
.header { padding:15px; background:#111827; color:#00ff88; font-size:22px; text-align:center; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:15px; padding:15px; }
.card { background:#111827; padding:15px; border-left:4px solid #00ff88; border-radius:10px; }
.sport { font-size:12px; color:#9ca3af; }
.match { font-size:16px; font-weight:bold; }
.profit { color:#00ff88; font-size:20px; margin-top:10px; }
.time { color:#facc15; font-size:13px; margin-top:5px; }
.odds { font-size:12px; background:#0f172a; padding:10px; margin-top:10px; white-space:pre-wrap; }
</style>

</head>

<body>

<div class="header">🚀 PRE-GAME ARBITRAGE SYSTEM</div>

<div class="grid">

{% for o in data %}
<div class="card">
<div class="sport">{{o["sport"]}}</div>
<div class="match">{{o["match"]}}</div>
<div class="profit">+{{o["profit"]}}%</div>
<div class="time">LIVE FOR: {{o["duration"]}}</div>
<div class="odds">{{o["odds"]}}</div>
</div>
{% endfor %}

</div>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML, data=LIVE_OPPORTUNITIES)

# =========================
# TELEGRAM
# =========================

async def send_telegram(session, msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    await session.post(url, data={"chat_id": CHAT_ID, "text": str(msg)})

# =========================
# FETCH ODDS
# =========================

async def fetch(session, sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    try:
        async with session.get(url, params=params) as r:
            data = await r.json()
            return data if isinstance(data, list) else []
    except:
        return []

# =========================
# PRE-GAME FILTER (IMPORTANT)
# =========================

def is_pregame(event):
    try:
        return event.get("commence_time") and datetime.fromisoformat(
            event["commence_time"].replace("Z", "+00:00")
        ) > datetime.now(timezone.utc)
    except:
        return False

# =========================
# BUILD BEST ODDS
# =========================

def build_best(event):
    best = {
        "h2h": {},
        "spreads": {},
        "totals": {}
    }

    for book in event.get("bookmakers", []):

        if book["key"] not in BOOKS:
            continue

        for market in book.get("markets", []):

            mkey = market["key"]

            if mkey not in best:
                continue

            for o in market["outcomes"]:
                name = o["name"]
                price = o["price"]

                key = f"{mkey}_{name}"

                if key not in best[mkey] or price > best[mkey][key]["price"]:
                    best[mkey][key] = {
                        "price": price,
                        "book": book["key"]
                    }

    return best

# =========================
# ARB CALC
# =========================

def arb_profit(outcomes):
    try:
        total = sum(1 / x["price"] for x in outcomes.values())
        return (1 - total) * 100
    except:
        return -999

# =========================
# DURATION
# =========================

def get_duration(start_time):
    return f"{int(time.time() - start_time)}s"

# =========================
# BOT LOOP
# =========================

async def run_bot():

    async with aiohttp.ClientSession() as session:

        while True:

            for sport in SPORTS:

                events = await fetch(session, sport)

                print(f"{sport} | events: {len(events)}")

                for event in events:

                    # 🚨 PRE-GAME ONLY FILTER
                    if not is_pregame(event):
                        continue

                    best = build_best(event)

                    for market_type, outcomes in best.items():

                        if len(outcomes) < 2:
                            continue

                        profit = arb_profit(outcomes)

                        if profit < MIN_PROFIT:
                            continue

                        arb_id = f"{event.get('id')}-{market_type}"

                        now = time.time()

                        if arb_id not in SEEN_ARBS:
                            SEEN_ARBS[arb_id] = now

                        duration = get_duration(SEEN_ARBS[arb_id])

                        msg = f"""
🚨 PRE-GAME ARB FOUND 🚨

Sport: {sport}
Match: {event.get('home_team')} vs {event.get('away_team')}
Market: {market_type.upper()}

Profit: {round(profit,2)}%
Live For: {duration}

Bankroll: ${BANKROLL}

Odds:
{outcomes}
"""

                        dashboard_item = {
                            "sport": sport,
                            "match": f"{event.get('home_team')} vs {event.get('away_team')}",
                            "profit": round(profit,2),
                            "duration": duration,
                            "odds": str(outcomes)
                        }

                        LIVE_OPPORTUNITIES.insert(0, dashboard_item)

                        if len(LIVE_OPPORTUNITIES) > 50:
                            LIVE_OPPORTUNITIES.pop()

                        print(msg)

                        await send_telegram(session, msg)

            await asyncio.sleep(SCAN_DELAY)

# =========================
# START
# =========================
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
