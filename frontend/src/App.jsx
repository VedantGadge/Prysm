import { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import Sidebar from './components/Sidebar/Sidebar'
import ChatContainer from './components/Chat/ChatContainer'
import Header from './components/Header/Header'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const selectedStock = useSelector((state) => state.stock.selectedStock)

  return (
    <div className="flex h-screen bg-dark-900 overflow-hidden">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header 
          sidebarOpen={sidebarOpen} 
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} 
        />
        <main className="flex-1 overflow-hidden">
          <ChatContainer />
        </main>
      </div>
    </div>
  )
}

export default App
