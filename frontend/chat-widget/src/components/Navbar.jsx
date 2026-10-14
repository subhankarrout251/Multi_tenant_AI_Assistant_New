import { NavLink } from "react-router-dom";
import { SparklesIcon, ChatIcon, UploadIcon } from "./Icons";
import "./Navbar.css";

export function Navbar({ activeClientName }) {
  return (
    <header className="site-navbar">
      <div className="navbar-inner">
        <div className="navbar-brand">
          <span className="navbar-logo">
            <SparklesIcon size={18} />
          </span>
          <div className="brand-text">
            <span className="brand-title">Multi-Tenant Assistant</span>
            <span className="brand-badge">Enterprise RAG</span>
          </div>
        </div>

        <nav className="navbar-links">
          <NavLink
            to="/"
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            end
          >
            <ChatIcon size={16} />
            <span>Live Chat Preview</span>
          </NavLink>
          <NavLink
            to="/upload"
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <UploadIcon size={16} />
            <span>Upload & Update Form</span>
          </NavLink>
        </nav>

        <div className="navbar-actions">
          <div className="nav-active-badge" title="Currently responding client in the chat widget">
            <span className="nav-pulse-dot"></span>
            <span className="nav-active-label">Active:</span>
            <strong>{activeClientName || "Crushaders Tech"}</strong>
          </div>
        </div>
      </div>
    </header>
  );
}
