"""
run_analysis.py - Main entry point for the F&O analysis bot.
Usage: python run_analysis.py [close|premarket|open]
"""
import sys
import os
import json
from datetime import datetime

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    # Determine run type from args or time
    if len(sys.argv) > 1:
        run_type = sys.argv[1]
    else:
        # Auto-detect based on IST time
        from datetime import timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        hour = now.hour

        if 23 <= hour or hour < 5:
            run_type = "close"
        elif 5 <= hour < 8:
            run_type = "premarket"
        else:
            run_type = "open"

    print(f"=" * 60)
    print(f"F&O India Trading Analysis Bot")
    print(f"Run Type: {run_type}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"=" * 60)

    # Step 1: Fetch data
    print("\n[Step 1/2] Fetching market data...")
    from fetch_data import fetch_all
    try:
        data = fetch_all(run_type)
        print(f"Data fetched successfully. Keys: {list(data.keys())}")
    except Exception as e:
        print(f"Error fetching data: {e}")
        # Try to use existing data
        data_path = os.path.join("data", "market_data.json")
        if os.path.exists(data_path):
            print("Using existing data file.")
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"run_type": run_type, "news": []}

    # Step 2: Generate PDF
    print("\n[Step 2/2] Generating PDF...")
    from generate_pdf import compute_analysis, generate_pdf
    try:
        analysis = compute_analysis(data)
        pdf_path, filename = generate_pdf(data, analysis)

        print(f"\n{'=' * 60}")
        print(f"Analysis Complete!")
        print(f"Final Score: {analysis['final_score']:+.2f} ({analysis['signal']})")
        print(f"Confidence: {analysis['confidence']} ({analysis['agreement']:.0%})")
        print(f"PDF: {pdf_path}")
        print(f"{'=' * 60}")

        return pdf_path, filename

    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    main()
