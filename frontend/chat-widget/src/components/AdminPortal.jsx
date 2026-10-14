import { useState, useEffect, useRef } from "react";
import {
  fetchWebsites,
  setActiveWebsite,
  submitSetupClient,
  fetchCompanyDocs,
  deleteCompanyDoc,
  fetchJobStatus,
  triggerGenerateFinetune,
  uploadFinetuneDataset,
  getFinetuneDownloadUrl,
} from "../api/adminApi";
import { Link } from "react-router-dom";
import {
  SparklesIcon,
  ChatIcon,
  EditIcon,
  PlusIcon,
  BuildingIcon,
  TuneIcon,
  CheckIcon,
  CloseIcon,
  InfoIcon,
  DocumentIcon,
  WordDocIcon,
  TrashIcon,
  UploadIcon,
  SaveIcon,
  RocketIcon,
  RefreshIcon,
  GlobeIcon,
  PhoneIcon,
  MailIcon,
  LocationIcon,
  DownloadIcon,
} from "./Icons";
import "./AdminPortal.css";

export function AdminPortal({ onClientChanged }) {
  const [activeTab, setActiveTab] = useState("setup"); // setup | finetune | websites
  const [websitesData, setWebsitesData] = useState({ websites: [], active_id: "" });
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null); // { type: 'success' | 'info' | 'error', text: '' }

  // Form Mode: 'create' or 'update'
  const [formMode, setFormMode] = useState("update");
  const [selectedUpdateId, setSelectedUpdateId] = useState("");

  // Form Fields
  const [displayName, setDisplayName] = useState("");
  const [websiteId, setWebsiteId] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);

  // Existing Documents for the selected company in 'update' mode
  const [existingDocs, setExistingDocs] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  // Fine-tuning State
  const [selectedFinetuneId, setSelectedFinetuneId] = useState("");
  const [maxChunks, setMaxChunks] = useState(40);
  const [finetuneJobStatus, setFinetuneJobStatus] = useState(null);
  const [uploadingFinetune, setUploadingFinetune] = useState(false);

  // Load registered websites
  const loadWebsites = async (preferredSelectId = null) => {
    try {
      const data = await fetchWebsites();
      setWebsitesData(data);

      const targetId =
        preferredSelectId ||
        selectedUpdateId ||
        data.active_id ||
        (data.websites && data.websites[0]?.website_id) ||
        "";

      if (targetId && formMode === "update") {
        populateFormForCompany(targetId, data.websites);
      }

      if (!selectedFinetuneId && data.websites?.length > 0) {
        setSelectedFinetuneId(data.active_id || data.websites[0].website_id);
      }
    } catch (err) {
      console.error("Failed to load websites:", err);
      setStatusMessage({
        type: "error",
        text: `Error connecting to backend: ${err.message}. Ensure backend is running.`,
      });
    }
  };

  useEffect(() => {
    loadWebsites();
  }, []);

  // Fetch documents whenever selected company in update mode changes
  const loadExistingDocs = async (id) => {
    if (!id) {
      setExistingDocs([]);
      return;
    }
    setLoadingDocs(true);
    try {
      const res = await fetchCompanyDocs(id);
      setExistingDocs(res.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents for", id, err);
      setExistingDocs([]);
    } finally {
      setLoadingDocs(false);
    }
  };

  // Populate form with existing company data
  const populateFormForCompany = (id, sitesList = null) => {
    const list = sitesList || websitesData.websites || [];
    const site = list.find((s) => s.website_id === id);
    if (!site) return;

    setSelectedUpdateId(site.website_id);
    setWebsiteId(site.website_id);
    setDisplayName(site.display_name || "");
    setWebsiteUrl(site.base_url && site.base_url !== "uploaded_documents" && site.base_url !== "documents" ? site.base_url : "");
    setPhone(site.contact?.phone || "");
    setEmail(site.contact?.email || "");
    setAddress(site.contact?.address || "");
    setSelectedFiles([]);

    loadExistingDocs(site.website_id);
  };

  // Switch between 'create' and 'update' modes
  const handleSwitchMode = (mode) => {
    setFormMode(mode);
    setStatusMessage(null);
    if (mode === "create") {
      setDisplayName("");
      setWebsiteId("");
      setWebsiteUrl("");
      setPhone("");
      setEmail("");
      setAddress("");
      setSelectedFiles([]);
      setExistingDocs([]);
    } else {
      const targetId = selectedUpdateId || websitesData.active_id || websitesData.websites?.[0]?.website_id;
      if (targetId) {
        populateFormForCompany(targetId);
      }
    }
  };

  // Handle changing the selected company in update dropdown
  const handleSelectCompanyToUpdate = (e) => {
    const id = e.target.value;
    setSelectedUpdateId(id);
    populateFormForCompany(id);
  };

  // Auto-slugify websiteId from displayName only in create mode
  const handleNameChange = (e) => {
    const val = e.target.value;
    setDisplayName(val);
    if (formMode === "create") {
      const autoSlug = val
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
      setWebsiteId(autoSlug);
    }
  };

  // Handle Document Selection (.pdf, .docx only)
  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter((f) => {
      const ext = f.name.toLowerCase();
      return ext.endsWith(".pdf") || ext.endsWith(".docx");
    });

    if (validFiles.length < files.length) {
      alert("Note: Only PDF (.pdf) and Word (.docx) files are supported. Text or other files were excluded.");
    }

    setSelectedFiles((prev) => [...prev, ...validFiles]);
  };

  const removeFile = (idxToRemove) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== idxToRemove));
  };

  // Delete an existing document from server
  const handleDeleteExistingDoc = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete '${filename}'?`)) return;
    try {
      await deleteCompanyDoc(websiteId, filename);
      setStatusMessage({ type: "success", text: `Deleted document: ${filename}` });
      loadExistingDocs(websiteId);
    } catch (err) {
      setStatusMessage({ type: "error", text: `Failed to delete document: ${err.message}` });
    }
  };

  // Submit Form (handles both Create and Update)
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!displayName.trim() || !websiteId.trim()) {
      setStatusMessage({ type: "error", text: "Please enter Company Display Name and Company Slug ID." });
      return;
    }

    if (formMode === "create" && selectedFiles.length === 0) {
      setStatusMessage({
        type: "error",
        text: "For a new company, please attach at least one PDF (.pdf) or Word (.docx) document for knowledge ingestion.",
      });
      return;
    }

    setLoading(true);
    const hasFiles = selectedFiles.length > 0;
    setStatusMessage({
      type: "info",
      text: hasFiles
        ? "Uploading documents and ingesting vectors into AI knowledge base..."
        : "Updating company profile information...",
    });

    try {
      const formData = new FormData();
      formData.append("display_name", displayName.trim());
      formData.append("website_id", websiteId.trim());
      formData.append("website_url", websiteUrl.trim());
      formData.append("phone", phone.trim());
      formData.append("email", email.trim());
      formData.append("address", address.trim());

      selectedFiles.forEach((file) => {
        formData.append("files", file);
      });

      const res = await submitSetupClient(formData);
      const jobId = res.job_id;

      // Poll job status
      const interval = setInterval(async () => {
        try {
          const status = await fetchJobStatus(jobId);
          if (status.status === "completed") {
            clearInterval(interval);
            setLoading(false);
            setStatusMessage({
              type: "success",
              text: `Success! ${displayName} has been saved and activated. ${
                hasFiles ? `Ingested ${status.points_ingested || "all"} vectors from uploaded files.` : "Profile updated."
              }`,
            });
            setSelectedFiles([]);
            await loadWebsites(websiteId);
            loadExistingDocs(websiteId);
            if (onClientChanged) onClientChanged();
          } else if (status.status === "failed") {
            clearInterval(interval);
            setLoading(false);
            setStatusMessage({ type: "error", text: `Ingestion failed: ${status.error || "Unknown error"}` });
          } else {
            setStatusMessage({
              type: "info",
              text: `Processing: ${status.status}... (Pages: ${status.pages_discovered || 0}, Chunks: ${
                status.chunks_created || 0
              })`,
            });
          }
        } catch {
          clearInterval(interval);
          setLoading(false);
        }
      }, 1500);
    } catch (err) {
      setLoading(false);
      setStatusMessage({ type: "error", text: err.message || "Failed to submit form." });
    }
  };

  // Switch Active Client
  const handleSetActive = async (id) => {
    try {
      await setActiveWebsite(id);
      await loadWebsites();
      setStatusMessage({ type: "success", text: `Active client switched to: ${id}. Chat widget updated!` });
      if (onClientChanged) onClientChanged();
    } catch (err) {
      setStatusMessage({ type: "error", text: err.message });
    }
  };

  // Quick edit button from Registered Companies tab
  const handleStartEditCompany = (site) => {
    setFormMode("update");
    setSelectedUpdateId(site.website_id);
    populateFormForCompany(site.website_id);
    setActiveTab("setup");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Generate Fine-Tuning Dataset
  const handleGenerateFinetune = async () => {
    if (!selectedFinetuneId) return;
    setFinetuneJobStatus({ status: "started", message: "Starting dataset synthesis with Groq LLM..." });

    try {
      const res = await triggerGenerateFinetune(selectedFinetuneId, maxChunks);
      const jobId = res.job_id;

      const interval = setInterval(async () => {
        try {
          const status = await fetchJobStatus(jobId);
          if (status.status === "completed") {
            clearInterval(interval);
            setFinetuneJobStatus({
              status: "completed",
              message: `Generated ${status.points_ingested || 0} instruction Q&A pairs in data/${selectedFinetuneId}/finetune_data.jsonl!`,
              downloadUrl: getFinetuneDownloadUrl(selectedFinetuneId),
            });
          } else if (status.status === "failed") {
            clearInterval(interval);
            setFinetuneJobStatus({ status: "failed", message: `Error: ${status.error}` });
          } else {
            setFinetuneJobStatus({ status: "running", message: `Synthesizing training pairs from knowledge chunks...` });
          }
        } catch {
          clearInterval(interval);
        }
      }, 2000);
    } catch (err) {
      setFinetuneJobStatus({ status: "failed", message: err.message });
    }
  };

  // Upload Custom .jsonl Dataset
  const handleFinetuneUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith(".jsonl")) {
      alert("Only .jsonl format is accepted.");
      return;
    }

    setUploadingFinetune(true);
    try {
      await uploadFinetuneDataset(selectedFinetuneId, file);
      alert(`Successfully uploaded custom dataset for ${selectedFinetuneId}!`);
    } catch (err) {
      alert(err.message);
    } finally {
      setUploadingFinetune(false);
    }
  };

  return (
    <div className="admin-container">
      {/* Header */}
      <div className="admin-header">
        <div className="admin-title-area">
          <h1>
            <SparklesIcon size={22} />
            <span>Multi-Tenant AI Assistant Manager</span>
          </h1>
          <p className="admin-subtitle">
            Update hotel profiles, ingest PDF & Word documents, and manage fine-tuning in one place.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Link
            to="/"
            className="btn-secondary btn-sm"
            style={{ textDecoration: "none" }}
            title="Go to main chat preview"
          >
            <ChatIcon size={14} />
            <span>Open Chatbot Page (/)</span>
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === "setup" ? "active" : ""}`}
          onClick={() => setActiveTab("setup")}
        >
          {formMode === "update" ? <EditIcon size={16} /> : <PlusIcon size={16} />}
          <span>{formMode === "update" ? "Update Hotel / Company" : "Onboard New Hotel"}</span>
        </button>
        <button
          className={`tab-btn ${activeTab === "websites" ? "active" : ""}`}
          onClick={() => setActiveTab("websites")}
        >
          <BuildingIcon size={16} />
          <span>Registered Companies ({websitesData.websites?.length || 0})</span>
        </button>
        <button
          className={`tab-btn ${activeTab === "finetune" ? "active" : ""}`}
          onClick={() => setActiveTab("finetune")}
        >
          <TuneIcon size={16} />
          <span>Fine-Tuning Manager</span>
        </button>
      </div>

      {/* Status Alert */}
      {statusMessage && (
        <div className={`alert-box alert-${statusMessage.type}`}>
          <div className="alert-content">
            <span className="alert-icon">
              {statusMessage.type === "success" ? (
                <CheckIcon size={16} />
              ) : statusMessage.type === "error" ? (
                <CloseIcon size={16} />
              ) : (
                <InfoIcon size={16} />
              )}
            </span>
            <span>{statusMessage.text}</span>
          </div>
          <button className="alert-close" onClick={() => setStatusMessage(null)}>
            <CloseIcon size={14} />
          </button>
        </div>
      )}

      {/* TAB 1: FORM (CREATE OR UPDATE) */}
      {activeTab === "setup" && (
        <div className="card">
          {/* Mode Switcher Banner */}
          <div className="mode-toggle-bar">
            <div className="mode-pills">
              <button
                type="button"
                className={`mode-pill ${formMode === "update" ? "active" : ""}`}
                onClick={() => handleSwitchMode("update")}
              >
                <EditIcon size={14} />
                <span>Update Existing Hotel / Company</span>
              </button>
              <button
                type="button"
                className={`mode-pill ${formMode === "create" ? "active" : ""}`}
                onClick={() => handleSwitchMode("create")}
              >
                <PlusIcon size={14} />
                <span>Onboard New Hotel / Company</span>
              </button>
            </div>
            {formMode === "update" && (
              <div className="company-select-inline">
                <label className="select-label">Select Company:</label>
                <select
                  className="form-input form-select-compact"
                  value={selectedUpdateId}
                  onChange={handleSelectCompanyToUpdate}
                >
                  {websitesData.websites?.map((w) => (
                    <option key={w.website_id} value={w.website_id}>
                      {w.display_name} ({w.website_id}) {w.website_id === websitesData.active_id ? "(Active)" : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="card-header-row">
            <div>
              <h2 className="card-title">
                {formMode === "update" ? `Update Details & Knowledge: ${displayName || selectedUpdateId}` : "Onboard New Hotel or Company"}
              </h2>
              <p className="card-desc">
                {formMode === "update"
                  ? "Modify hotel profile, update contact details, or upload additional PDF/DOCX files to update AI knowledge."
                  : "Provide company details and upload brochures, tariffs, or policy documents in PDF or DOCX format."}
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Hotel / Company Display Name *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Grand Palace Hotel & Resort"
                  value={displayName}
                  onChange={handleNameChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  Client ID / Slug (lowercase) *
                  {formMode === "update" && <span className="label-tip"> (Permanent Identifier)</span>}
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. grand_palace"
                  value={websiteId}
                  onChange={(e) => setWebsiteId(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
                  disabled={formMode === "update"}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Official Website URL (Optional)</label>
                <input
                  type="url"
                  className="form-input"
                  placeholder="https://grandpalaceresort.com"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Contact Phone Number</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="+91 9876543210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Contact Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="reservations@grandpalaceresort.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Physical Address / Location</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Marine Drive, Puri, Odisha"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
              </div>

              {/* Existing Documents List (Update Mode) */}
              {formMode === "update" && (
                <div className="form-group full-width existing-docs-section">
                  <div className="section-subheading">
                    <span className="subheading-with-icon">
                      <DocumentIcon size={16} />
                      <span>Already Uploaded Knowledge Documents ({existingDocs.length})</span>
                    </span>
                    {loadingDocs && <span className="loading-inline">Loading...</span>}
                  </div>
                  {existingDocs.length === 0 && !loadingDocs ? (
                    <div className="empty-docs-box">
                      No documents uploaded yet for this client. Attach PDF or DOCX files below to build knowledge.
                    </div>
                  ) : (
                    <div className="docs-chips-grid">
                      {existingDocs.map((doc) => (
                        <div key={doc.filename} className="doc-chip">
                          <span className="doc-icon">
                            {doc.doc_type === "pdf" ? <DocumentIcon size={16} /> : <WordDocIcon size={16} />}
                          </span>
                          <div className="doc-info">
                            <span className="doc-name" title={doc.filename}>{doc.filename}</span>
                            <span className="doc-meta">
                              {(doc.size_bytes / 1024).toFixed(0)} KB • {doc.modified_at}
                            </span>
                          </div>
                          <button
                            type="button"
                            className="doc-delete-btn"
                            title="Delete this document from knowledge base"
                            onClick={() => handleDeleteExistingDoc(doc.filename)}
                          >
                            <TrashIcon size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Document Dropzone */}
              <div className="form-group full-width">
                <label className="form-label">
                  {formMode === "update"
                    ? "Attach Additional / Updated Documents (.PDF & .DOCX ONLY)"
                    : "Knowledge Documents (.PDF & .DOCX ONLY) *"}
                </label>
                <div
                  className="dropzone"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="dropzone-icon">
                    <UploadIcon size={28} />
                  </div>
                  <div className="dropzone-title">
                    {formMode === "update"
                      ? "Click or Drop PDF / DOCX to Add to Knowledge Base"
                      : "Click to attach PDF or Word (.docx) files"}
                  </div>
                  <div className="dropzone-note">
                    {formMode === "update"
                      ? "Optional if only updating contact details. Uploaded files will be parsed and indexed for this hotel."
                      : "Upload room rates, hotel brochure, restaurant menu, FAQ sheets, and booking policies."}
                  </div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf,.docx,.doc"
                    multiple
                    style={{ display: "none" }}
                  />
                </div>

                {selectedFiles.length > 0 && (
                  <div className="file-list">
                    <span className="new-files-label">New files ready to ingest:</span>
                    {selectedFiles.map((f, i) => (
                      <span key={i} className="file-tag">
                        {f.name.toLowerCase().endsWith(".pdf") ? (
                          <DocumentIcon size={14} />
                        ) : (
                          <WordDocIcon size={14} />
                        )}
                        <span>{f.name} ({(f.size / 1024).toFixed(0)} KB)</span>
                        <button
                          type="button"
                          className="file-remove-btn"
                          onClick={() => removeFile(i)}
                        >
                          <CloseIcon size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? (
                  <span>Processing & Ingesting...</span>
                ) : formMode === "update" ? (
                  <>
                    <SaveIcon size={16} />
                    <span>
                      {selectedFiles.length > 0
                        ? "Save Changes & Ingest New Documents"
                        : "Save & Update Hotel Profile"}
                    </span>
                  </>
                ) : (
                  <>
                    <RocketIcon size={16} />
                    <span>Onboard New Hotel & Ingest Knowledge</span>
                  </>
                )}
              </button>

              {formMode === "update" && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => populateFormForCompany(selectedUpdateId)}
                  disabled={loading}
                >
                  <RefreshIcon size={14} />
                  <span>Reset Changes</span>
                </button>
              )}
            </div>
          </form>
        </div>
      )}

      {/* TAB 2: REGISTERED COMPANIES */}
      {activeTab === "websites" && (
        <div className="card">
          <div className="card-header-row">
            <div>
              <h2 className="card-title">Registered Companies & Hotels ({websitesData.websites?.length || 0})</h2>
              <p className="card-desc">
                Select any hotel to edit its form details or activate it as the live chatbot agent.
              </p>
            </div>
            <button
              className="btn-primary btn-sm"
              onClick={() => {
                handleSwitchMode("create");
                setActiveTab("setup");
              }}
            >
              <PlusIcon size={14} />
              <span>Onboard New Hotel</span>
            </button>
          </div>

          <div className="company-grid">
            {websitesData.websites?.map((site) => {
              const isActive = site.website_id === websitesData.active_id;
              return (
                <div key={site.website_id} className={`company-card ${isActive ? "is-active" : ""}`}>
                  <div>
                    <div className="company-card-header">
                      <div>
                        <div className="company-name">{site.display_name}</div>
                        <div className="company-id">ID: {site.website_id}</div>
                      </div>
                      {isActive ? (
                        <span className="badge-active">ACTIVE</span>
                      ) : (
                        <span className="badge-inactive">READY</span>
                      )}
                    </div>

                    <div className="company-meta">
                      <div className="meta-line">
                        <GlobeIcon size={14} />
                        <span>{site.base_url || "Uploaded Documents"}</span>
                      </div>
                      {site.contact?.phone && (
                        <div className="meta-line">
                          <PhoneIcon size={14} />
                          <span>{site.contact.phone}</span>
                        </div>
                      )}
                      {site.contact?.email && (
                        <div className="meta-line">
                          <MailIcon size={14} />
                          <span>{site.contact.email}</span>
                        </div>
                      )}
                      {site.contact?.address && (
                        <div className="meta-line">
                          <LocationIcon size={14} />
                          <span>{site.contact.address}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="company-card-actions">
                    <button
                      className="btn-secondary btn-sm"
                      onClick={() => handleStartEditCompany(site)}
                      title="Load this hotel into the form to update details and documents"
                    >
                      <EditIcon size={13} />
                      <span>Edit & Update Form</span>
                    </button>

                    {!isActive ? (
                      <button
                        className="btn-primary btn-sm"
                        onClick={() => handleSetActive(site.website_id)}
                      >
                        <CheckIcon size={13} />
                        <span>Make Active</span>
                      </button>
                    ) : (
                      <span className="active-indicator-label">
                        <CheckIcon size={13} />
                        <span>Responding in Chat</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: FINE-TUNING */}
      {activeTab === "finetune" && (
        <div>
          <div className="card">
            <h2 className="card-title">1. Generate Fine-Tuning Dataset (.jsonl)</h2>
            <p className="card-desc">
              Synthesizes realistic customer Q&A conversation pairs from the company's uploaded PDF/Word chunks using Groq LLM.
            </p>

            <div className="form-grid" style={{ alignItems: "flex-end" }}>
              <div className="form-group">
                <label className="form-label">Select Company / Hotel</label>
                <select
                  className="form-input"
                  value={selectedFinetuneId}
                  onChange={(e) => setSelectedFinetuneId(e.target.value)}
                >
                  {websitesData.websites?.map((w) => (
                    <option key={w.website_id} value={w.website_id}>
                      {w.display_name} ({w.website_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Maximum Chunks to Synthesize</label>
                <input
                  type="number"
                  className="form-input"
                  value={maxChunks}
                  onChange={(e) => setMaxChunks(Number(e.target.value))}
                  min={5}
                  max={200}
                />
              </div>

              <div className="form-group">
                <button
                  className="btn-primary"
                  onClick={handleGenerateFinetune}
                  disabled={!selectedFinetuneId || finetuneJobStatus?.status === "running"}
                >
                  <TuneIcon size={15} />
                  <span>Generate Training Dataset</span>
                </button>
              </div>
            </div>

            {finetuneJobStatus && (
              <div className="finetune-status-card">
                <p style={{ fontSize: 13, color: "#475569", margin: "0 0 8px 0" }}>
                  <strong>Status:</strong> {finetuneJobStatus.message}
                </p>
                {finetuneJobStatus.downloadUrl && (
                  <a
                    href={finetuneJobStatus.downloadUrl}
                    className="download-link"
                    download
                  >
                    <DownloadIcon size={15} />
                    <span>Download {selectedFinetuneId}_finetune.jsonl</span>
                  </a>
                )}
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="card-title">2. Upload Pre-Made .jsonl Dataset</h2>
            <p className="card-desc">
              Already have an instruction-tuning JSONL file? Upload it directly for this client.
            </p>
            <div className="upload-jsonl-box">
              <input
                type="file"
                accept=".jsonl"
                onChange={handleFinetuneUpload}
                disabled={uploadingFinetune}
              />
              {uploadingFinetune && <span className="loading-inline">Uploading dataset...</span>}
            </div>
          </div>

          <div className="card guide-card">
            <h2 className="card-title">How to Fine-Tune Your Model with this Dataset</h2>
            <ol className="guide-steps">
              <li>Generate and download the <strong>.jsonl</strong> file above.</li>
              <li>Upload the file to <strong>OpenAI Fine-Tuning</strong> (platform.openai.com/finetune) or <strong>Together AI / Unsloth</strong>.</li>
              <li>After training completes, copy your fine-tuned model ID (e.g. <code>ft:gpt-4o-mini:...</code> or <code>ft:llama-3-8b:...</code>).</li>
              <li>Update <code>GROQ_MODEL=your-model-id</code> in your backend <code>.env</code> file.</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
