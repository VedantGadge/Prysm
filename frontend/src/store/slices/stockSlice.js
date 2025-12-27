import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { stockAPI } from '../../services/api'

const initialState = {
  selectedStock: null,
  stockData: null,
  searchResults: [],
  isSearching: false,
  isLoadingStock: false,
  error: null,
  popularStocks: [
    { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', exchange: 'NSE' },
    { symbol: 'TCS', name: 'Tata Consultancy Services', exchange: 'NSE' },
    { symbol: 'INFY', name: 'Infosys Ltd', exchange: 'NSE' },
    { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', exchange: 'NSE' },
    { symbol: 'ICICIBANK', name: 'ICICI Bank Ltd', exchange: 'NSE' },
    { symbol: 'WIPRO', name: 'Wipro Ltd', exchange: 'NSE' },
    { symbol: 'BHARTIARTL', name: 'Bharti Airtel Ltd', exchange: 'NSE' },
    { symbol: 'ITC', name: 'ITC Ltd', exchange: 'NSE' },
    { symbol: 'SBIN', name: 'State Bank of India', exchange: 'NSE' },
    { symbol: 'KOTAKBANK', name: 'Kotak Mahindra Bank', exchange: 'NSE' },
  ],
}

export const fetchStockData = createAsyncThunk(
  'stock/fetchStockData',
  async (symbol, { rejectWithValue }) => {
    try {
      const data = await stockAPI.getStockData(symbol)
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const searchStocks = createAsyncThunk(
  'stock/searchStocks',
  async (query, { rejectWithValue }) => {
    try {
      const results = await stockAPI.searchStocks(query)
      return results
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const stockSlice = createSlice({
  name: 'stock',
  initialState,
  reducers: {
    selectStock: (state, action) => {
      state.selectedStock = action.payload
    },
    clearSelectedStock: (state) => {
      state.selectedStock = null
      state.stockData = null
    },
    clearSearchResults: (state) => {
      state.searchResults = []
    },
    setError: (state, action) => {
      state.error = action.payload
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch stock data
      .addCase(fetchStockData.pending, (state) => {
        state.isLoadingStock = true
        state.error = null
      })
      .addCase(fetchStockData.fulfilled, (state, action) => {
        state.isLoadingStock = false
        state.stockData = action.payload
      })
      .addCase(fetchStockData.rejected, (state, action) => {
        state.isLoadingStock = false
        state.error = action.payload
      })
      // Search stocks
      .addCase(searchStocks.pending, (state) => {
        state.isSearching = true
      })
      .addCase(searchStocks.fulfilled, (state, action) => {
        state.isSearching = false
        state.searchResults = action.payload
      })
      .addCase(searchStocks.rejected, (state, action) => {
        state.isSearching = false
        state.error = action.payload
      })
  },
})

export const {
  selectStock,
  clearSelectedStock,
  clearSearchResults,
  setError,
  clearError,
} = stockSlice.actions

export default stockSlice.reducer
