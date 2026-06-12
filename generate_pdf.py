"""
generate_pdf.py - Generates F&O analysis PDF from market data.
Reads data/market_data.json and outputs to Output/Nifty_Analysis_DDMMMYYYY.pdf
"""
import json
import os
from datetime import datetime
from fpdf import FPDF

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "Output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Scoring thresholds
SCORE_RANGES = {
    "EXTREME_BULLISH": (0.80, 1.00),
    "MODERATE_BULLISH": (0.50, 0.80),
    "MILD_BULLISH": (0.20, 0.50),
    "NEUTRAL": (-0.20, 0.20),
    "MILD_BEARISH": (-0.50, -0.20),
    "MODERATE_BEARISH": (-0.80, -0.50),
    "EXTREME_BEARISH": (-1.00, -0.80),
}


class AnalysisPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Nifty F&O Analysis | Automated Report", 0, 0, "L")
        self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, "R")
        self.line(10, 15, 200, 15)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        self.line(10, 280, 200, 280)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | DISCLAIMER: F&O trading carries substantial risk.", 0, 0, "C")

    def section_title(self, title, color=(20, 60, 140)):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*color)
        self.cell(0, 8, title, 0, 1, "L")
        self.set_draw_color(*color)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def sub_title(self, title, color=(40, 40, 40)):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*color)
        self.cell(0, 6, title, 0, 1, "L")
        self.ln(1)

    def body_text(self, text, size=8):
        self.set_font("Helvetica", "", size)
        self.set_text_color(30, 30, 30)
        self.set_x(10)
        self.multi_cell(0, 4, text)
        self.ln(1)

    def bold_text(self, text, size=8):
        self.set_font("Helvetica", "B", size)
        self.set_text_color(30, 30, 30)
        self.set_x(10)
        self.multi_cell(0, 4, text)
        self.ln(0.5)

    def colored_box(self, label, value, color, w=90):
        x = self.get_x()
        y = self.get_y()
        self.set_fill_color(*color)
        self.set_draw_color(*[min(c + 30, 255) for c in color])
        self.rect(x, y, w, 6, "DF")
        self.set_xy(x + 1, y + 0.5)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(255, 255, 255)
        self.cell(35, 5, label, 0, 0)
        self.set_font("Courier", "", 7)
        self.cell(w - 37, 5, value, 0, 1, "R")
        self.ln(1)

    def data_table(self, headers, rows, col_widths=None):
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(20, 60, 140)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 5, h, 1, 0, "C", 1)
        self.ln()
        self.set_font("Helvetica", "", 7)
        self.set_text_color(30, 30, 30)
        fill = False
        for row in rows:
            if fill:
                self.set_fill_color(240, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 5, str(cell), 1, 0, "C", 1)
            self.ln()
            fill = not fill
        self.ln(2)

    def score_bar(self, label, score, w=150):
        self.set_font("Helvetica", "", 7)
        self.set_text_color(30, 30, 30)
        self.set_x(10)
        self.cell(45, 5, label, 0, 0)
        x = self.get_x()
        y = self.get_y()
        self.set_draw_color(200, 200, 200)
        self.rect(x, y + 1, w, 3)
        norm_score = (score + 1) / 2
        fill_w = norm_score * w
        if score > 0.2:
            self.set_fill_color(0, 180, 80)
        elif score < -0.2:
            self.set_fill_color(220, 50, 50)
        else:
            self.set_fill_color(240, 180, 30)
        self.rect(x, y + 1, max(fill_w, 0), 3, "F")
        self.set_xy(x + w + 1, y)
        self.set_font("Courier", "B", 7)
        self.cell(20, 5, f"{score:+.2f}", 0, 1)
        self.ln(0.5)


def get_signal(score):
    for signal, (low, high) in SCORE_RANGES.items():
        if low <= score <= high:
            return signal
    return "NEUTRAL"


def score_global_sentiment(data):
    """Category A: Global Market Sentiment (18% weight)"""
    us = data.get("us_markets", {})
    score = 0
    count = 0

    for key in ["spx", "dow", "nasdaq"]:
        if key in us:
            pct = us[key].get("change_pct", 0)
            if pct > 1:
                s = 1.0
            elif pct > 0.3:
                s = 0.5
            elif pct > -0.3:
                s = 0
            elif pct > -1:
                s = -0.5
            else:
                s = -1.0
            score += s
            count += 1

    # Momentum modifier for US (3+ consecutive)
    # Simplified: if all positive, add bonus
    if count > 0 and all(us.get(k, {}).get("change_pct", 0) > 0 for k in ["spx", "dow", "nasdaq"]):
        score += 0.25

    return round(min(max(score / max(count, 1), -1), 1), 2) if count > 0 else 0


