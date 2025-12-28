
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
