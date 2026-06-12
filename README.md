# Nifty F&O Analysis Bot

Automated daily F&O trading analysis for Indian markets (Nifty 50, Bank Nifty).

## What It Does

Fetches live market data from NSE India and Yahoo Finance, scores 13 indicator categories using the F&O India Trading Skill framework, and generates a PDF report.

## Schedule (IST)

| Time | Run Type | Description |
|------|----------|-------------|
| 00:00 | Close | Previous day closing summary |
| 06:00 | Pre-market | Gift Nifty + global cues |
| 09:00 | Open | Market open snapshot |

## Setup

### GitHub Actions (automated)

1. Fork or clone this repo
2. Enable GitHub Actions
3. (Optional) Set up Google Drive upload:
   - Create a Google Cloud project with Drive API enabled
   - Create a Service Account, download JSON key
   - Base64 encode: `cat key.json | base64`
   - Add GitHub secrets:
     - `GDRIVE_CREDENTIALS` = base64 encoded service account JSON
     - `GDRIVE_FOLDER_ID` = your Drive folder ID
   - Share the Drive folder with the service account email

### Local Run

```bash
pip install -r requirements.txt
python run_analysis.py close    # or premarket, open
```

## Data Sources

- **NSE India**: Nifty 50, Bank Nifty, VIX, FII/DII flows
- **Yahoo Finance**: US markets (S&P, Dow, Nasdaq), crude oil, gold, USD/INR, US 10Y yield
- **News scraping**: Moneycontrol, Economic Times headlines

## Scoring Framework

13 categories scored -1 to +1:
- **Quantitative (60%)**: Global sentiment, India market, derivatives, currency/commodities, technicals, breadth
- **Qualitative (40%)**: Macro policy, corporate events, calendar, geopolitical, sector catalysts, regulatory, news sentiment

## Output

PDF saved to `Output/Nifty_Analysis_DDMMMYYYY.pdf`

## Limitations

- Derivatives scoring (Category C) requires live option chain data - defaults to neutral
- News sentiment is keyword-based, not AI-powered
- NSE API may rate-limit or block requests
