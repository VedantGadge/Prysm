// Stock data service using Yahoo Finance API
import YahooFinance from 'yahoo-finance2'

// Create Yahoo Finance instance with suppressed notices
const yahooFinance = new YahooFinance({ 
  suppressNotices: ['yahooSurvey', 'ripHistorical'] 
})

// NSE stock symbol mapping (Yahoo Finance uses .NS suffix for NSE stocks)
const NSE_SUFFIX = '.NS'

// Map common symbols to Yahoo Finance format
const SYMBOL_MAP = {
  'RELIANCE': 'RELIANCE.NS',
  'TCS': 'TCS.NS',
  'INFY': 'INFY.NS',
  'HDFCBANK': 'HDFCBANK.NS',
  'ICICIBANK': 'ICICIBANK.NS',
  'WIPRO': 'WIPRO.NS',
  'BHARTIARTL': 'BHARTIARTL.NS',
  'ITC': 'ITC.NS',
  'SBIN': 'SBIN.NS',
  'KOTAKBANK': 'KOTAKBANK.NS',
  'LT': 'LT.NS',
  'HINDUNILVR': 'HINDUNILVR.NS',
  'ASIANPAINT': 'ASIANPAINT.NS',
  'MARUTI': 'MARUTI.NS',
  'SUNPHARMA': 'SUNPHARMA.NS',
  'AXISBANK': 'AXISBANK.NS',
  'BAJFINANCE': 'BAJFINANCE.NS',
  'TATAMOTORS': 'TATAMOTORS.NS',
  'TATASTEEL': 'TATASTEEL.NS',
  'ADANIENT': 'ADANIENT.NS',
}

// Convert symbol to Yahoo Finance format
function toYahooSymbol(symbol) {
  const upperSymbol = symbol.toUpperCase()
  if (SYMBOL_MAP[upperSymbol]) {
    return SYMBOL_MAP[upperSymbol]
  }
  // If already has .NS or .BO suffix, use as is
  if (upperSymbol.endsWith('.NS') || upperSymbol.endsWith('.BO')) {
    return upperSymbol
  }
  // Default to NSE
  return `${upperSymbol}.NS`
}

// Get comprehensive stock data
export async function getStockData(symbol) {
  const yahooSymbol = toYahooSymbol(symbol)
  const upperSymbol = symbol.toUpperCase().replace('.NS', '').replace('.BO', '')

  try {
    // Fetch quote data
    const quote = await yahooFinance.quote(yahooSymbol)
    
    // Fetch chart data for price history (last 1 year) - using chart() instead of deprecated historical()
    const endDate = new Date()
    const startDate = new Date()
    startDate.setFullYear(startDate.getFullYear() - 1)
    
    const chartData = await yahooFinance.chart(yahooSymbol, {
      period1: startDate,
      period2: endDate,
      interval: '1d',
    })
    const historical = chartData.quotes || []

    // Fetch quote summary for additional details
    let quoteSummary = null
    try {
      quoteSummary = await yahooFinance.quoteSummary(yahooSymbol, {
        modules: ['summaryDetail', 'financialData', 'defaultKeyStatistics', 'majorHoldersBreakdown', 'assetProfile'],
      })
    } catch (e) {
      console.log('Quote summary not available for', yahooSymbol)
    }

    // Format the response
    const stockData = {
      symbol: upperSymbol,
      name: quote.longName || quote.shortName || upperSymbol,
      exchange: quote.exchange || 'NSE',
      quote: {
        price: quote.regularMarketPrice,
        change: quote.regularMarketChange,
        changePercent: quote.regularMarketChangePercent,
        open: quote.regularMarketOpen,
        high: quote.regularMarketDayHigh,
        low: quote.regularMarketDayLow,
        previousClose: quote.regularMarketPreviousClose,
        volume: quote.regularMarketVolume,
        marketCap: quote.marketCap,
        pe: quote.trailingPE,
        eps: quote.epsTrailingTwelveMonths,
        dividend: quote.dividendRate,
        dividendYield: quote.dividendYield ? quote.dividendYield * 100 : null,
        week52High: quote.fiftyTwoWeekHigh,
        week52Low: quote.fiftyTwoWeekLow,
        avgVolume: quote.averageDailyVolume3Month,
        beta: quote.beta,
      },
      priceHistory: historical.map(item => ({
        date: item.date.toISOString().split('T')[0],
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
        volume: item.volume,
      })),
      financials: {
        ratios: {
          peRatio: quote.trailingPE,
          forwardPE: quote.forwardPE,
          pbRatio: quote.priceToBook,
          pegRatio: quoteSummary?.defaultKeyStatistics?.pegRatio || null,
          debtToEquity: quoteSummary?.financialData?.debtToEquity || null,
          currentRatio: quoteSummary?.financialData?.currentRatio || null,
          quickRatio: quoteSummary?.financialData?.quickRatio || null,
          roe: quoteSummary?.financialData?.returnOnEquity ? quoteSummary.financialData.returnOnEquity * 100 : null,
          roa: quoteSummary?.financialData?.returnOnAssets ? quoteSummary.financialData.returnOnAssets * 100 : null,
          grossMargin: quoteSummary?.financialData?.grossMargins ? quoteSummary.financialData.grossMargins * 100 : null,
          operatingMargin: quoteSummary?.financialData?.operatingMargins ? quoteSummary.financialData.operatingMargins * 100 : null,
          profitMargin: quoteSummary?.financialData?.profitMargins ? quoteSummary.financialData.profitMargins * 100 : null,
          revenueGrowth: quoteSummary?.financialData?.revenueGrowth ? quoteSummary.financialData.revenueGrowth * 100 : null,
          earningsGrowth: quoteSummary?.financialData?.earningsGrowth ? quoteSummary.financialData.earningsGrowth * 100 : null,
        },
        targetPrice: {
          mean: quoteSummary?.financialData?.targetMeanPrice || null,
          high: quoteSummary?.financialData?.targetHighPrice || null,
          low: quoteSummary?.financialData?.targetLowPrice || null,
          recommendation: quoteSummary?.financialData?.recommendationKey || null,
        },
      },
      shareholding: quoteSummary?.majorHoldersBreakdown ? {
        insidersPercent: quoteSummary.majorHoldersBreakdown.insidersPercentHeld ? quoteSummary.majorHoldersBreakdown.insidersPercentHeld * 100 : null,
        institutionsPercent: quoteSummary.majorHoldersBreakdown.institutionsPercentHeld ? quoteSummary.majorHoldersBreakdown.institutionsPercentHeld * 100 : null,
        institutionsFloatPercent: quoteSummary.majorHoldersBreakdown.institutionsFloatPercentHeld ? quoteSummary.majorHoldersBreakdown.institutionsFloatPercentHeld * 100 : null,
      } : null,
      companyInfo: {
        sector: quoteSummary?.assetProfile?.sector || quote.sector || 'N/A',
        industry: quoteSummary?.assetProfile?.industry || quote.industry || 'N/A',
        employees: quoteSummary?.assetProfile?.fullTimeEmployees || null,
        website: quoteSummary?.assetProfile?.website || null,
        description: quoteSummary?.assetProfile?.longBusinessSummary || `${quote.longName || upperSymbol} is listed on ${quote.exchange || 'NSE'}.`,
        address: quoteSummary?.assetProfile?.address1 || null,
        city: quoteSummary?.assetProfile?.city || null,
        country: quoteSummary?.assetProfile?.country || 'India',
      },
    }

    return stockData
  } catch (error) {
    console.error(`Error fetching stock data for ${symbol}:`, error.message)
    throw new Error(`Failed to fetch data for ${symbol}: ${error.message}`)
  }
}

