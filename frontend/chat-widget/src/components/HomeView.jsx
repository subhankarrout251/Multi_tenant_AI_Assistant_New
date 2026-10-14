import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { fetchClientInfo } from "../api/chatApi";
import {
  UploadIcon,
  GlobeIcon,
  BuildingIcon,
  TagIcon,
  KeyIcon,
  PhoneIcon,
  MailIcon,
  LocationIcon,
  ChatIcon,
} from "./Icons";
import "./HomeView.css";

export function HomeView() {
  const [clientInfo, setClientInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchClientInfo(true).then((info) => {
      setClientInfo(info);
      setLoading(false);
    });
  }, []);

  return (
    <div className="home-container">
      {/* Hero Section */}
      <section className="home-hero">
        <div className="hero-tag">Live Multi-Tenant Chatbot Demonstration</div>
        <h1 className="hero-title">
          {loading ? "Loading Client Assistant..." : clientInfo?.display_name || "Enterprise AI Assistant"}
        </h1>
        <p className="hero-desc">
          This AI assistant is powered by RAG (Retrieval-Augmented Generation) grounded strictly in PDF and Word (.docx) documents uploaded for this business.
        </p>

        <div className="hero-buttons">
          <Link to="/upload" className="btn-hero-primary">
            <UploadIcon size={16} />
            <span>Open /upload Form & Knowledge Manager</span>
          </Link>
          <a
            href={clientInfo?.base_url && !clientInfo.base_url.includes("documents") ? clientInfo.base_url : "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-hero-secondary"
          >
            <GlobeIcon size={16} />
            <span>Visit Official Site</span>
          </a>
        </div>
      </section>

      {/* Profile Details Card */}
      <section className="home-grid">
        <div className="profile-card">
          <h2 className="profile-card-title">
            <BuildingIcon size={18} />
            <span>Active Business Details</span>
          </h2>
          <div className="profile-meta-list">
            <div className="profile-meta-item">
              <span className="meta-icon">
                <TagIcon size={16} />
              </span>
              <div>
                <div className="meta-label">Display Name</div>
                <div className="meta-value">{clientInfo?.display_name || "Crushaders Tech Solutions"}</div>
              </div>
            </div>

            <div className="profile-meta-item">
              <span className="meta-icon">
                <KeyIcon size={16} />
              </span>
              <div>
                <div className="meta-label">Client Slug ID</div>
                <div className="meta-value font-mono">{clientInfo?.website_id || "crushaders_tech"}</div>
              </div>
            </div>

            <div className="profile-meta-item">
              <span className="meta-icon">
                <PhoneIcon size={16} />
              </span>
              <div>
                <div className="meta-label">Contact Phone</div>
                <div className="meta-value">{clientInfo?.contact?.phone || "Not configured"}</div>
              </div>
            </div>

            <div className="profile-meta-item">
              <span className="meta-icon">
                <MailIcon size={16} />
              </span>
              <div>
                <div className="meta-label">Contact Email</div>
                <div className="meta-value">{clientInfo?.contact?.email || "Not configured"}</div>
              </div>
            </div>

            <div className="profile-meta-item full-width">
              <span className="meta-icon">
                <LocationIcon size={16} />
              </span>
              <div>
                <div className="meta-label">Physical Location</div>
                <div className="meta-value">{clientInfo?.contact?.address || "Not configured"}</div>
              </div>
            </div>
          </div>

          <div className="profile-footer-cta">
            <span>Need to change these details or upload new brochures?</span>
            <Link to="/upload" className="link-inline">
              Update in /upload →
            </Link>
          </div>
        </div>

        {/* Live Chat Testing Card */}
        <div className="chat-intro-card">
          <h2 className="profile-card-title">
            <ChatIcon size={18} />
            <span>Live Assistant Interaction</span>
          </h2>
          <p className="card-sub">
            Click the chat launcher icon in the bottom-right corner to talk to this assistant!
          </p>

          <div className="test-prompts-title">Sample Queries to Try:</div>
          <div className="prompts-list">
            <div className="prompt-pill">
              &quot;Can you share your official contact phone and email?&quot;
            </div>
            <div className="prompt-pill">
              &quot;What services or room accommodations do you offer?&quot;
            </div>
            <div className="prompt-pill">
              &quot;Where are you located and what are your operating hours?&quot;
            </div>
            <div className="prompt-pill">
              &quot;What policies or terms should I know before booking?&quot;
            </div>
          </div>

          <div className="live-status-box">
            <span className="pulse-dot"></span>
            <span>RAG Context Vector Search Active (Qdrant + Groq LLM)</span>
          </div>
        </div>
      </section>
    </div>
  );
}
