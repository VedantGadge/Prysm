import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { ChevronDown, Building2, X } from 'lucide-react'
import { selectStock, clearSelectedStock } from '../../store/slices/stockSlice'
import StockSelectorDropdown from './StockSelectorDropdown'

function StockSelector() {
  const dispatch = useDispatch()
  const { selectedStock } = useSelector((state) => state.stock)
  const [showDropdown, setShowDropdown] = useState(false)

  const handleSelect = (stock) => {
    dispatch(selectStock(stock))
    setShowDropdown(false)
  }

  const handleClear = (e) => {
    e.stopPropagation()
    dispatch(clearSelectedStock())
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
          selectedStock
            ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
            : 'bg-dark-800 hover:bg-dark-700 text-dark-300 border border-dark-700'
        }`}
      >
        <Building2 size={16} />
        <span className="text-sm font-medium">
          {selectedStock ? selectedStock.symbol : 'Select Stock'}
        </span>
        {selectedStock ? (
          <button
            onClick={handleClear}
            className="ml-1 p-0.5 hover:bg-dark-600 rounded"
          >
            <X size={14} />
          </button>
        ) : (
          <ChevronDown size={14} />
        )}
      </button>

      {showDropdown && (
        <StockSelectorDropdown
          onSelect={handleSelect}
          onClose={() => setShowDropdown(false)}
        />
      )}
    </div>
  )
}

export default StockSelector
