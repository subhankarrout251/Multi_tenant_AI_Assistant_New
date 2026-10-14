import { useState, useCallback, useRef, useEffect } from "react";
import { sendMessage, clearChatHistory } from "../api/chatApi";

const SESSION_STORAGE_KEY_ID = "ai_assistant_chat_session_id";
const SESSION_STORAGE_KEY_MSGS = "ai_assistant_chat_messages";
const SESSION_STORAGE_KEY_TENANT = "ai_assistant_chat_tenant_id";

// Simple unique ID generator
const uid = () => `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

function getInitialSessionId() {
  try {
    const saved = sessionStorage.getItem(SESSION_STORAGE_KEY_ID);
    if (saved && saved.startsWith("sess-")) {
      return saved;
    }
  } catch {
    // sessionStorage unavailable
  }
  const newId = `sess-${Date.now()}`;
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY_ID, newId);
  } catch {}
  return newId;
}

function getDefaultWelcomeMessage(displayName) {
  const name = displayName ? `${displayName}` : "AI";
  return {
    id: "welcome",
    role: "bot",
    text: `Hi! I'm the ${name} assistant. How can I help you today?`,
  };
}

export function useChat(clientInfo = null) {
  const sessionId = useRef(getInitialSessionId());

  const [messages, setMessages] = useState(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_STORAGE_KEY_MSGS);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch {}
    return [getDefaultWelcomeMessage(clientInfo?.display_name)];
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // When clientInfo changes and only welcome message exists, update welcome message
  useEffect(() => {
    if (clientInfo?.display_name) {
      setMessages((prev) => {
        if (prev.length === 1 && prev[0].id === "welcome") {
          return [getDefaultWelcomeMessage(clientInfo.display_name)];
        }
        return prev;
      });
    }
  }, [clientInfo?.display_name]);

  // A tenant switch must begin a fresh browser and server conversation.
  // Otherwise a shared browser could display a previous client's messages.
  useEffect(() => {
    const websiteId = clientInfo?.website_id;
    if (!websiteId) return;

    try {
      const storedWebsiteId = sessionStorage.getItem(SESSION_STORAGE_KEY_TENANT);
      if (storedWebsiteId !== websiteId) {
        const newSessionId = `sess-${Date.now()}`;
        sessionId.current = newSessionId;
        sessionStorage.setItem(SESSION_STORAGE_KEY_ID, newSessionId);
        sessionStorage.removeItem(SESSION_STORAGE_KEY_MSGS);
        setMessages([getDefaultWelcomeMessage(clientInfo.display_name)]);
        setError(null);
      }
      sessionStorage.setItem(SESSION_STORAGE_KEY_TENANT, websiteId);
    } catch {
      // sessionStorage unavailable; backend tenant isolation still applies.
    }
  }, [clientInfo?.website_id, clientInfo?.display_name]);

  // Persist messages in sessionStorage
  useEffect(() => {
    try {
      sessionStorage.setItem(SESSION_STORAGE_KEY_MSGS, JSON.stringify(messages));
    } catch {}
  }, [messages]);

  const sendUserMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    setError(null);

    // Add user message immediately
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", text: trimmed },
    ]);
    setIsLoading(true);

    try {
      const data = await sendMessage(trimmed, sessionId.current);
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "bot", text: data.reply },
      ]);
    } catch {
      setError("Could not reach the server. Is the backend running?");
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "bot",
          text: "Sorry, I couldn't connect to the server right now. Please try again shortly.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearChat = useCallback(async () => {
    const oldSessionId = sessionId.current;
    const newSessionId = `sess-${Date.now()}`;
    sessionId.current = newSessionId;

    try {
      sessionStorage.setItem(SESSION_STORAGE_KEY_ID, newSessionId);
      sessionStorage.removeItem(SESSION_STORAGE_KEY_MSGS);
    } catch {}

    setMessages([getDefaultWelcomeMessage(clientInfo?.display_name)]);
    setError(null);

    // Asynchronously notify backend to clear old session memory
    if (oldSessionId) {
      clearChatHistory(oldSessionId);
    }
  }, [clientInfo?.display_name]);

  return { messages, sendUserMessage, isLoading, error, clearChat, sessionId: sessionId.current };
}
