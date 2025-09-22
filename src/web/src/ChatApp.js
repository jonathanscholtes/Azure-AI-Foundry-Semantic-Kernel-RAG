import React, { useState } from "react";

function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0,
      v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const ChatApp = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => generateUUID());

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to chat
    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_HOST}/hrpolicy/agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: input, session_id: sessionId }),
      });

      const data = await response.json();

      const agentMessage = {
        sender: "agent",
        text: data.content || "(no response)",
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error("Error talking to agent:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "agent", text: "⚠️ Error connecting to agent" },
      ]);
    }

    setInput("");
  };

  return (
    <div className="chat-container" style={styles.container}>
      <div style={styles.chatBox}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              ...styles.message,
              alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
              backgroundColor: msg.sender === "user" ? "#007bff" : "#e5e5ea",
              color: msg.sender === "user" ? "white" : "black",
            }}
          >
            {msg.text}
          </div>
        ))}
      </div>
      <div style={styles.inputRow}>
        <input
          type="text"
          value={input}
          placeholder="Type your message..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          style={styles.input}
        />
        <button onClick={sendMessage} style={styles.button}>
          Send
        </button>
      </div>
    </div>
  );
};

const styles = {
  container: {
    maxWidth: "600px",
    margin: "2rem auto",
    border: "1px solid #ccc",
    borderRadius: "10px",
    display: "flex",
    flexDirection: "column",
    height: "80vh",
  },
  chatBox: {
    flex: 1,
    padding: "1rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    overflowY: "auto",
  },
  message: {
    padding: "0.75rem 1rem",
    borderRadius: "20px",
    maxWidth: "75%",
  },
  inputRow: {
    display: "flex",
    padding: "0.5rem",
    borderTop: "1px solid #ddd",
  },
  input: {
    flex: 1,
    padding: "0.75rem",
    border: "1px solid #ccc",
    borderRadius: "5px",
    marginRight: "0.5rem",
  },
  button: {
    padding: "0.75rem 1.25rem",
    backgroundColor: "#007bff",
    color: "white",
    border: "none",
    borderRadius: "5px",
    cursor: "pointer",
  },
};

export default ChatApp;
