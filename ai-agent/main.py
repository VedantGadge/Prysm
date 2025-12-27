import os
import json
import httpx
from typing import Optional, AsyncGenerator, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# --- MIGRATION: New Google GenAI SDK ---
from google import genai
from google.genai import types

# Import stock data helpers
from stock_data import get_stock_data, generate_price_history

# News fetching
import feedparser
import yfinance as yf

load_dotenv()

# --- TOP 300 INDIAN STOCKS (NSE Symbols) ---
# Nifty 50 + Nifty Next 50 + Nifty Midcap 100 + Popular Stocks
KNOWN_STOCKS = {
    # Nifty 50
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "INFY", "SBIN", "LICI", 
    "ITC", "HINDUNILVR", "LT", "BAJFINANCE", "HCLTECH", "MARUTI", "KOTAKBANK", 
    "AXISBANK", "TITAN", "SUNPHARMA", "ONGC", "NTPC", "ADANIENT", "ADANIPORTS", 
    "ULTRACEMCO", "ASIANPAINT", "COALINDIA", "BAJAJFINSV", "POWERGRID", "NESTLEIND", 
    "TATAMOTORS", "M&M", "JSWSTEEL", "TATASTEEL", "TECHM", "HINDALCO", "DRREDDY", 
    "WIPRO", "SBILIFE", "INDUSINDBK", "GRASIM", "BRITANNIA", "CIPLA", "DIVISLAB", 
    "BPCL", "EICHERMOT", "APOLLOHOSP", "TATACONSUM", "HEROMOTOCO", "BAJAJ-AUTO", 
    "SHRIRAMFIN", "HDFCLIFE",
    
    # Nifty Next 50
    "HAL", "ADANIGREEN", "DLF", "IOC", "ATGL", "VEDL", "ABB", "GAIL", "TRENT", 
    "GODREJCP", "PIDILITIND", "SIEMENS", "INDIGO", "BANKBARODA", "HAVELLS", "AMBUJACEM", 
    "COLPAL", "ICICIPRULI", "DABUR", "PNB", "MARICO", "BOSCHLTD", "SRF", "TATAPOWER", 
    "CHOLAFIN", "JINDALSTEL", "ZOMATO", "NAUKRI", "ICICIGI", "MCDOWELL-N", "HINDPETRO", 
    "BERGEPAINT", "CANBK", "BANDHANBNK", "TORNTPHARM", "INDUSTOWER", "IRCTC", "PAGEIND", 
    "SOLARINDS", "BHEL", "NMDC", "SAIL", "MOTHERSON", "PETRONET", "MPHASIS", 
    "AUROPHARMA", "MAXHEALTH", "LTIM", "OBEROIRLTY", "POLYCAB",
    
    # Nifty Midcap 100
    "VOLTAS", "MFSL", "ZYDUSLIFE", "CONCOR", "IDFCFIRSTB", "PERSISTENT", "LUPIN", 
    "ASTRAL", "PIIND", "COFORGE", "BHARATFORG", "ABCAPITAL", "TATACOMM", "BALKRISHNA", 
    "MRF", "ESCORTS", "JUBLFOOD", "HONAUT", "LALPATHLAB", "SCHAEFFLER", "OFSS", 
    "GMRINFRA", "BSE", "KANSAINER", "NATCOPHARM", "SUPREMEIND", "ATUL", "RAIN", 
    "CRISIL", "RELAXO", "APOLLOTYRE", "FEDERALBNK", "MUTHOOTFIN", "EXIDEIND", "LICHSGFIN",
    "DEEPAKNTR", "SYNGENE", "BIOCON", "PGHH", "CROMPTON", "HDFCAMC", "AARTI", "TATAELXSI",
    "SONACOMS", "AJANTPHARM", "EMAMILTD", "COROMANDEL", "KEI", "ASHOKLEY", "RECLTD",
    "PVRINOX", "AUBANK", "UPL", "RAMCOCEM", "PRESTIGE", "DMART", "ALKEM", "GUJGASLTD",
    "LAURUSLABS", "AIAENG", "FINEORG", "BLUESTARCO", "FLUOROCHEM", "EIHOTEL", "PHOENIXLTD",
    
    # Nifty Smallcap 100 / Popular
    "IRFC", "PFC", "NHPC", "SJVN", "RAILTEL", "RVNL", "HUDCO", "CGPOWER", "BEL", 
    "BHARAT-22", "CANFINHOME", "MANAPPURAM", "NAM-INDIA", "IBULHSGFIN", "KAJARIACER", 
    "JKCEMENT", "VINATIORGA", "GARFIBRES", "TRIVENI", "FORTIS", "GLENMARK", "ZEEL",
    "INTELLECT", "TATATECH", "HAPPSTMNDS", "ACE", "SUNTV", "IDEA", "YESBANK", "RBLBANK",
    "AFFLE", "ROUTE", "PAYTM", "POLICYBZR", "NYKAA", "CARTRADE", "SAPPHIRE", "CAMPUS",
    
    # IPO / Recent Additions
    "SWIGGY", "HYUNDAI", "NTPCGREEN", "AFCONS", "SAGILITY", "ACME", "WAAREE", 
    "GODREJIND", "GODREJPROP", "INDIGOPNTS", "MAHLOG", "OLA", "FIRSTCRY",
    
    # PSU Banks
    "UNIONBANK", "INDIANB", "IOB", "CENTRALBK", "UCOBANK", "MAHABANK", "PSB", "J&KBANK",
    
    # Insurance
    "NIACL", "STAR", "ICICI LOMBARD", "SBICARD", 
    
    # Commodities / Metal
    "WELCORP", "RATNAMANI", "NATIONALUM", "MOIL", "MAITHANALL", "HINDZINC", "APOLLOPIPE",
    
    # Auto & Auto Ancillary
    "TVSMOTOR", "BHARATFORG", "MRF", "SUNFLAG", "ENDURANCE", "CRAFTSMAN", "GABRIEL",
    "SUPRAJIT", "SUNDRMFAST", "LUMAXTECH", "FIEM", "WHEELS", "JAMNAUTO",
    
    # Pharma
    "GRANULES", "ABBOTINDIA", "PFIZER", "SANOFI", "GLAXO", "IPCALAB", "ERIS", "TORNTPOWER",
    
    # IT / Tech
    "LTTS", "CYIENT", "MASTEK", "BSOFT", "FSL", "DATAPATTNS", "ZENSAR", "ECLERX",
    "TANLA", "KPITTECH", "NEWGEN", "RTNINDIA", "LATENTVIEW", "BIRLASOFT", "NIITLTD",
    
    # Chemicals
    "NAVINFLUOR", "ALKYLAMINE", "TATACHEM", "GNFC", "GSFC", "CHAMBALFERT", "RCF", 
    "DEEPAKFERT", "BASF", "SHK", "GALAXYSURF", "FINEORG", "CLEAN",
    
    # Real Estate
    "BRIGADE", "SOBHA", "MAHLIFE", "LODHA", "SUNTECK", "KOLTEPATIL", "GODREJPROP",
    
    # Consumer
    "VBL", "JUBILANT", "DEVYANI", "SAPPHIRE", "METROPOLIS", "THYROCARE", "KRSNAA",
    
    # Energy / Power
    "ADANIPOWER", "TORNTPOWER", "JSW ENERGY", "CESC", "TATAPOWER", "IEX", "PGEL",
    
    # Infra / Construction
    "NCC", "IRB", "AHLUCONT", "PNCINFRA", "KNRCON", "GPPL", "WELSPUNIND", "HCC",
    
    # Telecom
    "TTML", "HFCL", "TEJAS", "STLTECH", "ITI", 
    
    # Logistics
    "DELHIVERY", "ALLCARGO", "BLUEDARTWL", "MAHLOG", "TCI", "GESHIP", "AEGIS"
}