def score_india_market(data):
    """Category B: India-Specific Market Data (25% weight)"""
    nifty = data.get("nifty50", {})
    banknifty = data.get("banknifty", {})
    vix = data.get("india_vix", {})
    fii_dii = data.get("fii_dii", {})

    score = 0
    count = 0

    # Nifty change
    if nifty:
        pct = nifty.get("pChange", 0)
        if pct > 1.5:
            s = 1.0
        elif pct > 0.5:
            s = 0.5
        elif pct > -0.5:
            s = 0
        elif pct > -1.5:
            s = -0.5
        else:
            s = -1.0
        score += s * 0.15
        count += 0.15

    # Bank Nifty
    if banknifty:
        pct = banknifty.get("pChange", 0)
        if pct > 1.5:
            s = 1.0
        elif pct > 0.5:
            s = 0.5
        elif pct > -0.5:
            s = 0
        elif pct > -1.5:
            s = -0.5
        else:
            s = -1.0
        score += s * 0.15
        count += 0.15

    # VIX
    if vix:
        last = vix.get("last", 16)
        if last < 13:
            s = 1.0
        elif last < 16:
            s = 0.5
        elif last < 20:
            s = 0
        elif last < 25:
            s = -0.5
        else:
            s = -1.0
        score += s * 0.20
        count += 0.20

    # FII
    if fii_dii:
        try:
            fii = float(str(fii_dii.get("fii_cash", "0")).replace(",", "").replace("+", ""))
            if fii > 2000:
                s = 1.0
            elif fii > 500:
                s = 0.5
            elif fii > -500:
                s = 0
            elif fii > -2000:
                s = -0.5
            else:
                s = -1.0
            score += s * 0.20
            count += 0.20
        except (ValueError, TypeError):
            pass

        # DII
        try:
            dii = float(str(fii_dii.get("dii_cash", "0")).replace(",", "").replace("+", ""))
            if dii > 2000:
                s = 1.0
            elif dii > 500:
                s = 0.5
            elif dii > -500:
                s = 0
            elif dii > -2000:
                s = -0.5
            else:
                s = -1.0
            score += s * 0.10
            count += 0.10
        except (ValueError, TypeError):
            pass

    return round(min(max(score / max(count, 0.01), -1), 1), 2) if count > 0 else 0


def score_derivatives(data):
    """Category C: Derivatives Analytics (22% weight) - simplified without live PCR/OI"""
    # Without live option chain data, default to neutral
    return 0


def score_currency_commodities(data):
    """Category D: Currency & Commodities (12% weight)"""
    commodities = data.get("commodities", {})
    score = 0
    count = 0

    # Crude oil (lower = better for India)
    if "crude_wti" in commodities:
        pct = commodities["crude_wti"].get("change_pct", 0)
        if pct < -2:
            s = 1.0
        elif pct < -1:
            s = 0.5
        elif pct > 1:
            s = -0.5
        elif pct > 2:
            s = -1.0
        else:
            s = 0
        score += s * 0.30
        count += 0.30

    # Gold (lower = risk-on, better)
    if "gold" in commodities:
        pct = commodities["gold"].get("change_pct", 0)
        if pct < -1.5:
            s = 1.0
        elif pct < -0.5:
            s = 0.5
        elif pct > 0.5:
            s = -0.5
        elif pct > 1.5:
            s = -1.0
        else:
            s = 0
        score += s * 0.20
        count += 0.20

    # USD/INR (INR strengthening = positive)
    if "usdinr" in commodities:
        pct = commodities["usdinr"].get("change_pct", 0)
        if pct < -0.5:
            s = 1.0
        elif pct < -0.2:
            s = 0.5
        elif pct > 0.2:
            s = -0.5
        elif pct > 0.5:
            s = -1.0
        else:
            s = 0
        score += s * 0.40
        count += 0.40

    # US 10Y yield (lower = positive for EM)
    if "us10y" in commodities:
        pct = commodities["us10y"].get("change_pct", 0)
        if pct < -2:
            s = 1.0
        elif pct < -0.5:
            s = 0.5
        elif pct > 0.5:
            s = -0.5
        elif pct > 2:
            s = -1.0
        else:
            s = 0
        score += s * 0.10
        count += 0.10

    return round(min(max(score / max(count, 0.01), -1), 1), 2) if count > 0 else 0


