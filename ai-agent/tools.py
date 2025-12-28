"""
Prysm AI Agent - Tools Module
Contains the visual and analytical tools used by the LangGraph agent.
"""
import json
import os
from typing import Dict, Any, List, Optional
import feedparser
import yfinance as yf
from langchain_core.tools import tool
from stock_data import get_stock_data, generate_price_history, get_ticker_obj
from google import genai
from google.genai import types
from dotenv import load_dotenv

from pathlib import Path
env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize Gemini for internal tool usage (Sentiment/Future extraction)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[TOOLS] Gemini Init Failed: {e}")

# --- HELPER: News Fetching ---
def fetch_news_from_sources(ticker: str) -> List[Dict[str, Any]]:
    """Aggregate news from Google News, Yahoo Finance, and MoneyControl."""
    all_articles = []
    
    # 1. Yahoo Finance
    try:
        yf_ticker = yf.Ticker(f"{ticker}.NS")
        yf_news = yf_ticker.news or []
        for n in yf_news[:3]:
            all_articles.append({
                "title": n.get("title", ""),
                "source": n.get("publisher", "Yahoo Finance"),
                "url": n.get("link", ""),
                "published": str(n.get("providerPublishTime", ""))
            })
    except Exception:
        pass
    
    # 2. Google News RSS
    try:
        google_url = f"https://news.google.com/rss/search?q={ticker}+stock+india&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(google_url)
        for entry in feed.entries[:4]:
            source_name = entry.source.title if hasattr(entry, 'source') and hasattr(entry.source, 'title') else "Google News"
            all_articles.append({
                "title": entry.title,
                "source": source_name,
                "url": entry.link,
                "published": entry.get("published", "")
            })
    except Exception:
        pass
    
    # 3. MoneyControl RSS
    try:
        mc_url = "https://www.moneycontrol.com/rss/latestnews.xml"
        mc_feed = feedparser.parse(mc_url)
        for entry in mc_feed.entries[:10]:
            if ticker.lower() in entry.title.lower():
                all_articles.append({
                    "title": entry.title,
                    "source": "MoneyControl",
                    "url": entry.link,
                    "published": entry.get("published", "")
                })
                if len([a for a in all_articles if a['source'] == 'MoneyControl']) >= 2: break
    except Exception:
        pass
    
    # Dedup
    seen_titles = set()
    unique_articles = []
    for article in all_articles:
        t = article['title'][:50].lower()
        if t not in seen_titles:
            seen_titles.add(t)
            unique_articles.append(article)
            
    return unique_articles[:8]

