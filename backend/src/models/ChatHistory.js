import mongoose from "mongoose";

const chatHistorySchema = mongoose.Schema(
  {
    userId: {
      type: String,
      required: true,
      index: true,
    },
    role: {
      type: String,
      required: true,
      enum: ["user", "model"],
    },
    content: {
      type: String,
      required: true,
    },
    timestamp: {
      type: Date,
      default: Date.now,
    },
  },
  {
    timestamps: true,
  }
);

const ChatHistory = mongoose.model("ChatHistory", chatHistorySchema);

export default ChatHistory;