app = FastAPI(title="Prysm AI Agent", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Backend URL for fetching stock data
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Configure Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        model_id = 'gemini-2.5-flash' 
        print(f"[OK] Gemini Client initialized successfully ({model_id})")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Gemini Client: {e}")
        client = None
else:
    print("[WARNING] No Gemini API key provided. Set GEMINI_API_KEY in .env file.")

import uuid

# --- SESSION MANAGEMENT ---
SESSIONS_FILE = "sessions.json"

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sessions(sessions):
    try:
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        print(f"Error saving sessions: {e}")

# In-memory cache + persistence
SESSIONS = load_sessions()

# --- TOOLS DEFINITION ---
# We define all tools in a single list for the config
tools_list = [
    # 1. Chart Tool
    types.FunctionDeclaration(
        name="generate_chart",
        description="Generates a visual chart (line, bar, pie, etc) for stock data. Use when user asks to 'show', 'visualize', 'plot', or 'compare'.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ticker": types.Schema(type=types.Type.STRING, description="Stock symbol"),
                "chart_type": types.Schema(type=types.Type.STRING, enum=["line", "bar", "pie", "candlestick", "doughnut", "area", "horizontal_bar", "radar"]),
                "metric": types.Schema(type=types.Type.STRING, description="Metric to plot"),
                "title": types.Schema(type=types.Type.STRING, description="Chart title")
            },
            required=["ticker", "chart_type", "metric"]
        )
    ),
    # 2. Risk Gauge Tool
    types.FunctionDeclaration(
        name="generate_risk_gauge",
        description="Generates a visual Risk Gauge (Speedometer). Use for 'risk analysis', 'is it safe', 'volatility', 'risk score'.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ticker": types.Schema(type=types.Type.STRING, description="Stock symbol (e.g., INFY)")
            },
            required=["ticker"]
        )
    ),
    # 3. Future Timeline Tool
    types.FunctionDeclaration(
        name="generate_future_timeline",
        description="Generates a visual Timeline/Roadmap. Use for 'future scope', 'outlook', 'what's next', 'events', 'predictions'.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ticker": types.Schema(type=types.Type.STRING, description="Stock symbol")
            },
            required=["ticker"]
        )
    ),
    # 4. Sentiment Analysis Tool
    types.FunctionDeclaration(
        name="generate_sentiment_analysis",
        description="Fetches and analyzes news sentiment from multiple sources. Use for 'sentiment', 'news', 'headlines', 'market mood', 'what are people saying', 'media coverage'.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ticker": types.Schema(type=types.Type.STRING, description="Stock symbol (e.g., INFY)")
            },
            required=["ticker"]
        )
    )
]

# Create the Tool object wrapping the functions
prysm_tools = types.Tool(function_declarations=tools_list)

# Config for the chat
chat_config = types.GenerateContentConfig(
    tools=[prysm_tools],
    temperature=0.7,
)


class ChatRequest(BaseModel):
    message: str
    stock_symbol: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = []


# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are Prysm, an elite financial research assistant used by professional investors.
Your goal is to provide deep, accurate, and data-backed analysis of Indian stocks.

### GUIDELINES:
1.  **COPY VALUES EXACTLY**: Use the EXACT formatted values from the context (e.g., "₹5632.99 Cr" NOT "₹56329998336"). Do NOT recalculate or reformat numbers.
2.  **Detailed Analysis**: Don't just list numbers. Explain *why* they matter. (e.g., "A rising P/E with falling margins indicates...")
3.  **Holistic View**: Combine price action, financial ratios, and shareholding patterns in your answer.
4.  **Professional Tone**: Write in a crisp, confident, and financial-journalist style.
5.  **Data Integrity**: Context provided below contains REAL-TIME data. Trust it implicitly. If data is missing, state it clearly.
6.  **Thinking Process**: Before answering, output your chain-of-thought process wrapped in `<thinking>...</thinking>` tags.