# --- TOOL 1: CHART GENERATOR ---
@tool
def generate_chart(ticker: str, chart_type: str, metric: str, title: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a visual chart for stock data.
    Args:
        ticker: Stock symbol (e.g. INFY)
        chart_type: One of 'line', 'bar', 'pie', 'candlestick', 'doughnut', 'area', 'radar'
        metric: Metric to plot (e.g. 'price', 'valuation', 'revenue', 'profitability')
        title: Optional title for the chart
    """
    if not title: title = f"{metric} Chart for {ticker}"
    
    data = get_stock_data(ticker)
    if not data:
        return {"ui_content": json.dumps({"error": f"No data found for {ticker}"}), "llm_data": {"result": "No data"}}

    chart_data = {"labels": [], "datasets": []}
    quote = data.get("quote", {})
    ratios = data.get("financials", {}).get("ratios", {})
    fin = data.get("financials", {}).get("detailed", {})

    # Use REAL yfinance data only
    try:
        ticker_obj = get_ticker_obj(ticker)
        if not ticker_obj:
            return {"ui_content": "", "llm_data": {"result": "Data unavailable"}}
        
        if chart_type in ["candlestick", "area", "line"]:
            # Get real historical data
            hist = ticker_obj.history(period="3mo")
            if hist.empty:
                return {"ui_content": "", "llm_data": {"result": "No price history"}}
            
            if chart_type == "candlestick":
                hist = hist.tail(30)
                chart_data["labels"] = [d.strftime("%Y-%m-%d") for d in hist.index]
                chart_data["datasets"] = [{"label": f"{ticker} OHLC", "data": [[row['Open'], row['High'], row['Low'], row['Close']] for _, row in hist.iterrows()]}]
            elif chart_type == "area":
                monthly = hist.resample('M').last()
                chart_data["labels"] = [d.strftime("%Y-%m") for d in monthly.index[-12:]]
                chart_data["datasets"] = [{"label": f"{ticker} Price", "fill": True, "data": monthly['Close'].tail(12).tolist()}]
            else:  # line
                chart_data["labels"] = [d.strftime("%Y-%m-%d") for d in hist.index[-30:]]
                chart_data["datasets"] = [{"label": "Price", "data": hist['Close'].tail(30).tolist()}]
        
        elif chart_type in ["bar", "horizontal_bar"]:
            if metric == "valuation":
                pe = fin.get("trailingPE")
                pb = fin.get("priceToBook")
                ps = fin.get("priceToSales")
                if not any([pe, pb, ps]):
                    return {"ui_content": "", "llm_data": {"result": "Valuation data unavailable"}}
                chart_data["labels"] = ["P/E", "P/B", "P/S"]
                chart_data["datasets"] = [{"label": "Valuation", "data": [pe or 0, pb or 0, ps or 0]}]
            elif metric == "profitability":
                gm = fin.get("grossMargin")
                nm = fin.get("netMargin")
                roe = fin.get("returnOnEquity")
                if not any([gm, nm, roe]):
                    return {"ui_content": "", "llm_data": {"result": "Profitability data unavailable"}}
                chart_data["labels"] = ["Gross Margin", "Net Margin", "ROE"]
                chart_data["datasets"] = [{"label": "Margins %", "data": [gm or 0, nm or 0, roe or 0]}]
            else:
                return {"ui_content": "", "llm_data": {"result": f"Metric {metric} not supported"}}
                
        elif chart_type in ["pie", "doughnut"]:
            if metric == "shareholding":
                shareholding = data.get("shareholding", {})
                if not shareholding:
                    return {"ui_content": "", "llm_data": {"result": "Shareholding data unavailable"}}
                
                chart_data["labels"] = ["Promoters", "FII", "DII", "Public"]
                chart_data["datasets"] = [{
                    "label": "Shareholding Pattern",
                    "data": [
                        shareholding.get("promoters", 0),
                        shareholding.get("fii", 0),
                        shareholding.get("dii", 0),
                        shareholding.get("public", 0)
                    ]
                }]
            else:
                return {"ui_content": "", "llm_data": {"result": f"Pie chart for {metric} not supported (try 'shareholding')"}}
                
        else:
            return {"ui_content": "", "llm_data": {"result": f"Chart type {chart_type} not supported"}}
    except Exception as e:
        print(f"[CHART] Error: {e}")
        return {"ui_content": "", "llm_data": {"result": "Chart generation failed"}}

    final_json = {"type": chart_type, "title": title, "data": chart_data}
    
    return {
        "ui_content": f"[CHART:{json.dumps(final_json)}]",
        "llm_data": {
            "result": "Chart displayed.",
            "summary": f"Chart {title} showed {metric} data for {ticker}."
        }
    }

# --- TOOL 2: RISK GAUGE ---
@tool
def generate_risk_gauge(ticker: str) -> Dict[str, Any]:
    """Generates a visual Risk Gauge (Speedometer) for a stock."""
    data = get_stock_data(ticker)
    if not data: return {"ui_content": "", "llm_data": {"result": "No data"}}
    
    fin = data.get('financials', {}).get('detailed', {})
    
    # Only show risk if we have real beta data
    beta = fin.get('beta')
    if not beta:
        return {"ui_content": "", "llm_data": {"result": "Risk data unavailable (no beta)"}}
    
    score = 0
    factors = []
    
    if beta > 1.5:
        score += 40
        factors.append(f"Very High Beta ({beta:.2f})")
    elif beta > 1.2: 
        score += 25
        factors.append(f"High Beta ({beta:.2f})")
    elif beta < 0.8:
        score -= 10
        factors.append(f"Low Volatility (Beta: {beta:.2f})")
        
    if fin.get('netMargin', 0) < 0:
        score += 30
        factors.append("Negative Net Margins")
    
    debt_ratio = fin.get('debtToEquity')
    if debt_ratio and debt_ratio > 2:
        score += 20
        factors.append(f"High Debt (D/E: {debt_ratio:.2f})")
        
    score = max(0, min(100, score))  # Clamp 0-100
    
    risk_level = "Low"
    if score > 40: risk_level = "Moderate"
    if score > 70: risk_level = "High"
    
    if not factors:
        factors.append("Standard risk profile")
    
    payload = {"ticker": ticker, "score": score, "level": risk_level, "factors": factors}
    
    return {
        "ui_content": f"[RISK:{json.dumps(payload)}]",
        "llm_data": {
            "result": "Risk Gauge displayed.",
            "risk_score": score,
            "risk_level": risk_level,
            "factors": factors
        }
    }

# --- TOOL 3: FUTURE TIMELINE ---
@tool
def generate_future_timeline(ticker: str) -> Dict[str, Any]:
    """Generates a visual Timeline/Roadmap for a stock."""
    # Try to get real calendar events from yfinance
    try:
        ticker_obj = get_ticker_obj(ticker)
        if not ticker_obj:
            return {"ui_content": "", "llm_data": {"result": "Ticker data unavailable"}}
        
        events = []
        calendar = ticker_obj.calendar
        
        if calendar and 'Earnings Date' in calendar:
            earnings_date = calendar['Earnings Date']
            if hasattr(earnings_date, '__iter__'):
                earnings_date = earnings_date[0] if len(earnings_date) > 0 else None
            if earnings_date:
                events.append({
                    "date": str(earnings_date)[:10],
                    "title": "Earnings Report",
                    "desc": "Quarterly Results"
                })
        
        # Don't show if no real events
        if not events:
            return {"ui_content": "", "llm_data": {"result": "No upcoming events available"}}
        
        payload = {"ticker": ticker, "events": events}
        
        return {
            "ui_content": f"[TIMELINE:{json.dumps(payload)}]",
            "llm_data": {
                "result": "Timeline displayed.",
                "events_count": len(events),
                "events": str(events)
            }
        }
    except Exception as e:
        print(f"[TIMELINE] Error: {e}")
        return {"ui_content": "", "llm_data": {"result": "Timeline unavailable"}}

# --- TOOL 4: SENTIMENT ANALYSIS ---
@tool
def generate_sentiment_analysis(ticker: str) -> Dict[str, Any]:
    """Fetches and analyzes news sentiment from multiple sources."""
    articles = fetch_news_from_sources(ticker)
    if not articles:
        return {"ui_content": f"[SENTIMENT:{json.dumps({'error': 'No news'})}]", "llm_data": {"result": "No news found"}}
        
    # Mock AI analysis if client fails, or real if persistent
    overall = "Neutral"
    score = 50
    if client:
        try:
            titles = "\n".join([a['title'] for a in articles])
            prompt = f"Analyze sentiment for {ticker}: {titles}. Return JSON {{'overall': 'BULLISH', 'score': 80}}"
            res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            # Minimal parsing for migration proof-of-concept
            if "BULLISH" in res.text: overall = "Bullish"; score=80
            elif "BEARISH" in res.text: overall = "Bearish"; score=30
        except:
            pass

    payload = {
        "ticker": ticker,
        "overall": overall,
        "score": score,
        "articles": [{"title": a["title"], "source": a["source"], "sentiment": "Neutral"} for a in articles[:5]],
        "sources": list(set(a['source'] for a in articles))
    }
    
    return {
        "ui_content": f"[SENTIMENT:{json.dumps(payload)}]",
        "llm_data": {
            "result": "Sentiment Analysis displayed.",
            "overall": overall,
            "score": score
        }
    }

# --- TOOL 5: STOCK COMPARISON ---
@tool
def compare_stocks(ticker1: str, ticker2: str) -> Dict[str, Any]:
    """
    Compares two stocks side-by-side on key financial metrics.
    Args:
        ticker1: First stock symbol (e.g. TCS)
        ticker2: Second stock symbol (e.g. INFY)
    """
    data1 = get_stock_data(ticker1)
    data2 = get_stock_data(ticker2)
    
    if not data1 or not data2:
        return {"ui_content": "", "llm_data": {"result": f"Data unavailable for one or more tickers ({ticker1}, {ticker2})"}}
        
    def get_val(data, path):
        # path e.g. "financials.detailed.trailingPE"
        keys = path.split(".")
        val = data
        for k in keys:
            val = val.get(k, {})
        return val if isinstance(val, (int, float, str)) else "N/A"

    # Define comparison rows
    metrics = [
        ("Price", "quote.price"),
        ("Market Cap", "financials.detailed.marketCap"),
        ("P/E Ratio", "financials.detailed.trailingPE"),
        ("P/B Ratio", "financials.detailed.priceToBook"),
        ("ROE %", "financials.detailed.returnOnEquity"),
        ("Net Margin %", "financials.detailed.netMargin"),
        ("Rev Growth %", "financials.detailed.revenueGrowth"),
        ("Debt/Eq", "financials.detailed.debtToEquity")
    ]
    
    comparison_data = []
    for label, path in metrics:
        comparison_data.append({
            "metric": label,
            ticker1: get_val(data1, path),
            ticker2: get_val(data2, path)
        })
        
    payload = {
        "ticker1": ticker1,
        "ticker2": ticker2,
        "data": comparison_data
    }
    
    return {
        "ui_content": f"[COMPARISON:{json.dumps(payload)}]",
        "llm_data": {
            "result": f"Comparison between {ticker1} and {ticker2} displayed.",
            "data": str(comparison_data)
        }
    }

# --- TOOL 6: RAG RETRIEVAL ---
from rag_service import query_rag

@tool
def consult_knowledge_base(query: str) -> Dict[str, Any]:
    """
    Searches uploaded documents (PDFs, reports) for information.
    Use this when the user asks about specific uploaded files within their "knowledge base".
    It retrieves relevant excerpts from the vector database.
    """
    docs = query_rag(query, n_results=3)
    
    if not docs:
        return {
            "ui_content": "",
            "llm_data": {"result": "No relevant info found in uploaded documents."}
        }
    
    # Simple context joining
    context = "\n\n".join([f"Excerpt: {d}" for d in docs])
    
    return {
        "ui_content": "[DOC_SEARCH_ACTIVE]",
        "llm_data": {
            "result": "Found relevant document excerpts.",
            "excerpts": context
        }
    }