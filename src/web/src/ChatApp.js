import React, { useState, useRef, useEffect } from "react";

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
  const chatEndRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_HOST}/hrpolicy/agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: input, session_id: sessionId }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { sender: "agent", text: data.content || "(no response)" },
      ]);
    } catch (error) {
      console.error("Error talking to agent:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "agent", text: "⚠️ Error connecting to agent" },
      ]);
    }

    setInput("");
  };

  // Scroll to bottom when messages update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div style={styles.container}>
      <div style={styles.chatBox}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              ...styles.message,
              alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
              backgroundColor: msg.sender === "user" ? "#0078D4" : "#E5E5EA",
              color: msg.sender === "user" ? "#fff" : "#323130",
            }}
          >
            {msg.text}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <div style={styles.inputRow}>
        <input
          type="text"
          value={input}
          placeholder="Ask about HR policies..."
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
    width: "90%",             
    maxWidth: "900px",        
    margin: "0 auto",      
    border: "1px solid #ccc",
    borderRadius: "15px",
    display: "flex",
    flexDirection: "column",
    height: "70vh",           
    backgroundColor: "#fff",
    boxShadow: "0 8px 20px rgba(0,0,0,0.1)",
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
    maxWidth: "80%",
    fontSize: "0.95rem",
    lineHeight: 1.4,
  },
  inputRow: {
    display: "flex",
    padding: "0.75rem",
    borderTop: "1px solid #ddd",
  },
  input: {
    flex: 1,
    padding: "0.75rem",
    border: "1px solid #ccc",
    borderRadius: "10px",
    marginRight: "0.5rem",
    fontSize: "1rem",
  },
  button: {
    padding: "0.75rem 1.25rem",
    backgroundColor: "#0078D4",
    color: "white",
    border: "none",
    borderRadius: "10px",
    cursor: "pointer",
    fontWeight: "600",
    fontSize: "1rem",
  },
};

export default ChatApp;
