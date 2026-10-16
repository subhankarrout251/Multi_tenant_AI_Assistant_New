import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import { fetchClientInfo } from "../api/chatApi";
import { ChatBubble } from "./ChatBubble";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import AnimatedRobot3D from "./AnimatedRobot3D";

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [clientInfo, setClientInfo] = useState(null);
  const { messages, sendUserMessage, isLoading, error, clearChat } = useChat(clientInfo);
  const [clearedNotice, setClearedNotice] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    fetchClientInfo().then((info) => setClientInfo(info));
  }, []);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleClearChat = async () => {
    if (isLoading) return;
    await clearChat();
    setClearedNotice(true);
    setTimeout(() => setClearedNotice(false), 2500);
  };

  return (
    <>
      {/* Floating toggle button with 3D animated robot */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        aria-label={isOpen ? "Close chat" : "Open chat"}
        title={isOpen ? "Close assistant" : "Chat with assistant"}
        style={{
          position: "fixed",
          bottom: isOpen ? 24 : 16,
          right: isOpen ? 24 : 16,
          width: isOpen ? 52 : "auto",
          height: isOpen ? 52 : "auto",
          borderRadius: isOpen ? "50%" : 0,
          background: isOpen ? "#1A3C5E" : "transparent",
          border: "none",
          outline: "none",
          cursor: "pointer",
          color: "#fff",
          boxShadow: isOpen ? "0 8px 24px rgba(26, 60, 94, 0.4), 0 2px 6px rgba(0,0,0,0.15)" : "none",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 0,
          overflow: "visible",
          transition: "transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = "scale(1.1)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = "scale(1)";
        }}
      >
        {isOpen ? (
          <span style={{ fontSize: 24, fontWeight: "bold", lineHeight: 1 }}>✕</span>
        ) : (
          <AnimatedRobot3D size={74} showShadow={false} interactive={true} />
        )}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <div
          style={{
            position: "fixed",
            bottom: 88,
            right: 24,
            width: 360,
            height: 500,
            borderRadius: 16,
            border: "1px solid #e2e8f0",
            boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            zIndex: 999,
            background: "#fff",
            fontFamily: "system-ui, sans-serif",
          }}
          role="dialog"
          aria-label={clientInfo?.display_name ? `${clientInfo.display_name} chat assistant` : "AI Chat Assistant"}
        >
          {/* Header */}
          <div
            style={{
              background: "#1A3C5E",
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 10,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  position: "relative",
                  background: "transparent",
                }}
              >
                <AnimatedRobot3D size={28} showShadow={false} interactive={false} />
                <div
                  style={{
                    position: "absolute",
                    bottom: -1,
                    right: -1,
                    width: 9,
                    height: 9,
                    borderRadius: "50%",
                    background: "#4ade80",
                    border: "2px solid #1A3C5E",
                  }}
                />
              </div>
              <div style={{ overflow: "hidden" }}>
                <div
                  style={{
                    color: "#fff",
                    fontWeight: 500,
                    fontSize: 14,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {clientInfo?.display_name ? `${clientInfo.display_name} Assistant` : "Crushaders Tech Assistant"}
                </div>
                <div style={{ color: "rgba(255,255,255,0.55)", fontSize: 11 }}>
                  Typically replies instantly
                </div>
              </div>
            </div>

            {/* Header Action Button: Refresh / New Chat */}
            <button
              onClick={handleClearChat}
              title="Start a new chat (clear memory)"
              aria-label="Start new chat"
              disabled={isLoading}
              style={{
                background: "rgba(255,255,255,0.12)",
                border: "none",
                borderRadius: 8,
                width: 28,
                height: 28,
                color: "rgba(255,255,255,0.9)",
                cursor: isLoading ? "not-allowed" : "pointer",
                fontSize: 15,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                lineHeight: 1,
                transition: "background 0.2s ease, transform 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.22)";
                e.currentTarget.style.transform = "rotate(30deg)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.12)";
                e.currentTarget.style.transform = "rotate(0deg)";
              }}
            >
              ↺
            </button>
          </div>

          {/* Cleared notification banner */}
          {clearedNotice && (
            <div
              style={{
                background: "#f0fdf4",
                color: "#166534",
                fontSize: 12,
                padding: "6px 14px",
                borderBottom: "1px solid #bbf7d0",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>✓ Conversation memory cleared. Fresh chat started.</span>
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div
              style={{
                background: "#fef2f2",
                color: "#991b1b",
                fontSize: 12,
                padding: "6px 14px",
                borderBottom: "1px solid #fecaca",
              }}
            >
              {error}
            </div>
          )}

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "14px 14px 0",
              background: "#f8fafc",
            }}
          >
            {messages.map((msg) => (
              <ChatBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <ChatInput onSend={sendUserMessage} disabled={isLoading} />
        </div>
      )}
    </>
  );
}