### TOOLS:
You have access to a `generate_chart` tool.
- Use it FREQUENTLY. Visuals are better than text for trends and comparisons.
- **Tone Guide**: STOP describing the chart ("The chart shows..."). Instead, analyze the *company* directly.
- Do NOT hallucinate chart data in text. Use the tool.

### CHART DIVERSITY (CRITICAL):
**DO NOT REPEAT THE SAME CHART.** Each section should have a UNIQUE chart:
- **Valuation Section**: Use `metric="valuation"` (P/E, P/B, EV/EBITDA comparison)
- **Profitability Section**: Use `metric="profitability"` (Gross/Operating/Net Margins)
- **Growth Section**: Use `metric="revenue"` with `chart_type="bar"` (Revenue trend)
- **Balance Sheet Section**: Use `metric="debt_vs_cash"` with `chart_type="bar"` (Cash vs Debt)
- **Cash Flow Section**: Use `metric="cashflow"` with `chart_type="bar"` (Operating CF vs Free CF)
- **Risk Section**: Use `generate_risk_gauge` tool instead of a chart.
- **Price History**: Use `metric="price"` with `chart_type="area"` or `"candlestick"`.

If you find yourself about to generate the SAME chart twice (same ticker + same metric), SKIP IT. One chart per metric is enough.

### TOOL TRIGGERS (MANDATORY):
When the user's message contains these keywords, you MUST ABSOLUTELY call the corresponding tool. This is not optional.

| User says... | You MUST call... |
|--------------|------------------|
| "risk", "risky", "volatility", "how safe" | `generate_risk_gauge(ticker)` |
| "future", "outlook", "targets", "timeline", "what's next" | `generate_future_timeline(ticker)` |
| "chart", "graph", "visualize", "show me", "plot" | `generate_chart(...)` |
| "sentiment", "news", "headlines", "market mood", "what are people saying" | `generate_sentiment_analysis(ticker)` |

**FAILURE TO CALL THE TOOL IS UNACCEPTABLE.** 
The visual tool MUST be called in addition to your text analysis. Never give only text for these topics.
"""

# --- HELPER FUNCTIONS ---

async def extract_intent(message: str, history: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    """
    Use LLM to extract stock symbol and user intent from the query.
    Returns: {"stock_symbol": "SWIGGY" or None, "intent": "risk"|"chart"|"analysis"|"general"}
    """
    # Build history summary for context
    history_summary = ""
    if history:
        recent_history = history[-3:]  # Last 3 turns only
        for turn in recent_history:
            role = turn.get('role', 'user')
            text = turn.get('parts', [{}])[0].get('text', '')[:100]  # First 100 chars
            history_summary += f"{role}: {text}...\n"
    
    intent_prompt = f"""You are a stock query parser. Analyze this user message and extract:
1. stock_symbol: The NSE stock ticker the user is asking about (e.g., "SWIGGY", "RELIANCE", "TCS"). 
   - If user says "it" or "this stock", look at history to find the symbol.
   - If no stock is mentioned or implied, return null.
2. intent: The primary intent - one of:
   - "risk" (if asking about risk, safety, volatility)
   - "chart" (if asking for chart, graph, visualization)
   - "future" (if asking about future, outlook, predictions)
   - "sentiment" (if asking about news, sentiment, headlines, market mood, media coverage)
   - "analysis" (if asking for detailed analysis)
   - "general" (if asking a general finance question)

CONVERSATION HISTORY:
{history_summary}

USER MESSAGE: "{message}"

