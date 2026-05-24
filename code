import asyncio
import aiohttp
import time
from datetime import datetime
from flask import Flask, render_template_string, request, redirect

# =========================
# CONFIG
# =========================

API_KEY = "927ebd2cc49dab33d8c8cc345c191dad"

TELEGRAM_TOKEN = "8709562564:AAG2slM8N-ogaT1D0qGKNBcukwqF3mSzvGg"
CHAT_ID = "6670231760"

REGIONS = "eu"

MIN_PROFIT = 1.0
SCAN_DELAY = 10

# LIVE EDITABLE BANKROLL
BANKROLL = 100

SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "basketball_nba",
    "tennis_atp_singles"
]

BOOKS = [
    "pinnacle",
    "betonlineag",
    "1xbet"
]

# =========================
# STORAGE
# =========================

LIVE_OPPORTUNITIES = []
SEEN_ARBS = {}

# =========================
# FLASK APP
# =========================

app = Flask(__name__)

# =========================
# HTML UI
# =========================

HTML = """

<!DOCTYPE html>
<html>

<head>

<title>INSTITUTIONAL ARB TERMINAL</title>

<meta http-equiv="refresh" content="5">

<style>

body{
    margin:0;
    background:#0b1220;
    color:white;
    font-family:Arial;
}

.header{
    background:#111827;
    padding:20px;
    text-align:center;
    font-size:28px;
    font-weight:bold;
    color:#00ff88;
    border-bottom:2px solid #00ff88;
}

.stats{
    display:flex;
    gap:20px;
    padding:20px;
    flex-wrap:wrap;
}

.stat-box{
    background:#111827;
    padding:15px;
    border-radius:12px;
    min-width:200px;
    border:1px solid #1f2937;
}

.label{
    color:#9ca3af;
    font-size:13px;
}

.value{
    font-size:24px;
    margin-top:8px;
    font-weight:bold;
    color:#00ff88;
}

.bankroll-form{
    margin-top:10px;
}

input{
    padding:10px;
    border:none;
    border-radius:8px;
    width:120px;
}

button{
    padding:10px;
    border:none;
    border-radius:8px;
    background:#00ff88;
    font-weight:bold;
    cursor:pointer;
}

.grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
    gap:15px;
    padding:20px;
}

.card{
    background:#111827;
    border-radius:12px;
    padding:15px;
    border-left:5px solid #00ff88;
}

.sport{
    color:#9ca3af;
    font-size:12px;
}

.match{
    font-size:18px;
    margin-top:6px;
    font-weight:bold;
}

.market{
    margin-top:10px;
    color:#60a5fa;
}

.profit{
    margin-top:10px;
    font-size:24px;
    font-weight:bold;
    color:#00ff88;
}

.live-time{
    margin-top:10px;
    color:#facc15;
    font-size:13px;
}

.odds{
    margin-top:10px;
    background:#0f172a;
    padding:10px;
    border-radius:8px;
    white-space:pre-wrap;
    font-size:12px;
}

</style>

</head>

<body>

<div class="header">
🚀 INSTITUTIONAL ARBITRAGE TERMINAL
</div>

<div class="stats">

<div class="stat-box">
<div class="label">LIVE BANKROLL</div>
<div class="value">${{bankroll}}</div>

<form method="POST" action="/bankroll" class="bankroll-form">

<input type="number" name="bankroll" placeholder="New bankroll">

<button type="submit">
UPDATE
</button>

</form>

</div>

<div class="stat-box">
<div class="label">LIVE OPPORTUNITIES</div>
<div class="value">{{count}}</div>
</div>

<div class="stat-box">
<div class="label">MINIMUM PROFIT</div>
<div class="value">{{min_profit}}%</div>
</div>

</div>

<div class="grid">

{% for o in data %}

<div class="card">

<div class="sport">
{{o["sport"]}}
</div>

<div class="match">
{{o["match"]}}
</div>

<div class="market">
{{o["market"]}}
</div>

<div class="profit">
+{{o["profit"]}}%
</div>

<div class="live-time">
LIVE FOR:
{{o["duration"]}}
</div>

<div class="odds">
{{o["odds"]}}
</div>

</div>

{% endfor %}

</div>

</body>
</html>

"""

