import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { chatAPI } from "../../services/api";

const initialState = {
  messages: [],
  isLoading: false,
  isStreaming: false,
  currentStreamingId: null,
  error: null,
  conversationHistory: [],
  currentSessionId: null,
  sessionList: [],
  isSessionLoading: false,
};

// Simple ID generator
function generateId() {
  return "msg_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
}

// --- Session Thunks ---

export const loadSessions = createAsyncThunk(
  "chat/loadSessions",
  async (_, { rejectWithValue }) => {
    try {
      return await chatAPI.getSessions();
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const createNewSession = createAsyncThunk(
  "chat/createNewSession",
  async (_, { dispatch, rejectWithValue }) => {
    try {
      const session = await chatAPI.createSession();
      dispatch(clearChat());
      return session;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const selectSession = createAsyncThunk(
  "chat/selectSession",
  async (sessionId, { dispatch, rejectWithValue }) => {
    try {
      dispatch(clearChat());
      const sessionData = await chatAPI.getSession(sessionId);

      // Map backend messages to frontend format
      const snapshotMessages = (sessionData.snapshots || []).map((snap) => ({
        id: "snap_" + Math.random().toString(36).substr(2, 9),
        type: "ai",
        content: `Daily summary (${snap.date}):\n${snap.summary}`,
        timestamp: new Date().toISOString(),
        isComplete: true,
      }));

      const mappedMessages = (sessionData.messages || []).map((msg) => ({
        id: "hist_" + Math.random().toString(36).substr(2, 9),
        type: msg.role === "model" ? "ai" : "user",
        content: msg.parts[0].text,
        timestamp: new Date().toISOString(), // Fallback
        isComplete: true,
      }));

      return { sessionId, messages: [...snapshotMessages, ...mappedMessages], title: sessionData.title };
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async ({ message, stockSymbol, mode, profile }, { dispatch, getState, rejectWithValue }) => {
    const userMessageId = generateId();
    const aiMessageId = generateId();
    let sessionId = getState().chat.currentSessionId;

    // AUTO-CREATE SESSION IF NONE EXISTS
    if (!sessionId) {
      try {
        const newSession = await chatAPI.createSession();
        sessionId = newSession.id || newSession._id;
        dispatch(chatSlice.actions.setCurrentSessionId(sessionId));
      } catch (e) {
        console.error("Failed to create session:", e);
      }
    }

    // Add user message immediately
    dispatch(addUserMessage({ id: userMessageId, content: message }));

    // Add placeholder AI message
    dispatch(addAIMessage({ id: aiMessageId, content: "", isLoading: true }));

    try {
      // Start streaming
      dispatch(setStreaming({ isStreaming: true, messageId: aiMessageId }));

      const response = await chatAPI.sendMessage(
        message,
        stockSymbol,
        mode,
        profile,
        sessionId, // Pass session ID
        (chunk) => {
          dispatch(updateStreamingMessage({ id: aiMessageId, chunk }));
        }
      );

      // Finalize the message
      dispatch(finalizeMessage({ id: aiMessageId, content: response }));
      dispatch(setStreaming({ isStreaming: false, messageId: null }));

      // Refresh session list to update titles/previews if this was a new chat
      dispatch(loadSessions());

      return { userMessageId, aiMessageId, response };
    } catch (error) {
      dispatch(setError(error.message || "Failed to get response"));
      dispatch(removeMessage(aiMessageId));
      dispatch(setStreaming({ isStreaming: false, messageId: null }));
      return rejectWithValue(error.message);
    }
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addUserMessage: (state, action) => {
      state.messages.push({
        id: action.payload.id,
        type: "user",
        content: action.payload.content,
        timestamp: new Date().toISOString(),
      });
    },
    addAIMessage: (state, action) => {
      state.messages.push({
        id: action.payload.id,
        type: "ai",
        content: action.payload.content,
        timestamp: new Date().toISOString(),
        isLoading: action.payload.isLoading || false,
        charts: [],
      });
    },
    updateStreamingMessage: (state, action) => {
      const message = state.messages.find((m) => m.id === action.payload.id);
      if (message) {
        message.content += action.payload.chunk;
        // Keep isLoading true while streaming
        message.isLoading = true;
      }
    },
    finalizeMessage: (state, action) => {
      const message = state.messages.find((m) => m.id === action.payload.id);
      if (message) {
        message.content = action.payload.content;
        message.isLoading = false;
        message.isComplete = true;
      }
    },
    removeMessage: (state, action) => {
      state.messages = state.messages.filter((m) => m.id !== action.payload);
    },
    setStreaming: (state, action) => {
      state.isStreaming = action.payload.isStreaming;
      state.currentStreamingId = action.payload.messageId;
    },
    setError: (state, action) => {
      state.error = action.payload;
      state.isLoading = false;
    },
    clearError: (state) => {
      state.error = null;
    },
    clearChat: (state) => {
      state.messages = [];
      state.error = null;
      state.isLoading = false;
      state.isStreaming = false;
      state.currentStreamingId = null;
    },
    setCurrentSessionId: (state, action) => {
      state.currentSessionId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state) => {
        state.isLoading = false;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Something went wrong";
      })
      // Session reducers
      .addCase(loadSessions.fulfilled, (state, action) => {
        state.sessionList = action.payload;
      })
      .addCase(createNewSession.fulfilled, (state, action) => {
        state.currentSessionId = action.payload.id;
        // Add to list immediately
        state.sessionList.unshift(action.payload);
      })
      .addCase(selectSession.fulfilled, (state, action) => {
        state.currentSessionId = action.payload.sessionId;
        state.messages = action.payload.messages;
      });
  },
});

export const {
  addUserMessage,
  addAIMessage,
  updateStreamingMessage,
  finalizeMessage,
  removeMessage,
  setStreaming,
  setError,
  clearError,
  clearChat,
} = chatSlice.actions;

export default chatSlice.reducer;
