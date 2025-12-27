import express from 'express'
import { getStockData, searchStocks } from '../services/stockService.js'

const router = express.Router()

// Search stocks
router.get('/search', async (req, res) => {
  const { q } = req.query

  if (!q) {
    return res.status(400).json({ error: 'Search query is required' })
  }

  try {
    const results = await searchStocks(q)
    res.json(results)
  } catch (error) {
    console.error('Stock search error:', error)
    res.status(500).json({ 
      error: 'Failed to search stocks',
      message: error.message 
    })
  }
})

// Get stock data
router.get('/:symbol', async (req, res) => {
  const { symbol } = req.params

  try {
    const data = await getStockData(symbol)
    res.json(data)
  } catch (error) {
    console.error('Stock data error:', error)
    res.status(500).json({ 
      error: 'Failed to fetch stock data',
      message: error.message 
    })
  }
})

export default router
