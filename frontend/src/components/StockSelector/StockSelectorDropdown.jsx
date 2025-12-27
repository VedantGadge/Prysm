import { useState } from 'react'
import { useSelector } from 'react-redux'
import { Search, TrendingUp, Building2 } from 'lucide-react'

function StockSelectorDropdown({ onSelect, onClose }) {
  const { popularStocks } = useSelector((state) => state.stock)
  const [searchQuery, setSearchQuery] = useState('')

  const filteredStocks = popularStocks.filter(
    (stock) =>
      stock.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stock.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="absolute bottom-full left-0 mb-2 w-80 bg-dark-800 border border-dark-700 rounded-xl shadow-xl z-50 animate-fade-in overflow-hidden">
      {/* Search Input */}
      <div className="p-3 border-b border-dark-700">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search stocks..."
            className="w-full bg-dark-700 border border-dark-600 rounded-lg pl-10 pr-4 py-2 text-sm text-dark-100 placeholder-dark-500 focus:outline-none focus:border-primary-500"
            autoFocus
          />
        </div>
      </div>

      {/* Stock List */}
      <div className="max-h-64 overflow-y-auto">
        {filteredStocks.length > 0 ? (
          <div className="py-2">
            {filteredStocks.map((stock) => (
              <button
                key={stock.symbol}
                onClick={() => onSelect(stock)}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-dark-700 transition-colors text-left"
              >
                <div className="w-8 h-8 bg-dark-600 rounded-lg flex items-center justify-center">
                  <Building2 size={16} className="text-dark-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-dark-100 text-sm">{stock.symbol}</span>
                    <span className="text-xs text-dark-500">{stock.exchange}</span>
                  </div>
                  <p className="text-xs text-dark-400 truncate">{stock.name}</p>
                </div>
                <TrendingUp size={14} className="text-primary-400" />
              </button>
            ))}
          </div>
        ) : (
          <div className="p-4 text-center text-dark-500 text-sm">
            No stocks found
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="p-3 border-t border-dark-700 bg-dark-800/50">
        <p className="text-xs text-dark-500">
          Popular: RELIANCE, TCS, INFY, HDFCBANK
        </p>
      </div>
    </div>
  )
}

export default StockSelectorDropdown
