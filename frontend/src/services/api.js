import axios from "axios";

const API_BASE_URL = "/api";

// API service for chat
export const chatAPI = {
  uploadDocument: async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    // Direct call to Agent URL (8001) for File Upload (bypassing Node gateway for simplicity as Node just proxies)
    // Or we can add a route in Node. Let's assume Node gateway is set or we hit Agent directly.
    // For this prototype, we'll hit Agent direct if CORS allows, or add a proxy in Node.
    // Let's assume we use the gateway prefix /api/agent if setup, but current setup is /api/chat -> Node -> Agent.
    // To keep it clean, we should add a route in Node.
    // BUT for speed: let's try direct to Agent 8001 if possible, else we update Node.
    // Actually, looking at the setup, 8001 is where the RAG endpoint lives.

    // Let's use fetching to localhost:8001 directly for the prototype to avoid editing Node.
    const response = await fetch("http://localhost:8001/upload_doc", {
      method: "POST",
      body: formData,
    });
    return response.json();
  },

  getSessions: async () => {
    const response = await axios.get(`${API_BASE_URL}/sessions`);
    return response.data;
  },

  createSession: async () => {
    const response = await axios.post(`${API_BASE_URL}/sessions`);
    return response.data;
  },

  getSession: async (sessionId) => {
    const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}`);
    return response.data;
  },

  sendMessage: async (message, stockSymbol, mode, profile, sessionId, onChunk) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          stockSymbol,
          mode,
          profile,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response from server");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              break;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullContent += parsed.content;
                onChunk(parsed.content);
              }
            } catch (e) {
              // Not JSON, might be plain text chunk
              if (data.trim()) {
                fullContent += data;
                onChunk(data);
              }
            }
          }
        }
      }

      return fullContent;
    } catch (error) {
      console.error("Chat API error:", error);
      throw error;
    }
  },
};

// API service for stock data
export const stockAPI = {
  getStockData: async (symbol) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stock/${symbol}`);
      return response.data;
    } catch (error) {
      console.error("Stock API error:", error);
      throw error;
    }
  },

  searchStocks: async (query) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stock/search`, {
        params: { q: query },
      });
      return response.data;
    } catch (error) {
      console.error("Stock search error:", error);
      throw error;
    }
  },
};

export default {
  chatAPI,
  stockAPI,
};