# =========================
# DASHBOARD
# =========================

@app.route("/")
def home():

    global BANKROLL

    return render_template_string(
        HTML,
        data=LIVE_OPPORTUNITIES,
        bankroll=BANKROLL,
        count=len(LIVE_OPPORTUNITIES),
        min_profit=MIN_PROFIT
    )

# =========================
# LIVE BANKROLL UPDATE
# =========================

@app.route("/bankroll", methods=["POST"])
def update_bankroll():

    global BANKROLL

    try:
        BANKROLL = float(
            request.form.get("bankroll")
        )
    except:
        pass

    return redirect("/")

# =========================
# TELEGRAM ALERTS
# =========================

async def send_telegram(session, msg):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:

        await session.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg
            }
        )

    except Exception as e:

        print("TELEGRAM ERROR:", e)

# =========================
# FETCH ODDS
# =========================

async def fetch(session, sport):

    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"

    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }

    try:

        async with session.get(
            url,
            params=params
        ) as r:

            data = await r.json()

            return data if isinstance(data, list) else []

    except Exception as e:

        print("FETCH ERROR:", e)

        return []

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

            market_key = market["key"]

            if market_key not in best:
                continue

            for o in market["outcomes"]:

                name = o["name"]
                price = o["price"]

                key = f"{market_key}_{name}"

                if (
                    key not in best[market_key]
                    or price > best[market_key][key]["price"]
                ):

                    best[market_key][key] = {
                        "price": price,
                        "book": book["key"]
                    }

    return best

# =========================
# ARB CALC
# =========================

def arb_profit(outcomes):

    try:

        total = sum(
            1 / x["price"]
            for x in outcomes.values()
        )

        return (1 - total) * 100

    except:

        return -999

# =========================
# DURATION FORMATTER
# =========================

def format_duration(seconds):

    mins = int(seconds // 60)

    secs = int(seconds % 60)

    return f"{mins}m {secs}s"

# =========================
# MAIN BOT LOOP
# =========================

async def run_bot():

    async with aiohttp.ClientSession() as session:

        while True:

            for sport in SPORTS:

                events = await fetch(
                    session,
                    sport
                )

                print(
                    f"Scanning {sport} | Events: {len(events)}"
                )

                for event in events:

                    best = build_best(event)

                    for market_type, outcomes in best.items():

                        if len(outcomes) < 2:
                            continue

                        profit = arb_profit(outcomes)

                        if profit < MIN_PROFIT:
                            continue

                        arb_id = (
                            f"{event.get('id')}"
                            f"-{market_type}"
                        )

                        now = time.time()

                        if arb_id not in SEEN_ARBS:

                            SEEN_ARBS[arb_id] = now

                        duration = format_duration(
                            now - SEEN_ARBS[arb_id]
                        )

                        msg = f"""

🚨 LIVE ARBITRAGE FOUND 🚨

Sport:
{sport}

Match:
{event.get('home_team')}
vs
{event.get('away_team')}

Market:
{market_type.upper()}

Profit:
{round(profit,2)}%

Live For:
{duration}

Bankroll:
${BANKROLL}

Odds:
{outcomes}

"""

                        dashboard_data = {
                            "sport": sport,
                            "match": f"{event.get('home_team')} vs {event.get('away_team')}",
                            "market": market_type.upper(),
                            "profit": round(profit,2),
                            "duration": duration,
                            "odds": str(outcomes)
                        }

                        LIVE_OPPORTUNITIES.insert(
                            0,
                            dashboard_data
                        )

                        if len(LIVE_OPPORTUNITIES) > 50:
                            LIVE_OPPORTUNITIES.pop()

                        print(msg)

                        await send_telegram(
                            session,
                            msg
                        )

            await asyncio.sleep(SCAN_DELAY)

# =========================
# START BOT
# =========================

if __name__ == "__main__":

    asyncio.run(run_bot())
