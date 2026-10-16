const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

let cachedClientInfo = null;

export function invalidateClientInfoCache() {
  cachedClientInfo = null;
}

export async function fetchClientInfo(forceRefresh = false) {
  if (cachedClientInfo && !forceRefresh) {
    return cachedClientInfo;
  }
  try {
    const response = await fetch(`${BASE_URL}/api/v1/info`);
    if (response.ok) {
      cachedClientInfo = await response.json();
      return cachedClientInfo;
    }
  } catch (err) {
    console.warn("Could not fetch active client info from backend:", err);
  }

  cachedClientInfo = {
    website_id: import.meta.env.VITE_WEBSITE_ID ?? "crushaders_tech",
    display_name: "AI Assistant",
  };
  return cachedClientInfo;
}

export async function sendMessage(message, sessionId) {
  if (!cachedClientInfo) {
    await fetchClientInfo();
  }
  const websiteId =
    cachedClientInfo?.website_id ??
    (import.meta.env.VITE_WEBSITE_ID ?? "crushaders_tech");

  const response = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      website_id: websiteId,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json(); // { reply: string, sources: string[] }
}

export async function clearChatHistory(sessionId) {
  if (!sessionId) return;
  try {
    const response = await fetch(`${BASE_URL}/api/v1/chat/clear`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    return response.ok;
  } catch (err) {
    console.warn("Could not clear session history on backend:", err);
    return false;
  }
}

export async function fetchChatHistory(sessionId) {
  if (!sessionId) return [];
  try {
    const response = await fetch(`${BASE_URL}/api/v1/chat/history/${encodeURIComponent(sessionId)}`);
    if (response.ok) {
      const data = await response.json();
      return data.messages || [];
    }
  } catch (err) {
    console.warn("Could not fetch chat history from backend:", err);
  }
  return [];
}