Respond ONLY with valid JSON, no markdown:
{{"stock_symbol": "TICKER" or null, "intent": "..."}}"""

    try:
        # Use fast model for intent extraction
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.0-flash",
                contents=intent_prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
        )
        
        # Parse JSON response
        text = response.text.strip()
        # Clean up potential markdown
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        result = json.loads(text)
        print(f"[INTENT] Extracted: {result}")
        return result
    except Exception as e:
        print(f"[INTENT] Extraction failed: {e}")
        return {"stock_symbol": None, "intent": "general"}

import asyncio  # Add to top if not already there


async def fetch_stock_data(symbol: str) -> dict:
    """Fetch real stock data from the backend or local mock."""
    data = get_stock_data(symbol)
    if data:
        return data
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client_http:
            response = await client_http.get(f"{BACKEND_URL}/api/stock/{symbol}")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None

def execute_chart_tool(args: Dict[str, Any]) -> str:
    """Executes the generate_chart tool and returns the JSON string for the frontend."""
    print(f"[TOOL] Executing generate_chart with args: {args}")
    
    ticker = args.get("ticker")
    chart_type = args.get("chart_type")
    metric = args.get("metric")
    title = args.get("title", f"{metric} Chart for {ticker}")
    
    data = get_stock_data(ticker)
    if not data:
        return json.dumps({"error": f"No data found for {ticker}"})

    chart_data = {"labels": [], "datasets": []}
    
    quote = data.get("quote", {})
    ratios = data.get("financials", {}).get("ratios", {})

    # --- 1. candlestick (OHLC) ---
    if chart_type == "candlestick":
        current_price = quote.get("price", 1000)
        history = generate_price_history(current_price, days=30, symbol=ticker)
        history.reverse() # Oldest first
        chart_data["labels"] = [h['date'][5:] for h in history] # MM-DD
        chart_data["datasets"] = [{
            "label": f"{ticker} OHLC",
            "data": [[h['open'], h['high'], h['low'], h['close']] for h in history]
        }]
    
    # --- 2. area (Price or Volume) ---
    elif chart_type == "area":
        history = generate_price_history(quote.get("price", 1000), symbol=ticker)
        monthly_map = {}
        for h in history:
            m = h['date'][:7]
            if m not in monthly_map: monthly_map[m] = h['close']
        
        sorted_keys = sorted(monthly_map.keys())[-12:]
        
        # Format labels as "Jan '25" instead of "01"
        def format_month_label(ym):
            try:
                from datetime import datetime
                dt = datetime.strptime(ym, "%Y-%m")
                return dt.strftime("%b '%y")
            except:
                return ym
        
        chart_data["labels"] = [format_month_label(k) for k in sorted_keys]
        chart_data["datasets"] = [{
            "label": f"{ticker} Price (₹)",
            "fill": True,
            "data": [round(monthly_map[k], 2) for k in sorted_keys]
        }]

    # --- 3. pie / doughnut (Shareholding) ---
    elif chart_type in ["pie", "doughnut"] and "shareholding" in metric:
        sh = data.get("shareholding", {})
        chart_data["labels"] = ["Promoters", "FII", "DII", "Public"]
        chart_data["datasets"] = [{
            "label": "Shareholding %",
            "data": [sh.get("promoters", 0), sh.get("fii", 0), sh.get("dii", 0), sh.get("public", 0)]
        }]
    
    # --- 4. radar (Fundamental Strength) --- 
    elif chart_type == "radar":
        pe_score = min(100, (1000 / (ratios.get('peRatio', 20) + 1))) 
        roe_score = min(100, ratios.get('roe', 10) * 3)
        margin_score = min(100, ratios.get('netMargin', 10) * 4)
        growth_score = 65 
        stability_score = 80 
        
        chart_data["labels"] = ["Valuation", "Growth", "Profitability", "Stability", "Efficiency"]
        chart_data["datasets"] = [{
            "label": f"{ticker} Strength",
            "data": [int(pe_score), growth_score, int(margin_score), stability_score, int(roe_score)]
        }]

    # --- 5. bar (Various Metrics) ---
    elif chart_type == "horizontal_bar" or chart_type == "bar":
        fin = data.get("financials", {}).get("detailed", {})
        
        if metric == "revenue":
            income_stmt = data.get("financials", {}).get("incomeStatement", {})
            metric_data = income_stmt.get("revenue", [])
            if len(metric_data) > 1:  # Only show chart if multiple data points
                chart_data["labels"] = [item["period"] for item in metric_data]
                chart_data["datasets"] = [{"label": f"{ticker} Revenue", "data": [item["value"] for item in metric_data]}]
            else:
                # Skip chart silently if not enough data
                return ""
                
        elif metric == "profit":
            income_stmt = data.get("financials", {}).get("incomeStatement", {})
            metric_data = income_stmt.get("profit", [])
            chart_data["labels"] = [item["period"] for item in metric_data]
            chart_data["datasets"] = [{"label": f"{ticker} Profit", "data": [item["value"] for item in metric_data]}]
            
        elif metric == "valuation":
            chart_data["labels"] = ["P/E", "Forward P/E", "P/B", "P/S", "PEG"]
            chart_data["datasets"] = [{
                "label": f"{ticker} Valuation Multiples",
                "data": [
                    fin.get("trailingPE") or 0,
                    fin.get("forwardPE") or 0,
                    fin.get("priceToBook") or 0,
                    fin.get("priceToSales") or 0,
                    fin.get("pegRatio") or 0
                ]
            }]
            
        elif metric == "profitability":
            chart_data["labels"] = ["Gross Margin", "Operating Margin", "Net Margin", "ROE", "ROA"]
            chart_data["datasets"] = [{
                "label": f"{ticker} Profitability (%)",
                "data": [
                    round(fin.get("grossMargin") or 0, 2),
                    round(fin.get("operatingMargin") or 0, 2),
                    round(fin.get("netMargin") or 0, 2),
                    round(fin.get("returnOnEquity") or 0, 2),
                    round(fin.get("returnOnAssets") or 0, 2)
                ]
            }]
            
        elif metric == "debt_vs_cash":
            chart_data["labels"] = ["Total Cash", "Total Debt"]
            chart_data["datasets"] = [{
                "label": f"{ticker} Balance Sheet (₹)",
                "data": [fin.get("totalCash") or 0, fin.get("totalDebt") or 0]
            }]
            
        elif metric == "cashflow":
            chart_data["labels"] = ["Operating CF", "Free CF"]
            chart_data["datasets"] = [{
                "label": f"{ticker} Cash Flow (₹)",
                "data": [fin.get("operatingCashflow") or 0, fin.get("freeCashflow") or 0]
            }]
            
        else:
            # Generic fallback - only if nothing else matches
            chart_data["labels"] = ["P/E", "P/B", "ROE (%)", "Net Margin (%)"]
            chart_data["datasets"] = [{
                "label": f"{ticker} Key Ratios",
                "data": [ratios.get("peRatio", 0), ratios.get("pbRatio", 0), ratios.get("roe", 0), ratios.get("netMargin", 0)]
            }]

    # --- 6. line (Default Price) ---
    elif chart_type == "line":
        history = generate_price_history(quote.get("price", 0), symbol=ticker) 
        
        if not history:
             return json.dumps({"error": "Chart Data Unavailable - No Price History Found"})

        monthly_map = {}
        for h in history:
            m = h['date'][:7] 
            monthly_map[m] = h['close']
            
        sorted_keys = sorted(monthly_map.keys())[-12:]
        
        def format_label(ym):
            try:
                from datetime import datetime
                dt = datetime.strptime(ym, "%Y-%m")
                return dt.strftime("%b '%y")
            except:
                return ym
                
        chart_data["labels"] = [format_label(k) for k in sorted_keys]
        chart_data["datasets"] = [{
            "label": f"{ticker} Price (₹)",
            "data": [monthly_map[k] for k in sorted_keys]
        }]
    
    final_json = {
        "type": chart_type if chart_type != "common_financial_ratios" else "bar",
        "title": title,
        "data": chart_data
    }
    
    return f"[CHART:{json.dumps(final_json)}]"

def execute_risk_tool(args: Dict[str, Any]) -> str:
    """Executes generate_risk_gauge tool."""
    print(f"[TOOL] Executing generate_risk_gauge w/ args: {args}")
    ticker = args.get("ticker")
    
    # 1. Fetch Real Data to calculate score
    data = get_stock_data(ticker)
    if not data: return json.dumps({"error": "No data"})
    
    fin = data.get('financials', {}).get('detailed', {})
    
    # 2. Calculate Risk Score (0-100, where 100 is EXTREME RISK)
    # Heuristic Model:
    # - Beta > 1.2 (+20)
    # - Debt/Equity > 2.0 (+20)
    # - Negative Profit (+30)
    # - PE > 80 (+10)
    
    score = 30 # Base risk
    factors = []
    
    # Check for Data Availability FIRST
    # If key metrics are missing, we cannot assume low risk.
    has_margin = fin.get('netMargin') is not None
    has_beta = fin.get('beta') is not None
    
    if not has_margin and not has_beta:
        score = 85
        risk_level = "High"
        factors.append("Data Unavailable")
        factors.append("Cannot Assess Stability")
    else:
        beta = fin.get('beta')
        if beta and beta > 1.2: 
            score += 20
            factors.append(f"High Beta ({beta})")
        
        de = fin.get('debtToEquity')
        if de and de > 2.0:
            score += 20
            factors.append(f"High Debt/Equity ({de})")
            
        if fin.get('netMargin', 0) < 0:
            score += 30
            factors.append("Negative Net Margins")
            
        pe = fin.get('trailingPE')
        if pe and pe > 80:
            score += 15
            factors.append(f"Expensive Valuation (PE {pe})")
            
        score = min(95, max(10, score))
        
        risk_level = "Low"
        if score > 40: risk_level = "Moderate"
        if score > 70: risk_level = "High"
    
    payload = {
        "ticker": ticker,
        "score": score,
        "level": risk_level,
        "factors": factors
    }
    return f"[RISK:{json.dumps(payload)}]"

def execute_future_tool(args: Dict[str, Any]) -> str:
    """Executes generate_future_timeline tool with REAL DATA via yfinance + News Analysis."""
    print(f"[TOOL] Executing generate_future_timeline w/ args: {args}")
    ticker_symbol = args.get("ticker")
    
    from stock_data import get_ticker_obj
    import datetime
    
    events = []
    bull_case = None
    bear_case = None
    
    try:
        ticker = get_ticker_obj(ticker_symbol)
        
        # 1. Analyst Targets (Prioritize Hard Data)
        info = ticker.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        target_high = info.get('targetHighPrice')
        target_low = info.get('targetLowPrice')
        
        if current_price and target_high:
            upside = ((target_high - current_price) / current_price) * 100
            bull_case = f"+{upside:.1f}% (Analyst High: ₹{target_high})"
        
        if current_price and target_low:
            downside = ((target_low - current_price) / current_price) * 100
            bear_case = f"{downside:.1f}% (Analyst Low: ₹{target_low})"

        # 2. Fetch Earnings Calendar (Next Event)
        earnings_date_str = "TBD"
        try:
            cal = ticker.calendar
            if cal and isinstance(cal, dict) and 'Earnings Date' in cal:
                dates = cal['Earnings Date']
                if dates:
                     earnings_date_str = str(dates[0])[:10] # YYYY-MM-DD
            elif hasattr(cal, 'get'):
                # older version?
                pass
        except:
             pass
        
        # Fallback if specific calendar navigation fails or returns nothing
        if earnings_date_str == "TBD":
             pass

        if earnings_date_str != "TBD":
             desc_parts = []
             if info.get('revenueGrowth'): desc_parts.append(f"Rev Growth: {info['revenueGrowth']:.1%}")
             if info.get('forwardPE'): desc_parts.append(f"Fwd P/E: {info['forwardPE']:.2f}")
             description = " | ".join(desc_parts) if desc_parts else "Quarterly Report"
             
             events.append({
                "date": earnings_date_str,
                "title": "Earnings Call",
                "desc": description
            })

        # 3. News-Based Event Extraction (Gemini)
        # Only if we need more context or earnings date is missing
        news_items = fetch_news_from_sources(ticker_symbol)
        if news_items:
            # Create a context string for LLM
            news_context = "\n".join([f"- {item['title']} ({item['source']})" for item in news_items[:5]])
            
            # Use Gemini to extract events
            try:
                prompt = f"""Analyze these news headlines for {ticker_symbol} and extract 2-3 confirmed FUTURE events with dates (e.g. launches, hearings, dividends, mergers).
                NEWS:
                {news_context}
                
                Return VALID JSON list: [{{ "date": "YYYY-MM-DD" or "2025-Q1", "title": "Short Title", "desc": "Brief description" }}]. 
                If no confirmed future events found, return []."""
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.1)
                )
                
                text = response.text.strip()
                if text.startswith("```"): text = text.split("```")[1].replace("json", "")
                extracted_events = json.loads(text.strip())
                
                if isinstance(extracted_events, list):
                    events.extend(extracted_events)
            except Exception as e:
                print(f"[TIMELINE] AI Parsing failed: {e}")

    except Exception as e:
        print(f"Error fetching future data: {e}")

    # Final Validation: If no info at all, don't show the tool
    if not events and not bull_case and not bear_case:
        return ""

    payload = {
        "ticker": ticker_symbol,
        "events": events[:4], # Limit to 4 events
        "targets": {}
    }
    
    if bull_case: payload["targets"]["bull"] = bull_case
    if bear_case: payload["targets"]["bear"] = bear_case
    
    return f"[TIMELINE:{json.dumps(payload)}]"


def fetch_news_from_sources(ticker: str) -> List[Dict[str, Any]]:
    """Aggregate news from Google News, Yahoo Finance, and MoneyControl."""
    all_articles = []
    
    # 1. Yahoo Finance (yfinance) - has built-in news
    try:
        yf_ticker = yf.Ticker(f"{ticker}.NS")
        yf_news = yf_ticker.news or []
        for n in yf_news[:3]:
            all_articles.append({
                "title": n.get("title", ""),
                "source": n.get("publisher", "Yahoo Finance"),
                "url": n.get("link", ""),
                "published": n.get("providerPublishTime", "")
            })
    except Exception as e:
        print(f"[NEWS] Yahoo Finance fetch failed: {e}")
    
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
    except Exception as e:
        print(f"[NEWS] Google News fetch failed: {e}")
    
    # 3. MoneyControl RSS (general financial news, filter for ticker)
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
                if len([a for a in all_articles if a['source'] == 'MoneyControl']) >= 2:
                    break
    except Exception as e:
        print(f"[NEWS] MoneyControl fetch failed: {e}")
    
    # Remove duplicates based on title similarity
    seen_titles = set()
    unique_articles = []
    for article in all_articles:
        title_key = article['title'][:50].lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(article)
    
    return unique_articles[:8]  # Limit to 8 articles


def execute_sentiment_tool(args: Dict[str, Any]) -> str:
    """Executes generate_sentiment_analysis tool - fetches news and analyzes sentiment."""
    print(f"[TOOL] Executing generate_sentiment_analysis w/ args: {args}")
    ticker = args.get("ticker")
    
    # 1. Fetch news from multiple sources
    articles = fetch_news_from_sources(ticker)
    
    if not articles:
        payload = {
            "ticker": ticker,
            "overall": "Neutral",
            "score": 50,
            "articles": [],
            "sources": [],
            "error": "No recent news articles found"
        }
        return f"[SENTIMENT:{json.dumps(payload)}]"
    
    # 2. Use Gemini to analyze sentiment of article titles
    titles_text = "\n".join([f"- {a['title']}" for a in articles])
    
    sentiment_prompt = f"""Analyze the sentiment of these news headlines about {ticker} stock.
