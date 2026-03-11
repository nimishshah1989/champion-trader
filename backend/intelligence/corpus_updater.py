"""
corpus_updater.py — Nightly Corpus B ingestion.

Runs at 17:30 IST every market day.
Ingests:
  - Nifty 200 daily OHLCV summary (top movers, PPC/NPC detected, sector leaders)
  - India VIX reading
  - Regime classification for the day

Maintains rolling 90-day window — deletes documents older than 90 days.
"""

import logging
from datetime import datetime

import yfinance as yf

from backend.config import settings
from backend.intelligence.rag_engine import delete_old_documents, ingest_document

logger = logging.getLogger(__name__)


async def ingest_daily():
    """
    Nightly ingestion job for Corpus B.
    Called by APScheduler at 17:30 IST on market days.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Corpus B ingestion starting for {today}")

    chunks_ingested = 0

    # 1. Fetch India VIX
    try:
        vix_data = yf.download("^INDIAVIX", period="5d", progress=False)
        if not vix_data.empty:
            vix_close = float(vix_data["Close"].iloc[-1])
            vix_text = f"India VIX on {today}: {vix_close:.2f}"
            if vix_close > 20:
                vix_text += " (ELEVATED — high volatility regime likely)"
            elif vix_close < 13:
                vix_text += " (LOW — calm market, contraction setups may work better)"

            chunks_ingested += ingest_document(
                text=vix_text,
                metadata={"corpus": "b", "date": today, "type": "vix", "source": "yfinance"},
                corpus="corpus_b",
            )
    except Exception as e:
        logger.error(f"VIX fetch failed: {e}")

    # 2. Fetch Nifty 50 summary
    try:
        nifty = yf.download("^NSEI", period="5d", progress=False)
        if not nifty.empty:
            close = float(nifty["Close"].iloc[-1])
            prev_close = float(nifty["Close"].iloc[-2]) if len(nifty) > 1 else close
            change_pct = ((close - prev_close) / prev_close) * 100

            nifty_text = (
                f"Nifty 50 on {today}: Close {close:.2f}, "
                f"Change {change_pct:+.2f}%, "
                f"High {float(nifty['High'].iloc[-1]):.2f}, "
                f"Low {float(nifty['Low'].iloc[-1]):.2f}"
            )

            chunks_ingested += ingest_document(
                text=nifty_text,
                metadata={"corpus": "b", "date": today, "type": "nifty_summary", "source": "yfinance"},
                corpus="corpus_b",
            )
    except Exception as e:
        logger.error(f"Nifty fetch failed: {e}")

    # 3. Fetch top Nifty 200 movers (sample: top 20 by volume)
    try:
        from backend.data.nse_stocks import NIFTY_200

        # Fetch a subset for daily summary
        symbols = [f"{s}.NS" for s in NIFTY_200[:50]]
        data = yf.download(symbols, period="2d", group_by="ticker", progress=False)

        movers = []
        for sym in NIFTY_200[:50]:
            try:
                ticker = f"{sym}.NS"
                if ticker in data.columns.get_level_values(0):
                    df = data[ticker].dropna()
                    if len(df) >= 2:
                        close = float(df["Close"].iloc[-1])
                        prev = float(df["Close"].iloc[-2])
                        pct = ((close - prev) / prev) * 100
                        vol = float(df["Volume"].iloc[-1])
                        movers.append({"symbol": sym, "change_pct": pct, "volume": vol, "close": close})
            except Exception:
                continue

        if movers:
            # Top gainers
            gainers = sorted(movers, key=lambda x: x["change_pct"], reverse=True)[:5]
            losers = sorted(movers, key=lambda x: x["change_pct"])[:5]

            summary_parts = [f"Market movers on {today}:"]
            summary_parts.append("Top gainers: " + ", ".join(
                f"{m['symbol']} ({m['change_pct']:+.1f}%)" for m in gainers
            ))
            summary_parts.append("Top losers: " + ", ".join(
                f"{m['symbol']} ({m['change_pct']:+.1f}%)" for m in losers
            ))

            mover_text = "\n".join(summary_parts)
            chunks_ingested += ingest_document(
                text=mover_text,
                metadata={"corpus": "b", "date": today, "type": "movers", "source": "yfinance"},
                corpus="corpus_b",
            )
    except Exception as e:
        logger.error(f"Movers fetch failed: {e}")

    # 4. Purge old documents (rolling 90-day window)
    deleted = delete_old_documents("corpus_b", days=settings.corpus_b_retention_days)

    logger.info(
        f"Corpus B ingestion complete: {chunks_ingested} chunks ingested, "
        f"{deleted} old documents purged"
    )

    return {"chunks_ingested": chunks_ingested, "deleted": deleted}
