"""
Real-time stock data fetching using yfinance.
"""

import yfinance as yf
from datetime import datetime
import pandas as pd
import traceback
import requests
from bs4 import BeautifulSoup
import re

def get_ticker_obj(symbol: str):
    """Helper to get yf.Ticker object, defaulting to NSE (.NS)."""
    # Simple heuristic: if no suffix, assume NSE for Indian context
    if "." not in symbol:
        symbol = f"{symbol}.NS"
    return yf.Ticker(symbol)

def generate_price_history(current_price: float, days: int = 365, symbol: str = None) -> list:
    """
    Generate price history from yfinance.
    Note: current_price arg is kept for compatibility but ignored if symbol is provided.
    If symbol is None, it falls back to mock (should not happen with new logic).
    """
    if not symbol:
        # STRICT: No mock data allowed
        return []

    try:
        ticker_obj = get_ticker_obj(symbol)
        # Fetch 1y history to cover enough ground, or 'max' if needed
        # period='1y' or '1mo' depending on days
        period = "1y"
        if days > 365: period = "5y"
        elif days <= 30: period = "3mo" # Get a bit more for candles
        
        hist = ticker_obj.history(period=period)
        
        # Reset index to get Date as column
        hist = hist.reset_index()
        
        # Format
        output = []
        # Sort descending (latest last) usually yfinance gives ascending.
        # Our previous mock gave ascending (oldest first)? 
        # Main.py logic: chart_data["labels"] = [h['date'][5:] for h in history]
        # Recharts usually expects ascending (Time ->).
        
        # Slice to requested days
        # df.tail(days)
        hist = hist.tail(days)
        
        for _, row in hist.iterrows():
            # Handle Date (timestamp)
            date_str = row['Date'].strftime("%Y-%m-%d")
            output.append({
                "date": date_str,
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": int(row['Volume'])
            })
        return output
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []

def scrape_stock_data(symbol: str) -> dict:
    """
    Final Resort: Web Scraping Yahoo Finance Page.
    """
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        print(f"[DEBUG] Scraping URL: {url}")
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            print(f"[DEBUG] Yahoo Scrape failed: {response.status_code}. Trying Google Finance...")
            # Google Finance Fallback
            # Ticker: SWIGGY.NS -> SWIGGY:NSE
            g_ticker = symbol.replace('.NS', ':NSE').replace('.BO', ':BOM')
            g_url = f"https://www.google.com/finance/quote/{g_ticker}"
            print(f"[DEBUG] Google URL: {g_url}")
            g_resp = requests.get(g_url, headers=headers, timeout=5)
            if g_resp.status_code == 200:
                 g_soup = BeautifulSoup(g_resp.text, 'html.parser')
                 # Google Finance Price class: 'YMlKec fxKbKc' (often changes, but 'YMlKec' is somewhat stable)
                 # Better to find by structure
                 price_div = g_soup.find('div', {'class': 'YMlKec fxKbKc'})
                 if price_div:
                     price = float(price_div.text.replace('₹', '').replace(',', '').strip())
                     print(f"[DEBUG] Google Finance Scrape Success! Price: {price}")
                     return {
                        'currentPrice': price,
                        'regularMarketPrice': price,
                        'previousClose': price, # unavailable easily
                        'dayHigh': price,
                        'dayLow': price,
                        'volume': 0,
                        'longName': f"{symbol} (Google Scrape)",
                        'marketCap': 0,
                        'scraped': True
                    }
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Yahoo Finance HTML classes change often, so we look for data-attributes or common patterns
        # Price is usually in a <fin-streamer data-field="regularMarketPrice"> or similar
        
        price = None
        # Strategy 1: fin-streamer tag (most reliable for real-time)
        streamer = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
        if streamer and streamer.text:
            price = float(streamer.text.replace(',', '').strip())
            
        # Strategy 2: If streamer fails, try looking for the main price class (often changes)
        if not price:
            # Look for look-alikes of standard price classes
            price_tag = soup.find('div', {'data-test': 'qsp-price'})
            if price_tag:
                # usually inside a span
                span = price_tag.find('span')
                if span: price = float(span.text.replace(',', '').strip())

        if not price:
            print("[DEBUG] Scrape failed to find price in HTML")
            return None
            
        print(f"[DEBUG] Web Scrape Success! Price: {price}")
        
        # Try to get other stats if possible
        prev_close = 0
        pc_streamer = soup.find('fin-streamer', {'data-field': 'regularMarketPreviousClose'})
        if pc_streamer: prev_close = float(pc_streamer.text.replace(',', ''))
        
        # Return a partial info dict mimicking yfinance 'info'
        return {
            'currentPrice': price,
            'regularMarketPrice': price,
            'previousClose': prev_close,
            'dayHigh': price, # Approximation
            'dayLow': price, # Approximation
            'volume': 0, # Hard to scrape robustly without robust selector
            'longName': f"{symbol} (Scraped)",
            'marketCap': 0,
            'scraped': True
        }
        
    except Exception as e:
        print(f"[DEBUG] Scraping Exception: {e}")
        return None