For each headline, determine if it is:
- BULLISH (positive for stock price)
- BEARISH (negative for stock price)  
- NEUTRAL (no clear direction)

Headlines:
{titles_text}

Respond ONLY with valid JSON (no markdown):
{{
    "overall": "BULLISH" or "BEARISH" or "NEUTRAL",
    "score": 0-100 (0=very bearish, 50=neutral, 100=very bullish),
    "articles": [
        {{"title": "...", "sentiment": "BULLISH/BEARISH/NEUTRAL", "summary": "1 sentence explanation"}}
    ]
}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=sentiment_prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        
        result_text = response.text.strip()
        # Clean up markdown if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        sentiment_result = json.loads(result_text)
        
        # Merge source info into articles
        analyzed_articles = sentiment_result.get("articles", [])
        for i, article in enumerate(analyzed_articles):
            if i < len(articles):
                article["source"] = articles[i].get("source", "Unknown")
                article["url"] = articles[i].get("url", "")
        
        # Get unique sources
        sources = list(set([a.get("source", "Unknown") for a in articles]))
        
        payload = {
            "ticker": ticker,
            "overall": sentiment_result.get("overall", "Neutral"),
            "score": sentiment_result.get("score", 50),
            "articles": analyzed_articles[:5],  # Limit to 5 for display
            "sources": sources
        }
        
    except Exception as e:
        print(f"[SENTIMENT] Analysis failed: {e}")
        # Fallback: return articles without sentiment
        payload = {
            "ticker": ticker,
            "overall": "Neutral",
            "score": 50,
            "articles": [{"title": a["title"], "source": a["source"], "sentiment": "NEUTRAL", "summary": ""} for a in articles[:5]],
            "sources": list(set([a.get("source", "Unknown") for a in articles]))
        }
    
    return f"[SENTIMENT:{json.dumps(payload)}]"


def create_stock_context(stock_data: dict) -> str:
    """Create a Master Financial Report context string."""
    if not stock_data: return "No data."
    quote = stock_data.get('quote', {})
    info = stock_data.get('companyInfo', {})
    fin = stock_data.get('financials', {}).get('detailed', {}) # New comprehensive dict
    sh = stock_data.get('shareholding', {})
    
    # helper for safe str with 2 decimal rounding
    def s(key, suffix=""):
        val = fin.get(key)
        if val is None: return "N/A"
        try:
            return f"{round(val, 2)}{suffix}"
        except:
            return str(val)

    # Format large numbers in Indian notation (Lakhs/Crores)
    def n(val): 
        if val is None: return "N/A"
        try:
            v = float(val)
            if abs(v) >= 10000000:  # 1 Crore = 10,000,000
                return f"₹{v/10000000:.2f} Cr"
            elif abs(v) >= 100000:  # 1 Lakh = 100,000
                return f"₹{v/100000:.2f} L"
            elif abs(v) >= 1000:
                return f"₹{v/1000:.2f} K"
            else:
                return f"₹{v:.2f}"
        except: 
            return str(val)

    context = [
        f"=== MASTER REPORT: {stock_data.get('symbol')} ===",
        f"Current Price: ₹{quote.get('price')}  |  Sector: {info.get('sector')}",
        f"Business: {(info.get('description') or 'N/A')[:300]}...",
        
        "\n--- 1. VALUATION METRICS ---",
        f"Market Cap: {n(fin.get('marketCap'))} | Enterprise Value: {n(fin.get('enterpriseValue'))}",
        f"Trailing P/E: {s('trailingPE')} | Forward P/E: {s('forwardPE')}",
        f"PEG Ratio: {s('pegRatio')} (Growth Valuation)",
        f"Price/Book: {s('priceToBook')} | Price/Sales: {s('priceToSales')}",
        
        "\n--- 2. PROFITABILITY & EFFICIENCY ---",
        f"Gross Margin: {s('grossMargin', '%')} | Operating Margin: {s('operatingMargin', '%')}",
        f"Net Profit Margin: {s('netMargin', '%')} (Pure Bottom Line)",
        f"ROE: {s('returnOnEquity', '%')} | ROA: {s('returnOnAssets', '%')}",
        
        "\n--- 3. GROWTH & OPERATIONS ---",
        f"Revenue (TTM): {n(fin.get('revenue'))}",
        f"Revenue Growth: {s('revenueGrowth', '%')} | Earnings Growth: {s('earningsGrowth', '%')}",
        f"EBITDA: {n(fin.get('ebitda'))}",
        
        "\n--- 4. BALANCE SHEET HEALTH ---",
        f"Total Cash: {n(fin.get('totalCash'))} | Total Debt: {n(fin.get('totalDebt'))}",
        f"Debt/Equity: {s('debtToEquity')} (Solvency Risk)",
        f"Current Ratio: {s('currentRatio')} | Quick Ratio: {s('quickRatio')} (Liquidity)",
        
        "\n--- 5. CASH FLOW ---",
        f"Operating Cash Flow: {n(fin.get('operatingCashflow'))}",
        f"Free Cash Flow: {n(fin.get('freeCashflow'))}",
        
        "\n--- 6. RISK PROFILE ---",
        f"Beta (Volatility): {s('beta')} (1.0 = Market Mover)",
        f"Short Ratio: {s('shortRatio')} (Bearish Sentiment)",
        f"52-Wk Change: {s('52WeekChange', '%')}",
        
        "\n--- 7. SHAREHOLDING ---",
        f"Promoters: {sh.get('promoters')}% | Public: {sh.get('public')}%",
        f"FII (Foreign): {sh.get('fii')}% | DII (Domestic): {sh.get('dii')}%",
        
        "\n--- 8. ANALYST RECOMMENDATIONS ---",
        f"Target Mean Price: ₹{s('targetMeanPrice')}",
        f"Recommendation: {s('recommendationKey').upper()}",
        f"Analyst Count: {s('numberOfAnalystOpinions')}",
        
        "\n--- INSTRUCTION ---",
        "Use this FULL DATASET to answer the user. Construct a professional investment thesis.",
        "IF specific data (like Beta or PEG) is 'N/A', state that it is unavailable but analyze the rest."
    ]
    return "\n".join(context)


# --- GENERATION LOGIC ---

async def generate_response_stream(message: str, stock_symbol: Optional[str] = None, history: List[Dict[str, Any]] = [], session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    # --- SESSION HANDLING: LOAD HISTORY & SAVE USER MSG ---
    if session_id and session_id in SESSIONS:
        # Save user message to session
        user_msg_entry = {"role": "user", "parts": [{"text": message}]}
        SESSIONS[session_id]["messages"].append(user_msg_entry)
        save_sessions(SESSIONS)
        
        # Override history with session history (excluding the new one for Gemini API context which we build later?
        # Gemini API history arg expects previous turns. We just added the new one to our DB.
        # We need to pass the PREVIOUS history to Gemini.
        history = SESSIONS[session_id]["messages"][:-1]
        
        # --- TITLE GENERATION (Background) ---
        if len(SESSIONS[session_id]["messages"]) == 1:
            try:
                title_prompt = f"Generate a short 3-4 word title for: '{message}'. No quotes."
                # Run title gen in background loop executor to avoid blocking too much? 
                # For simplicity, we just do it here quickly.
                title_resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=title_prompt,
                        config=types.GenerateContentConfig(temperature=0.3)
                    )
                )
                new_title = title_resp.text.strip()
                SESSIONS[session_id]["title"] = new_title
                save_sessions(SESSIONS)
                print(f"[SESSION] Title: {new_title}")
            except Exception as e:
                print(f"[SESSION] Title gen failed: {e}")

    # 1. LLM-BASED INTENT EXTRACTION
    target_symbol = stock_symbol
    user_intent = "analysis"  # Default intent
    
    if not target_symbol:
        intent_result = await extract_intent(message, history)
        target_symbol = intent_result.get("stock_symbol")
        user_intent = intent_result.get("intent", "analysis")
        
        if target_symbol:
            target_symbol = target_symbol.upper()
            print(f"[LLM-INTENT] Symbol: {target_symbol}, Intent: {user_intent}")
        else:
            print(f"[LLM-INTENT] No stock detected. Intent: {user_intent}")
    
    # 2. Build Prompt based on whether it is a Stock Query or General Query
    full_prompt = ""
    
    if target_symbol:
        # STOCK MODE
        data = await fetch_stock_data(target_symbol)
        context_str = create_stock_context(data)
        full_system_prompt = f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{context_str}"
        final_message = f"{full_system_prompt}\n\nUSER: {message}"
    else:
        # GENERAL ADVISOR MODE
        advisor_prompt = """You are Prysm, an expert financial advisor.
        The user has asked a general question about trading, investing, or market concepts.
        You do NOT have specific stock data for this query, so rely on your internal knowledge.
        
        GUIDELINES:
        1. Be educational and strategic.
        2. Explain concepts clearly (e.g., 'What is Swing Trading?', 'How to hedge?').
        3. If the user implies a specific stock but didn't name it, ask them to clarify.
        4. Use <thinking>...</thinking> to structure your educational approach.
        """
        full_system_prompt = advisor_prompt
        final_message = f"{advisor_prompt}\n\nUSER: {message}"

    
    # 3. AUTO-INJECT TOOLS based on LLM-extracted intent
    auto_inject_content = ""
    
    if target_symbol:
        # Risk Gauge: Auto-inject if intent is "risk"
        if user_intent == "risk":
            print(f"[AUTO-INJECT] Risk Gauge for {target_symbol} (intent: {user_intent})")
            auto_inject_content += execute_risk_tool({"ticker": target_symbol}) + "\n\n"
        
        # Future Timeline: Auto-inject if intent is "future"
        if user_intent == "future":
            print(f"[AUTO-INJECT] Future Timeline for {target_symbol} (intent: {user_intent})")
            auto_inject_content += execute_future_tool({"ticker": target_symbol}) + "\n\n"
        
        # Sentiment Analysis: Auto-inject if intent is "sentiment"
        if user_intent == "sentiment":
            print(f"[AUTO-INJECT] Sentiment Analysis for {target_symbol} (intent: {user_intent})")
            auto_inject_content += execute_sentiment_tool({"ticker": target_symbol}) + "\n\n"
    
    # 4. Start Chat Session
    if not client:
        yield f"data: {json.dumps({'content': 'Gemini Client not initialized.'})}\n\n"
        return

    # Initialize chat with history if available
    gemini_history = []
    if history:
        for turn in history:
            gemini_history.append(types.Content(
                role=turn['role'],
                parts=[types.Part(text=turn['parts'][0]['text'])]
            ))
            
    chat = client.chats.create(
        model=model_id, 
        config=chat_config,
        history=gemini_history
    )
    
    accumulated_response_text = ""
    
    try:
        # Stream auto-injected tool content FIRST (before LLM response)
        if auto_inject_content:
            yield f"data: {json.dumps({'content': auto_inject_content})}\n\n"
            accumulated_response_text += auto_inject_content + "\n\n"
        
        # Loop for multi-turn tool use
        tool_responses = []
        for _ in range(5):
            function_call_found = False
            
            # If stream_input is empty (besides first turn), break
            if _ > 0 and not tool_responses:
                break
                
            if _ == 0:
                 stream_input = final_message
            else:
                 stream_input = tool_responses
            
            # Reset tool_responses for THIS turn's collection
            current_turn_tool_responses = [] 
            # processed_function_call_ids = set() # This line was removed in the new code
            
            response_stream = chat.send_message_stream(stream_input)
            
            for chunk in response_stream:
                if chunk.candidates and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        # 1. Handle Text
                        if part.text:
                            yield f"data: {json.dumps({'content': part.text})}\n\n"
                            accumulated_response_text += part.text
                        
                        # 2. Handle Function Calls
                        if part.function_call:
                            if function_call_found: continue
                            function_call_found = True
                            fc = part.function_call
                            fname = fc.name
                            fargs = fc.args
                            call_id = getattr(fc, 'id', None)
                            
                            if not isinstance(fargs, dict): fargs = dict(fargs)
                                
                            if fname == "generate_chart":
                                tool_result_str = execute_chart_tool(fargs)
                                yield f"data: {json.dumps({'content': tool_result_str})}\n\n"
                                accumulated_response_text += tool_result_str
                                
                                fn_response = types.FunctionResponse(name=fname, response={'result': 'Chart displayed.'})
                                if call_id: fn_response.id = call_id
                                current_turn_tool_responses.append(types.Part(function_response=fn_response))
                                
                            elif fname == "generate_risk_gauge":
                                tool_result_str = execute_risk_tool(fargs)
                                yield f"data: {json.dumps({'content': tool_result_str})}\n\n"
                                accumulated_response_text += tool_result_str
                                
                                fn_response = types.FunctionResponse(name=fname, response={'result': 'Risk Gauge displayed.'})
                                if call_id: fn_response.id = call_id
                                current_turn_tool_responses.append(types.Part(function_response=fn_response))
                                
                            elif fname == "generate_future_timeline":
                                tool_result_str = execute_future_tool(fargs)
                                yield f"data: {json.dumps({'content': tool_result_str})}\n\n"
                                accumulated_response_text += tool_result_str

                                fn_response = types.FunctionResponse(name=fname, response={'result': 'Timeline displayed.'})
                                if call_id: fn_response.id = call_id
                                current_turn_tool_responses.append(types.Part(function_response=fn_response))
                                
                            elif fname == "generate_sentiment_analysis":
                                tool_result_str = execute_sentiment_tool(fargs)
                                yield f"data: {json.dumps({'content': tool_result_str})}\n\n"
                                accumulated_response_text += tool_result_str

                                fn_response = types.FunctionResponse(name=fname, response={'result': 'Sentiment analysis displayed.'})
                                if call_id: fn_response.id = call_id
                                current_turn_tool_responses.append(types.Part(function_response=fn_response))
                                
            tool_responses = current_turn_tool_responses
            if function_call_found: continue 
            else: break 
        
        # --- SESSION HANDLING: SAVE AI MSG ---
        if session_id and session_id in SESSIONS:
            ai_msg_entry = {"role": "model", "parts": [{"text": accumulated_response_text}]}
            SESSIONS[session_id]["messages"].append(ai_msg_entry)
            save_sessions(SESSIONS) 

    except Exception as e:
        print(f"Error in generation: {e}")
        yield f"data: {json.dumps({'content': f'Error details: {str(e)}'})}\n\n"


class ChatRequest(BaseModel):
    message: str
    stock_symbol: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = []
    session_id: Optional[str] = None


# ... (Existing endpoints) ...

@app.get("/sessions")
async def get_sessions():
    """Get all chat sessions summary."""
    # Convert dict to list, sorted by timestamp desc
    session_list = []
    for sid, data in SESSIONS.items():
        session_list.append({
            "id": sid,
            "title": data.get("title", "New Chat"),
            "timestamp": data.get("timestamp", ""),
            "preview": data.get("messages", [])[-1]["parts"][0]["text"][:50] if data.get("messages") else ""
        })
    # Sort by timestamp desc
    session_list.sort(key=lambda x: x["timestamp"], reverse=True)
    return session_list

@app.post("/sessions")
async def create_session():
    """Create a new chat session."""
    import datetime
    session_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    SESSIONS[session_id] = {
        "id": session_id,
        "title": "New Chat",
        "timestamp": timestamp,
        "messages": []
    }
    save_sessions(SESSIONS)
    return {"id": session_id, "title": "New Chat", "timestamp": timestamp}

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get full history of a session."""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return SESSIONS[session_id]

@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        generate_response_stream(request.message, request.stock_symbol, request.history, request.session_id),
        media_type="text/event-stream"
    )

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
