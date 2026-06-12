"""
fetch_data.py - Fetches market data from NSE India, Yahoo Finance, and news sources.
Saves to data/market_data.json for PDF generation.
"""
import json
import os
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

try:
    import yfinance as yf
except ImportError:
    yf = None

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "Output")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "application/json, text/plain, */*",
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 3


def retry_request(func, *args, retries=MAX_RETRIES, delay=RETRY_DELAY, **kwargs):
    """Generic retry wrapper for requests."""
    for attempt in range(retries):
        try:
            result = func(*args, **kwargs)
            return result
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif attempt < retries - 1:
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise
    return None


def get_nse_session():
    """Create a requests session with NSE cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        resp = session.get("https://www.nseindia.com", timeout=15)
        if resp.status_code == 200:
            return session
    except Exception as e:
        print(f"Warning: Could not get NSE session: {e}")
    return session


def fetch_nse_index(session, symbol="NIFTY 50"):
    """Fetch NSE index data with retries."""
    url = f"https://www.nseindia.com/api/equity-stockIndices?index={symbol.replace(' ', '%20')}"
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and len(data["data"]) > 0:
                    meta = data.get("metadata", {})
                    return {
                        "name": symbol,
                        "last": meta.get("last", 0),
                        "change": meta.get("change", 0),
                        "pChange": meta.get("pChange", 0),
                        "open": meta.get("open", 0),
                        "high": meta.get("high", 0),
                        "low": meta.get("low", 0),
                        "previousClose": meta.get("previousClose", 0),
                    }
            elif resp.status_code == 429:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"  Rate limited on {symbol}, waiting {wait}s...")
                time.sleep(wait)
                continue
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for {symbol}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    print(f"Warning: Could not fetch NSE index {symbol} after {MAX_RETRIES} attempts")
    return None


def fetch_nse_vix(session):
    """Fetch India VIX with retries."""
    url = "https://www.nseindia.com/api/allIndices"
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for idx in data.get("data", []):
                    if idx.get("index") == "INDIA VIX":
                        return {
                            "last": idx.get("last", 0),
                            "change": idx.get("change", 0),
                            "pChange": idx.get("pChange", 0),
                            "open": idx.get("open", 0),
                            "high": idx.get("high", 0),
                            "low": idx.get("low", 0),
                        }
            elif resp.status_code == 429:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"  Rate limited on VIX, waiting {wait}s...")
                time.sleep(wait)
                continue
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for VIX: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    print("Warning: Could not fetch VIX after retries")
    return None


def fetch_fii_dii(session):
    """Fetch FII/DII cash market data with retries."""
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                result = {}
                for item in data:
                    category = item.get("category", "")
                    if "FII" in category or "FPI" in category:
                        result["fii_cash"] = item.get("net", "0")
                    elif "DII" in category:
                        result["dii_cash"] = item.get("net", "0")
                return result
            elif resp.status_code == 429:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"  Rate limited on FII/DII, waiting {wait}s...")
                time.sleep(wait)
                continue
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for FII/DII: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    print("Warning: Could not fetch FII/DII after retries")
    return {}


def fetch_gift_nifty():
    """Fetch Gift Nifty from multiple sources."""
    # Source 1: Moneycontrol
    try:
        url = "https://www.moneycontrol.com/markets/futures-fno/gift-nifty/2351907"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            price_elem = soup.find("span", {"class": "amount"})
            if price_elem:
                price = float(price_elem.text.replace(",", "").strip())
                return {"last": price, "source": "Moneycontrol"}
    except Exception as e:
        print(f"  Gift Nifty (Moneycontrol): {e}")

    # Source 2: Investing.com
    try:
        url = "https://www.investing.com/indices/sgx-nifty"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            price_elem = soup.find("span", {"data-test": "textLastPrice"})
            if price_elem:
                price = float(price_elem.text.replace(",", "").strip())
                return {"last": price, "source": "Investing.com"}
    except Exception as e:
        print(f"  Gift Nifty (Investing.com): {e}")

    return None


def fetch_us_markets():
    """Fetch US market data via yfinance."""
    if yf is None:
        print("Warning: yfinance not installed, skipping US market data")
        return {}

    tickers = {
        "spx": "^GSPC",
        "dow": "^DJI",
        "nasdaq": "^IXIC",
        "russell": "^RUT",
    }
    results = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if not hist.empty and len(hist) >= 2:
                last = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                change_pct = ((last - prev) / prev) * 100
                results[name] = {
                    "last": round(last, 2),
                    "change_pct": round(change_pct, 2),
                    "change_pts": round(last - prev, 2),
                }
        except Exception as e:
            print(f"Warning: Could not fetch {name}: {e}")
        time.sleep(1)
    return results


def fetch_commodities_fx():
    """Fetch commodities and FX via yfinance."""
    if yf is None:
        return {}

    tickers = {
        "crude_wti": "CL=F",
        "brent": "BZ=F",
        "gold": "GC=F",
        "silver": "SI=F",
        "usdinr": "USDINR=X",
        "us10y": "^TNX",
    }
    results = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if not hist.empty and len(hist) >= 2:
                last = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                change_pct = ((last - prev) / prev) * 100
                results[name] = {
                    "last": round(last, 2),
                    "change_pct": round(change_pct, 2),
                }
        except Exception as e:
            print(f"Warning: Could not fetch {name}: {e}")
        time.sleep(1)
    return results


def fetch_news_headlines():
    """Fetch top financial news headlines from multiple sources."""
    headlines = []

    # Source 1: Google News RSS for Indian markets
    try:
        url = "https://news.google.com/rss/search?q=Indian+stock+market+Nifty+Bank+Nifty+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:7]:
                title = item.find("title")
                link = item.find("link")
                if title is not None and title.text:
                    headlines.append({
                        "source": "Google News",
                        "headline": title.text.strip()[:150],
                        "url": link.text.strip() if link is not None else "",
                    })
    except Exception as e:
        print(f"  Google News RSS: {e}")

    # Source 2: Moneycontrol market news
    try:
        url = "https://www.moneycontrol.com/markets/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            # Try multiple selector patterns
            items = (
                soup.find_all("li", class_="clearfix", limit=5) or
                soup.find_all("div", class_="news", limit=5) or
                soup.find_all("a", class_="linktitle", limit=5)
            )
            for item in items:
                link = item.find("a") if item.name != "a" else item
                if link and link.text.strip() and len(link.text.strip()) > 10:
                    headlines.append({
                        "source": "Moneycontrol",
                        "headline": link.text.strip()[:150],
                        "url": link.get("href", ""),
                    })
    except Exception as e:
        print(f"  Moneycontrol news: {e}")

    # Source 3: Economic Times market news
    try:
        url = "https://economictimes.indiatimes.com/markets"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            # Try multiple selector patterns
            items = (
                soup.find_all("div", class_="eachStory", limit=5) or
                soup.find_all("div", class_="story", limit=5) or
                soup.find_all("a", class_="title", limit=5)
            )
            for item in items:
                link = item.find("a") if item.name != "a" else item
                if link and link.text.strip() and len(link.text.strip()) > 10:
                    headlines.append({
                        "source": "Economic Times",
                        "headline": link.text.strip()[:150],
                        "url": link.get("href", ""),
                    })
    except Exception as e:
        print(f"  ET news: {e}")

    # Source 4: Livemint market news
    try:
        url = "https://www.livemint.com/market"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.find_all("a", class_="headline", limit=5)
            for item in items:
                if item.text.strip() and len(item.text.strip()) > 10:
                    headlines.append({
                        "source": "Livemint",
                        "headline": item.text.strip()[:150],
                        "url": item.get("href", ""),
                    })
    except Exception as e:
        print(f"  Livemint news: {e}")

    # Deduplicate by headline text
    seen = set()
    unique_headlines = []
    for h in headlines:
        key = h["headline"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique_headlines.append(h)

    return unique_headlines[:10]


def fetch_all(run_type="close"):
    """
    Fetch all market data.
    run_type: 'close' (0:00 IST), 'premarket' (6:00 IST), 'open' (9:00 IST)
    """
    print(f"Fetching data for run type: {run_type}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    data = {
        "run_type": run_type,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%d %b %Y"),
    }

    # NSE session
    print("Creating NSE session...")
    session = get_nse_session()
    time.sleep(2)

    # Nifty 50
    print("Fetching Nifty 50...")
    nifty = fetch_nse_index(session, "NIFTY 50")
    if nifty:
        data["nifty50"] = nifty
    time.sleep(3)

    # Bank Nifty
    print("Fetching Bank Nifty...")
    banknifty = fetch_nse_index(session, "NIFTY BANK")
    if banknifty:
        data["banknifty"] = banknifty
    time.sleep(3)

    # India VIX
    print("Fetching India VIX...")
    vix = fetch_nse_vix(session)
    if vix:
        data["india_vix"] = vix
    time.sleep(3)

    # FII/DII
    print("Fetching FII/DII data...")
    fii_dii = fetch_fii_dii(session)
    if fii_dii:
        data["fii_dii"] = fii_dii

    # Gift Nifty (mainly for pre-market run)
    if run_type in ("premarket", "open"):
        print("Fetching Gift Nifty...")
        gift = fetch_gift_nifty()
        if gift:
            data["gift_nifty"] = gift
        time.sleep(2)

    # US markets
    print("Fetching US markets...")
    us = fetch_us_markets()
    if us:
        data["us_markets"] = us

    # Commodities and FX
    print("Fetching commodities and FX...")
    commodities = fetch_commodities_fx()
    if commodities:
        data["commodities"] = commodities

    # News
    print("Fetching news headlines...")
    news = fetch_news_headlines()
    data["news"] = news
    print(f"  Fetched {len(news)} headlines")

    # Save
    output_path = os.path.join(DATA_DIR, "market_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Data saved to {output_path}")
    return data


if __name__ == "__main__":
    import sys

    run_type = sys.argv[1] if len(sys.argv) > 1 else "close"
    fetch_all(run_type)