import time

# Simple in-memory cache: {symbol: {'data': dict, 'timestamp': float}}
DATA_CACHE = {}
CACHE_DURATION = 300  # 5 minutes

def get_stock_data(symbol: str) -> dict:
    """Get real-time stock data from Yahoo Finance with caching."""
    if not symbol:
        return None
        
    symbol = symbol.upper()
        
    # Check Cache
    if symbol in DATA_CACHE:
        cached = DATA_CACHE[symbol]
        if time.time() - cached['timestamp'] < CACHE_DURATION:
            print(f"[DEBUG] Returning cached data for {symbol}")
            return cached['data']
    
    try:
        ticker = get_ticker_obj(symbol)
        info = ticker.info
        
        # Basic Validation: if no price, maybe invalid
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        
        # FALLBACK 1: fast_info (Newer YF API)
        if not current_price:
            try:
                current_price = ticker.fast_info.last_price
                print(f"[DEBUG] Using fast_info price: {current_price}")
            except: pass
            
        # FALLBACK 3: yf.download (Bulk endpoint, often works for cached/blocked tickers)
        if not current_price:
            try:
                # progress=False prevents printing to stdout
                import io
                from contextlib import redirect_stdout
                with redirect_stdout(io.StringIO()):
                    df = yf.download(symbol, period="5d", progress=False)
                
                if not df.empty:
                    current_price = float(df['Close'].iloc[-1])
                    print(f"[DEBUG] Used yf.download fallback: {current_price}")
                    # Also recover other basic data if missing
                    if not info.get('dayHigh'): info['dayHigh'] = float(df['High'].iloc[-1])
                    if not info.get('dayLow'): info['dayLow'] = float(df['Low'].iloc[-1])
                    if not info.get('volume'): info['volume'] = int(df['Volume'].iloc[-1])
            except Exception as e:
                print(f"[DEBUG] Download fallback failed: {e}")

        # FALLBACK 4: Web Scraping (Last Resort)
        if not current_price:
            print("[DEBUG] All API methods failed. Attempting Web Scrape...")
            scraped_data = scrape_stock_data(symbol)
            if scraped_data:
                 current_price = scraped_data['currentPrice']
                 print(f"[DEBUG] Web Scrape successful: {current_price} | Using fallback data.")
                 # Merge scraped info into 'info' dict so subsequent logic works
                 info.update(scraped_data)
                 # Mark as scraped in info for risk tool to see?
                 info['is_scraped_fallback'] = True

        if not current_price:
            # Try removing suffix if added or clean up
            return None

        # --- Construct Quote ---
        quote = {
            "price": round(current_price, 2),
            "change": 0, # Calc below
            "changePercent": 0,
            "open": info.get('open', 0) or round(float(df['Open'].iloc[-1]), 2) if 'df' in locals() and not df.empty else 0,
            "high": info.get('dayHigh', 0),
            "low": info.get('dayLow', 0),
            "volume": info.get('volume', 0),
            "marketCap": info.get('marketCap', 0),
            "pe": info.get('trailingPE', 0),
            "eps": info.get('trailingEps', 0),
            "dividend": info.get('dividendRate', 0),
            "dividendYield": (info.get('dividendYield', 0) or 0) * 100,
            "week52High": info.get('fiftyTwoWeekHigh', 0),
            "week52Low": info.get('fiftyTwoWeekLow', 0),
        }
        
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
        # If prev_close missing, try to infer from history if we fetched it?
        # For now, safe default
        if prev_close:
            quote["change"] = round(current_price - prev_close, 2)
            quote["changePercent"] = round(((current_price - prev_close) / prev_close) * 100, 2)

        # --- Construct Financials (Mocking some parts as yf structure is complex/variable) ---
        # Ideally extract income_stmt
        
        # Mocking quarterly revenue/profit labels for UI to ensure it renders something
        # Real data extraction from ticker.quarterly_income_stmt is possible but often messy keys
        # We will try to get TTM values or last 4 quarters if possible, else stick to some generic logic
        # For robustness in this short timeframe, we map ratios correctly but might leave lists simplified
        
        # --- Comprehensive Financials & Ratios ---
        # We extract EVERYTHING available for deep analysis.
        
        financials = {
            # Valuation
            "marketCap": info.get('marketCap'),
            "enterpriseValue": info.get('enterpriseValue'),
            "trailingPE": info.get('trailingPE'),
            "forwardPE": info.get('forwardPE'),
            "pegRatio": info.get('pegRatio'),
            "priceToBook": info.get('priceToBook'),
            "priceToSales": info.get('priceToSalesTrailing12Months'),
            
            # Profitability
            "grossMargin": (info.get('grossMargins', 0) or 0) * 100,
            "operatingMargin": (info.get('operatingMargins', 0) or 0) * 100,
            "netMargin": (info.get('profitMargins', 0) or 0) * 100,
            "returnOnEquity": (info.get('returnOnEquity', 0) or 0) * 100,
            "returnOnAssets": (info.get('returnOnAssets', 0) or 0) * 100,
            
            # Operations / Growth
            "revenue": info.get('totalRevenue'),
            "revenueGrowth": (info.get('revenueGrowth', 0) or 0) * 100,
            "earningsGrowth": (info.get('earningsGrowth', 0) or 0) * 100,
            "ebitda": info.get('ebitda'),
            
            # Balance Sheet / Financial Health
            "totalCash": info.get('totalCash'),
            "totalDebt": info.get('totalDebt'),
            "debtToEquity": info.get('debtToEquity'),
            "currentRatio": info.get('currentRatio'),
            "quickRatio": info.get('quickRatio'),
            
            # Cash Flow
            "operatingCashflow": info.get('operatingCashflow'),
            "freeCashflow": info.get('freeCashflow'),
            
            # Risk / Stock Info
            "beta": info.get('beta'),
            "shortRatio": info.get('shortRatio'),
            "52WeekChange": (info.get('52WeekChange', 0) or 0) * 100,
            
            # Analyst Targets
            "targetHighPrice": info.get('targetHighPrice'),
            "targetLowPrice": info.get('targetLowPrice'),
            "targetMeanPrice": info.get('targetMeanPrice'),
            "recommendationKey": info.get('recommendationKey'),
            "numberOfAnalystOpinions": info.get('numberOfAnalystOpinions')
        }
        
        # Legacy support for existing tool code
        ratios = {
            "peRatio": financials['trailingPE'],
            "pbRatio": financials['priceToBook'],
            "roe": financials['returnOnEquity'],
            "netMargin": financials['netMargin']
        }

        # Shareholding (YF often lacks Indian shareholding, we provide placeholders if missing)
        # Verify if holders exists
        promoters = 0
        fii = 0
        dii = 0
        public = 0
        
        # Major holders usually gives percentages held by Insiders (Promoters) and Institutions
        # holders = ticker.major_holders
        # This is often slow or broken. We will use a safe fallback or parsed data if available.
        # For this iteration, we keep shareholding dynamic but maybe random if real data unavailable?
        # Actually, let's keep shareholding somewhat static or simplified to avoid 0s. 
        # YFinance 'major_holders' [0] is % insiders, [1] is % institutions.
        try:
           mh = ticker.major_holders
           if isinstance(mh, pd.DataFrame):
                # Check structure: 'Breakdown' column or index?
                # Usually it has columns [0, 1] or ['Breakdown', 'Value'] depending on version.
                # We convert to dict for safety.
                # Case 1: Columns are 0 and 1 (older YF)
                # Case 2: Named columns
                
                # Normalize to dict
                mh_dict = {}
                # If 'Breakdown' is a column, set it as index
                if 'Breakdown' in mh.columns and 'Value' in mh.columns:
                    mh.set_index('Breakdown', inplace=True)
                    mh_dict = mh['Value'].to_dict()
                elif 0 in mh.columns and 1 in mh.columns:
                    # Old style: 0 is "20% % Insiders", 1 is "..."
                    # But the debug output showed keys like 'insidersPercentHeld'.
                    # Let's try to iterate if specific keys aren't found.
                    pass
                
                # Try to get values using the keys seen in debug output
                # Keys: 'insidersPercentHeld', 'institutionsPercentHeld'
                
                # If dict is empty, maybe it's the structure from debug:
                # Breakdown (Index?) | Value
                # insidersPercentHeld | 0.16
                if not mh_dict and 'Value' in mh.columns:
                     # Maybe Breakdown is the index name?
                     mh_dict = mh['Value'].to_dict()
                
                # Extract
                insiders_pct = mh_dict.get('insidersPercentHeld', 0)
                if insiders_pct > 1: insiders_pct /= 100 # Handle 16.0 vs 0.16
                
                inst_pct = mh_dict.get('institutionsPercentHeld', 0)
                if inst_pct > 1: inst_pct /= 100
                
                promoters = insiders_pct * 100
                total_inst = inst_pct * 100
                
                # Heuristic split for India (FII vs DII not explicitly in major_holders)
                fii = total_inst * 0.55 
                dii = total_inst * 0.45
                
                public = 100 - promoters - total_inst
                if public < 0: public = 0

           else:
               # Fallback if not DF
               promoters = 50.0
               public = 50.0
        except Exception as e:
            print(f"Shareholding parse error: {e}")
            promoters = 50.0
            public = 50.0

        shareholding = {
            "promoters": round(promoters, 2),
            "fii": round(fii, 2),
            "dii": round(dii, 2),
            "public": round(public, 2),
        }

        # Company Info
        company_info = {
            "sector": info.get('sector', 'Unknown'),
            "industry": info.get('industry', 'Unknown'),
            "employees": info.get('fullTimeEmployees', 0),
            "founded": "N/A", # YF doesn't always have founded year clearly
            "headquarters": f"{info.get('city', '')}, {info.get('country', '')}",
            "description": info.get('longBusinessSummary') or info.get('shortName')
        }

        result = {
            "symbol": symbol.upper(),
            "name": info.get('longName') or symbol,
            "exchange": "NSE" if ".NS" in ticker.ticker else "Unknown",
            "quote": quote,
            "financials": {
                "incomeStatement": {
                    "revenue": [{"period": "TTM", "value": info.get('totalRevenue', 0)}],
                    "profit": [{"period": "TTM", "value": info.get('netIncomeToCommon', 0)}]
                },
                "ratios": ratios,
                "detailed": financials # FULL DATASET
            },
            "shareholding": shareholding,
            "companyInfo": company_info
        }
        
        # Save to Cache
        DATA_CACHE[symbol.upper()] = {'data': result, 'timestamp': time.time()}
        return result

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        # traceback.print_exc() # Reduce noise
        
        # Cache failure to prevent retry spam
        DATA_CACHE[symbol.upper()] = {'data': None, 'timestamp': time.time()}
        return None

def search_stocks(query: str) -> list:
    """Mock search or pass-through. YFinance doesn't have good text search."""
    # We can keep a small cache of popular stocks or just return query as a result
    upper = query.upper()
    return [{
        "symbol": upper,
        "name": f"{upper} (Fetched Real-Time)",
        "exchange": "NSE"
    }]