// Search stocks
export async function searchStocks(query) {
  try {
    const results = await yahooFinance.search(query, {
      newsCount: 0,
      quotesCount: 10,
    })

    // Filter to only include Indian stocks (NSE/BSE)
    const indianStocks = results.quotes
      .filter(q => q.exchange === 'NSI' || q.exchange === 'BSE' || q.symbol?.endsWith('.NS') || q.symbol?.endsWith('.BO'))
      .map(q => ({
        symbol: q.symbol?.replace('.NS', '').replace('.BO', '') || q.symbol,
        name: q.longname || q.shortname || q.symbol,
        exchange: q.exchange === 'NSI' ? 'NSE' : q.exchange === 'BSE' ? 'BSE' : 'NSE',
        type: q.quoteType,
      }))

    // If no Indian stocks found, return all equity results
    if (indianStocks.length === 0) {
      return results.quotes
        .filter(q => q.quoteType === 'EQUITY')
        .slice(0, 10)
        .map(q => ({
          symbol: q.symbol,
          name: q.longname || q.shortname || q.symbol,
          exchange: q.exchange,
          type: q.quoteType,
        }))
    }

    return indianStocks
  } catch (error) {
    console.error('Error searching stocks:', error.message)
    
    // Return popular stocks as fallback
    return [
      { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', exchange: 'NSE' },
      { symbol: 'TCS', name: 'Tata Consultancy Services', exchange: 'NSE' },
      { symbol: 'INFY', name: 'Infosys Ltd', exchange: 'NSE' },
      { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', exchange: 'NSE' },
      { symbol: 'ICICIBANK', name: 'ICICI Bank Ltd', exchange: 'NSE' },
    ].filter(s => 
      s.symbol.toLowerCase().includes(query.toLowerCase()) ||
      s.name.toLowerCase().includes(query.toLowerCase())
    )
  }
}

// Get multiple stock quotes for comparison
export async function getMultipleQuotes(symbols) {
  try {
    const yahooSymbols = symbols.map(s => toYahooSymbol(s))
    const quotes = await yahooFinance.quote(yahooSymbols)
    
    return (Array.isArray(quotes) ? quotes : [quotes]).map(q => ({
      symbol: q.symbol?.replace('.NS', '').replace('.BO', ''),
      name: q.longName || q.shortName,
      price: q.regularMarketPrice,
      change: q.regularMarketChange,
      changePercent: q.regularMarketChangePercent,
      pe: q.trailingPE,
      marketCap: q.marketCap,
    }))
  } catch (error) {
    console.error('Error fetching multiple quotes:', error.message)
    throw error
  }
}

export default {
  getStockData,
  searchStocks,
  getMultipleQuotes,
}