def score_technical(data):
    """Category E: Technical Indicators (13% weight) - simplified"""
    nifty = data.get("nifty50", {})
    if nifty:
        last = nifty.get("last", 0)
        prev = nifty.get("previousClose", 0)
        if prev > 0:
            pct = ((last - prev) / prev) * 100
            if pct > 0.5:
                return 0.25
            elif pct < -0.5:
                return -0.25
    return 0


def score_breadth(data):
    """Category F: Breadth & Flow (10% weight) - simplified"""
    return 0


def score_macro_policy(data):
    """Category G: Macroeconomic & Policy Events (20% weight)"""
    # Check news for RBI/Fed keywords
    news = data.get("news", [])
    for item in news:
        headline = item.get("headline", "").lower()
        if any(kw in headline for kw in ["rbi", "repo rate", "fed", "fomc", "rate cut", "rate hike"]):
            if any(kw in headline for kw in ["cut", "dovish", "pause"]):
                return 0.5
            elif any(kw in headline for kw in ["hike", "hawkish"]):
                return -0.5
    return 0


def score_corporate_events(data):
    """Category H: Corporate Events & Earnings (15% weight)"""
    news = data.get("news", [])
    for item in news:
        headline = item.get("headline", "").lower()
        if any(kw in headline for kw in ["result", "earnings", "quarterly", "profit", "revenue"]):
            if any(kw in headline for kw in ["beat", "surge", "strong", "profit"]):
                return 0.5
            elif any(kw in headline for kw in ["miss", "weak", "loss", "decline"]):
                return -0.5
    return 0


def score_calendar_seasonal(data):
    """Category I: Calendar & Seasonal Factors (12% weight)"""
    return 0


def score_geopolitical(data):
    """Category J: Geopolitical & Global Risk (18% weight)"""
    news = data.get("news", [])
    positive_kw = ["peace", "deal", "ceasefire", "de-escalation", "rally", "surge", "jump"]
    negative_kw = ["war", "conflict", "tension", "strike", "attack", "crisis", "selloff"]

    pos_count = 0
    neg_count = 0
    for item in news:
        headline = item.get("headline", "").lower()
        for kw in positive_kw:
            if kw in headline:
                pos_count += 1
        for kw in negative_kw:
            if kw in headline:
                neg_count += 1

    if pos_count > neg_count:
        return min(0.7, 0.3 + (pos_count - neg_count) * 0.1)
    elif neg_count > pos_count:
        return max(-0.7, -0.3 - (neg_count - pos_count) * 0.1)
    return 0


def score_sector_catalysts(data):
    """Category K: Sector-Specific Catalysts (15% weight)"""
    return 0


def score_regulatory(data):
    """Category L: Regulatory & SEBI Actions (10% weight)"""
    return 0


def score_news_sentiment(data):
    """Category M: Unstructured News Flow (10% weight)"""
    news = data.get("news", [])
    positive_kw = ["surge", "rally", "jump", "gain", "bull", "high", "record", "boom"]
    negative_kw = ["fall", "drop", "crash", "bear", "low", "decline", "slump", "loss"]

    pos = 0
    neg = 0
    for item in news:
        headline = item.get("headline", "").lower()
        for kw in positive_kw:
            if kw in headline:
                pos += 1
        for kw in negative_kw:
            if kw in headline:
                neg += 1

    total = pos + neg
    if total > 0:
        return round((pos - neg) / total, 2)
    return 0


def compute_analysis(data):
    """Compute full analysis with scores."""
    scores = {}

    # Quantitative (60%)
    scores["A_global"] = score_global_sentiment(data)
    scores["B_india"] = score_india_market(data)
    scores["C_derivatives"] = score_derivatives(data)
    scores["D_currency"] = score_currency_commodities(data)
    scores["E_technical"] = score_technical(data)
    scores["F_breadth"] = score_breadth(data)

    # Qualitative (40%)
    scores["G_macro"] = score_macro_policy(data)
    scores["H_corporate"] = score_corporate_events(data)
    scores["I_calendar"] = score_calendar_seasonal(data)
    scores["J_geopolitical"] = score_geopolitical(data)
    scores["K_sector"] = score_sector_catalysts(data)
    scores["L_regulatory"] = score_regulatory(data)
    scores["M_news"] = score_news_sentiment(data)

    # Compute weighted scores
    quant = (
        scores["A_global"] * 0.18
        + scores["B_india"] * 0.25
        + scores["C_derivatives"] * 0.22
        + scores["D_currency"] * 0.12
        + scores["E_technical"] * 0.13
        + scores["F_breadth"] * 0.10
    )

    qual = (
        scores["G_macro"] * 0.20
        + scores["H_corporate"] * 0.15
        + scores["I_calendar"] * 0.12
        + scores["J_geopolitical"] * 0.18
        + scores["K_sector"] * 0.15
        + scores["L_regulatory"] * 0.10
        + scores["M_news"] * 0.10
    )

    final = quant * 0.60 + qual * 0.40
    signal = get_signal(final)

    # Agreement ratio
    all_scores = list(scores.values())
    active = [s for s in all_scores if s != 0]
    if final > 0:
        agreeing = sum(1 for s in active if s > 0.2)
    else:
        agreeing = sum(1 for s in active if s < -0.2)
    agreement = agreeing / max(len(active), 1)

    if agreement > 0.75:
        confidence = "HIGH"
    elif agreement > 0.60:
        confidence = "MEDIUM"
    elif agreement > 0.50:
        confidence = "LOW"
    else:
        confidence = "CHAOS"

    return {
        "scores": scores,
        "quant_score": round(quant, 2),
        "qual_score": round(qual, 2),
        "final_score": round(final, 2),
        "signal": signal,
        "confidence": confidence,
        "agreement": round(agreement, 2),
    }


