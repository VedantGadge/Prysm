import express from "express";
import axios from "axios";

const router = express.Router();

const AI_AGENT_URL = process.env.AI_AGENT_URL || "http://localhost:8001";

// GET /api/sessions
router.get("/", async (req, res) => {
  try {
    const response = await axios.get(`${AI_AGENT_URL}/sessions`);
    res.json(response.data);
  } catch (error) {
    console.error("Error fetching sessions:", error.message);
    res.status(500).json({ error: "Failed to fetch sessions" });
  }
});

// POST /api/sessions
router.post("/", async (req, res) => {
  try {
    const response = await axios.post(`${AI_AGENT_URL}/sessions`);
    res.json(response.data);
  } catch (error) {
    console.error("Error creating session:", error.message);
    res.status(500).json({ error: "Failed to create session" });
  }
});

// GET /api/sessions/:id
router.get("/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const response = await axios.get(`${AI_AGENT_URL}/sessions/${id}`);
    res.json(response.data);
  } catch (error) {
    console.error(`Error fetching session ${req.params.id}:`, error.message);
    res.status(500).json({ error: "Failed to fetch session" });
  }
});

export default router;
