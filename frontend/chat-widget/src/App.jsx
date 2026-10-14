import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AdminPortal } from "./components/AdminPortal";
import { ChatWidget } from "./components/ChatWidget";
import { invalidateClientInfoCache } from "./api/chatApi";

export default function App() {
  const [chatKey, setChatKey] = useState(0);

  const handleClientChanged = () => {
    // Invalidate client cache and trigger re-render of ChatWidget
    invalidateClientInfoCache();
    setChatKey((k) => k + 1);
  };

  return (
    <BrowserRouter>
      <div style={{ minHeight: "100vh", background: "#f8fafc" }}>
        <Routes>
          {/* First page (/): Nothing shown except the chatbot */}
          <Route path="/" element={<div style={{ minHeight: "100vh" }} />} />

          {/* /upload route: All forms, document upload, and update settings */}
          <Route
            path="/upload"
            element={<AdminPortal onClientChanged={handleClientChanged} />}
          />
          <Route path="/admin" element={<Navigate to="/upload" replace />} />

          {/* Fallback to first page */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {/* Chatbot is always present */}
        <ChatWidget key={chatKey} />
      </div>
    </BrowserRouter>
  );
}