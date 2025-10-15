import React, { useState, useRef, useEffect } from "react";
import parse from "html-react-parser";
import { ThumbsUp, ThumbsDown } from "lucide-react";

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
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_HOST}/hrpolicy/agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: input, session_id: sessionId }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: data.content || "(no response)",
          references: data.references || [],
          feedback: null,
          response_id: data.response_id || null,
        },
      ]);
    } catch (error) {
      console.error("Error talking to agent:", error);
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: "⚠️ Error connecting to agent",
          feedback: null,
          response_id: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (index, value) => {
    setMessages((prev) =>
      prev.map((msg, i) =>
        i === index
          ? { ...msg, feedback: msg.feedback === value ? null : value }
          : msg
      )
    );

    const message = messages[index];
    if (!message?.response_id) return;

    try {
      await fetch(`${process.env.REACT_APP_API_HOST}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          response_id: message.response_id,
          feedback: value,
        }),
      });
    } catch (error) {
      console.error("Error sending feedback:", error);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div style={styles.container}>
      <div style={styles.chatBox}>
        {messages.map((msg, idx) => (
          <ChatMessage
            key={idx}
            msg={msg}
            idx={idx}
            handleFeedback={handleFeedback}
          />
        ))}

        {loading && (
          <div
            style={{
              ...styles.message,
              alignSelf: "flex-start",
              backgroundColor: "#f0f0f0",
              color: "#333",
            }}
          >
            <div style={styles.spinnerContainer}>
              <div style={styles.spinner}></div>
              <span style={{ marginLeft: "10px" }}>Agent is thinking...</span>
            </div>
          </div>
        )}

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
          disabled={loading}
        />
        <button onClick={sendMessage} style={styles.button} disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
};

const ChatMessage = ({ msg, idx, handleFeedback }) => {
  const [showRefs, setShowRefs] = useState(false);

  return (
    <div
      style={{
        ...styles.message,
        alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
        backgroundColor: msg.sender === "user" ? "#1A719E" : "#AAE09D",
        color: msg.sender === "user" ? "#fff" : "#323130",
      }}
    >
      {parse(msg.text)}

      {msg.sender === "agent" && (
        <>
          <div style={styles.feedbackRow}>
            <button
              style={{
                ...styles.feedbackButton,
                ...(msg.feedback === "up" ? styles.feedbackSelectedUp : {}),
              }}
              onClick={() => handleFeedback(idx, "up")}
              title="Helpful"
            >
              <ThumbsUp size={18} />
            </button>
            <button
              style={{
                ...styles.feedbackButton,
                ...(msg.feedback === "down" ? styles.feedbackSelectedDown : {}),
              }}
              onClick={() => handleFeedback(idx, "down")}
              title="Not helpful"
            >
              <ThumbsDown size={18} />
            </button>
          </div>

          {msg.references && msg.references.length > 0 && (
            <div style={styles.referencesBox}>
              <button
                onClick={() => setShowRefs(!showRefs)}
                style={styles.toggleButton}
              >
                {showRefs ? "Hide Sources ▲" : "Show Sources ▼"}
              </button>
              {showRefs && (
                <ul style={styles.referencesList}>
                  {msg.references.map((ref, i) => (
                    <li key={i}>{ref}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
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
    position: "relative",
  },
  feedbackRow: {
    marginTop: "0.25rem",
    display: "flex",
    gap: "0.5rem",
  },
  feedbackButton: {
    background: "transparent",
    border: "1px solid transparent",
    borderRadius: "50%",
    padding: "6px",
    cursor: "pointer",
    color: "#888",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.2s ease",
  },
  feedbackSelectedUp: {
    backgroundColor: "#E5F3FF",
    borderColor: "#0078D4",
    color: "#0078D4",
  },
  feedbackSelectedDown: {
    backgroundColor: "#FDE7E9",
    borderColor: "#d13438",
    color: "#d13438",
  },
  referencesBox: {
    marginTop: "0.5rem",
    backgroundColor: "#f7f7f7",
    borderRadius: "10px",
    padding: "0.5rem 0.75rem",
    fontSize: "0.85rem",
    color: "#444",
  },
  referencesList: {
    margin: "0.25rem 0 0 1rem",
    padding: 0,
    listStyleType: "disc",
  },
  toggleButton: {
    background: "none",
    border: "none",
    color: "#0078D4",
    cursor: "pointer",
    fontSize: "0.85rem",
    fontWeight: 500,
    padding: 0,
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
  spinnerContainer: {
    display: "flex",
    alignItems: "center",
  },
  spinner: {
    width: "18px",
    height: "18px",
    border: "3px solid #ccc",
    borderTop: "3px solid #0078D4",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
};

// inject spinner keyframes
const styleSheet = document.styleSheets[0];
if (styleSheet) {
  styleSheet.insertRule(
    `@keyframes spin { 
      0% { transform: rotate(0deg); } 
      100% { transform: rotate(360deg); } 
    }`,
    styleSheet.cssRules.length
  );
}

export default ChatApp;
