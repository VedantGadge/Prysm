import { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { 
  Search, 
  Menu, 
  Sun, 
  Moon, 
  Bell,
  Eye,
  Command
} from 'lucide-react'
import StockSelector from '../StockSelector/StockSelector'

function Header({ sidebarOpen, onToggleSidebar }) {
  const selectedStock = useSelector((state) => state.stock.selectedStock)
  const [showSearch, setShowSearch] = useState(false)

  return (
    <header className="h-14 bg-dark-900 border-b border-dark-700 flex items-center justify-between px-4 flex-shrink-0">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {!sidebarOpen && (
          <button
            onClick={onToggleSidebar}
            className="p-2 hover:bg-dark-800 rounded-lg transition-colors"
            aria-label="Open sidebar"
          >
            <Menu size={20} className="text-dark-400" />
          </button>
        )}

        {/* Logo when sidebar is closed */}
        {!sidebarOpen && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">P</span>
            </div>
            <span className="font-semibold text-dark-100">Prysm</span>
            <span className="px-1.5 py-0.5 bg-primary-500/20 text-primary-400 text-xs rounded font-medium">
              Pro
            </span>
          </div>
        )}

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-1 ml-4">
          {['Screener', 'Pulse', 'Discovery', 'Portfolio', 'Analyze'].map((item) => (
            <button
              key={item}
              className="px-3 py-1.5 text-sm text-dark-400 hover:text-dark-100 hover:bg-dark-800 rounded-lg transition-colors"
            >
              {item}
              {item === 'Portfolio' && <span className="ml-1">✨</span>}
            </button>
          ))}
        </nav>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative hidden sm:block">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-800 border border-dark-700 rounded-lg text-sm text-dark-400 min-w-[200px]">
            <Search size={16} />
            <span>Search your favourite</span>
            <div className="flex items-center gap-1 ml-auto text-xs">
              <kbd className="px-1.5 py-0.5 bg-dark-700 rounded text-dark-300">Ctrl</kbd>
              <span>+</span>
              <kbd className="px-1.5 py-0.5 bg-dark-700 rounded text-dark-300">K</kbd>
            </div>
          </div>
        </div>

        {/* Theme Toggle */}
        <button className="p-2 hover:bg-dark-800 rounded-lg transition-colors">
          <Sun size={18} className="text-dark-400" />
        </button>

        {/* Watchlist */}
        <button className="flex items-center gap-2 px-3 py-1.5 bg-dark-800 hover:bg-dark-700 border border-dark-700 rounded-lg transition-colors">
          <Eye size={16} className="text-dark-400" />
          <span className="text-sm text-dark-300">Watchlist</span>
        </button>

        {/* User Avatar */}
        <button className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-medium text-sm">
          V
        </button>
      </div>
    </header>
  )
}

export default Header
