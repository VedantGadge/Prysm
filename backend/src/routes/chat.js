import express from "express";
import axios from "axios";
import ChatHistory from "../models/ChatHistory.js";

const router = express.Router();

const AI_AGENT_URL = process.env.AI_AGENT_URL || "http://localhost:8001";

// Send message to AI agent and stream response
router.post("/", async (req, res) => {
  const { message, stockSymbol } = req.body;
  // TODO: Get real userId from auth token
  const userId = "default_user_v1";

  if (!message) {
    return res.status(400).json({ error: "Message is required" });
  }

  try {
    // 1. Fetch recent history (Last 10 messages)
    const historyDocs = await ChatHistory.find({ userId })
      .sort({ timestamp: -1 })
      .limit(10);

    // Convert to Gemini format: [{role: 'user'|'model', parts: [{text: '...'}]}, ...]
    const history = historyDocs.reverse().map((doc) => ({
      role: doc.role,
      parts: [{ text: doc.content }],
    }));

    // 2. Save User Message to DB (Async, don't block)
    const userMsgPromise = ChatHistory.create({
      userId,
      role: "user",
      content: message,
    });

    // Set headers for streaming
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");

    // 3. Make request to AI agent
    const response = await axios.post(
      `${AI_AGENT_URL}/chat`,
      {
        message,
        stock_symbol: stockSymbol,
        history: history, // Pass history to Python
      },
      {
        responseType: "stream",
        timeout: 120000,
      }
    );

    // 4. Stream response and accumulate for saving
    let aiResponseText = "";

    response.data.on("data", (chunk) => {
      const chunkStr = chunk.toString();
      res.write(chunkStr);

      // Parse chunk to extract text for DB
      try {
        const lines = chunkStr.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (dataStr !== "[DONE]") {
              const data = JSON.parse(dataStr);
              if (data.content) {
                aiResponseText += data.content;
              }
            }
          }
        }
      } catch (e) {
        // Ignore parse errors on partial chunks
      }
    });

    response.data.on("end", async () => {
      res.write("data: [DONE]\n\n");
      res.end();

      // 5. Save AI Response to DB
      await userMsgPromise; // Ensure user msg is saved first (optional but good)
      if (aiResponseText) {
        await ChatHistory.create({
          userId,
          role: "model",
          content: aiResponseText,
        });
      }
    });

    response.data.on("error", (error) => {
      console.error("Stream error:", error);
      res.write(`data: {"error": "Stream error"}\n\n`);
      res.end();
    });
  } catch (error) {
    console.error("Chat API error:", error.message);
    if (!res.headersSent) {
      res.status(500).json({ error: "Failed to process chat" });
    } else {
      res.end();
    }
  }
});

export default router;