def generate_pdf(data, analysis):
    """Generate the PDF report."""
    pdf = AnalysisPDF("P", "mm", "A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    date_str = datetime.now().strftime("%d %b %Y")
    run_type = data.get("run_type", "close")
    run_label = {"close": "Previous Day Close", "premarket": "Pre-Market", "open": "Market Open"}.get(run_type, run_type)

    # Title
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 140)
    pdf.ln(8)
    pdf.cell(0, 10, "Nifty F&O Trend Analysis", 0, 1, "C")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 7, f"{date_str} | {run_label}", 0, 1, "C")
    pdf.ln(2)

    # Signal badge
    signal = analysis["signal"]
    confidence = analysis["confidence"]
    if "BULLISH" in signal:
        badge_color = (0, 150, 0)
    elif "BEARISH" in signal:
        badge_color = (200, 50, 50)
    else:
        badge_color = (200, 180, 30)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*badge_color)
    pdf.cell(0, 6, f"SIGNAL: {signal} | CONFIDENCE: {confidence}", 0, 1, "C")
    pdf.ln(4)

    # Executive Summary
    pdf.section_title("1. Executive Summary")
    pdf.body_text(
        f"Automated F&O analysis using {run_label} data. Composite score: "
        f"{analysis['final_score']:+.2f} ({signal.replace('_', ' ')}). "
        f"Agreement ratio: {analysis['agreement']:.0%} ({confidence} confidence)."
    )

    pdf.colored_box("Final Score", f"{analysis['final_score']:+.2f} ({signal.replace('_', ' ')})", badge_color)
    pdf.colored_box("Confidence", f"{confidence} ({analysis['agreement']:.0%})", (240, 180, 30))
    pdf.colored_box("Run Type", run_label, (100, 100, 200))
    pdf.ln(2)

    # Market Snapshot
    pdf.section_title("2. Market Snapshot")

    rows = []
    nifty = data.get("nifty50", {})
    if nifty:
        rows.append(["Nifty 50", f"{nifty.get('last', 'N/A'):,.1f}", f"{nifty.get('pChange', 0):+.2f}%"])
    banknifty = data.get("banknifty", {})
    if banknifty:
        rows.append(["Bank Nifty", f"{banknifty.get('last', 'N/A'):,.1f}", f"{banknifty.get('pChange', 0):+.2f}%"])
    gift = data.get("gift_nifty", {})
    if gift:
        rows.append(["Gift Nifty", f"{gift.get('last', 'N/A'):,.1f}", "Pre-market"])
    vix = data.get("india_vix", {})
    if vix:
        rows.append(["India VIX", f"{vix.get('last', 'N/A'):.2f}", f"{vix.get('pChange', 0):+.2f}%"])

    fii_dii = data.get("fii_dii", {})
    if fii_dii:
        rows.append(["FII Cash", fii_dii.get("fii_cash", "N/A"), ""])
        rows.append(["DII Cash", fii_dii.get("dii_cash", "N/A"), ""])

    us = data.get("us_markets", {})
    for key, name in [("spx", "S&P 500"), ("dow", "Dow Jones"), ("nasdaq", "Nasdaq")]:
        if key in us:
            rows.append([name, f"{us[key]['last']:,.2f}", f"{us[key]['change_pct']:+.2f}%"])

    commodities = data.get("commodities", {})
    for key, name in [("crude_wti", "WTI Crude"), ("gold", "COMEX Gold"), ("usdinr", "USD/INR")]:
        if key in commodities:
            rows.append([name, f"{commodities[key]['last']:,.2f}", f"{commodities[key]['change_pct']:+.2f}%"])

    if rows:
        pdf.data_table(["Indicator", "Value", "Change"], rows, [60, 70, 60])

    # Scoring Engine
    pdf.add_page()
    pdf.section_title("3. Scoring Engine - 13 Categories")
    pdf.sub_title("Quantitative Indicators (60%)")

    s = analysis["scores"]
    pdf.score_bar("A. Global Sentiment [18%]", s["A_global"])
    pdf.score_bar("B. India Market Data [25%]", s["B_india"])
    pdf.score_bar("C. Derivatives [22%]", s["C_derivatives"])
    pdf.score_bar("D. Currency/Commodity [12%]", s["D_currency"])
    pdf.score_bar("E. Technical [13%]", s["E_technical"])
    pdf.score_bar("F. Breadth/Flow [10%]", s["F_breadth"])
    pdf.ln(1)
    pdf.bold_text(f"Quantitative Total: {analysis['quant_score']:+.2f}")

    pdf.ln(2)
    pdf.sub_title("Qualitative Indicators (40%)")
    pdf.score_bar("G. Macro Policy [20%]", s["G_macro"])
    pdf.score_bar("H. Corporate Events [15%]", s["H_corporate"])
    pdf.score_bar("I. Calendar/Seasonal [12%]", s["I_calendar"])
    pdf.score_bar("J. Geopolitical [18%]", s["J_geopolitical"])
    pdf.score_bar("K. Sector Catalysts [15%]", s["K_sector"])
    pdf.score_bar("L. Regulatory [10%]", s["L_regulatory"])
    pdf.score_bar("M. News Sentiment [10%]", s["M_news"])
    pdf.ln(1)
    pdf.bold_text(f"Qualitative Total: {analysis['qual_score']:+.2f}")

    # Composite Score
    pdf.ln(2)
    pdf.section_title("4. Composite Score")
    pdf.data_table(
        ["Component", "Score", "Weight", "Contribution"],
        [
            ["Quantitative", f"{analysis['quant_score']:+.2f}", "60%", f"{analysis['quant_score'] * 0.6:+.3f}"],
            ["Qualitative", f"{analysis['qual_score']:+.2f}", "40%", f"{analysis['qual_score'] * 0.4:+.3f}"],
            ["FINAL", f"{analysis['final_score']:+.2f}", "100%", signal.replace("_", " ")],
        ],
        [50, 40, 40, 60],
    )

    # News Snapshots
    pdf.add_page()
    pdf.section_title("5. News Snapshots")
    news = data.get("news", [])
    if news:
        for i, item in enumerate(news[:8], 1):
            source = item.get("source", "Unknown")
            headline = item.get("headline", "N/A")
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 100, 100)
            pdf.set_x(10)
            pdf.cell(0, 4, f"[{source}]", 0, 1)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(30, 30, 30)
            pdf.set_x(10)
            pdf.multi_cell(0, 4, headline)
            pdf.ln(2)
    else:
        pdf.body_text("No news headlines available for this run.")

    # Override Checks
    pdf.section_title("6. Override Checks")
    chaos_active = analysis["confidence"] == "CHAOS"
    pdf.data_table(
        ["Override", "Status", "Action"],
        [
            ["CHAOS", "ACTIVE" if chaos_active else "NOT ACTIVE", "No Trade" if chaos_active else "Normal"],
            ["Absorbing States", "NOT CHECKED", "Requires live OI data"],
        ],
        [50, 50, 90],
    )

    if chaos_active:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(200, 50, 50)
        pdf.set_x(10)
        pdf.cell(0, 6, "HARD RULE: CHAOS CONFIDENCE - NO TRADE", 0, 1, "C")
        pdf.body_text("Per framework rules, no trade recommendation generated. Paper observation only.")

    # Disclaimer
    pdf.ln(5)
    pdf.set_draw_color(150, 150, 150)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 3.5,
        "DISCLAIMER: This analysis is for educational purposes only. F&O trading carries substantial risk "
        "of loss. Past performance does not guarantee future results. Consult a SEBI-registered investment advisor."
    )

    # Save
    date_file = datetime.now().strftime("%d%b%Y")
    filename = f"Nifty_Analysis_{date_file}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)
    pdf.output(output_path)
    print(f"PDF saved to: {output_path}")
    return output_path, filename


if __name__ == "__main__":
    # Load data
    data_path = os.path.join(DATA_DIR, "market_data.json")
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"No data file found at {data_path}. Running with empty data.")
        data = {"run_type": "manual", "news": []}

    analysis = compute_analysis(data)
    generate_pdf(data, analysis)
