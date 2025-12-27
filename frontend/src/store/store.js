import { configureStore } from '@reduxjs/toolkit'
import chatReducer from './slices/chatSlice'
import stockReducer from './slices/stockSlice'

export const store = configureStore({
  reducer: {
    chat: chatReducer,
    stock: stockReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
})
