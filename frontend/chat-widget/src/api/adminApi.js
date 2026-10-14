const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const ADMIN_KEY = import.meta.env.VITE_ADMIN_API_KEY ?? "";

function getAdminHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  if (ADMIN_KEY) {
    headers["X-Admin-Key"] = ADMIN_KEY;
  }
  return headers;
}

export async function fetchWebsites() {
  const res = await fetch(`${BASE_URL}/api/v1/admin/websites`, {
    headers: getAdminHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch websites list");
  return res.json();
}

export async function setActiveWebsite(websiteId) {
  const res = await fetch(`${BASE_URL}/api/v1/admin/websites/active`, {
    method: "POST",
    headers: getAdminHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ website_id: websiteId }),
  });
  if (!res.ok) throw new Error("Failed to update active website");
  return res.json();
}

export async function submitSetupClient(formData) {
  const res = await fetch(`${BASE_URL}/api/v1/admin/setup`, {
    method: "POST",
    headers: getAdminHeaders(), // Browser sets multipart boundary automatically
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Setup / Update request failed");
  }
  return res.json(); // { job_id, website_id }
}

export async function updateCompanyProfile(websiteId, profileData) {
  const res = await fetch(`${BASE_URL}/api/v1/admin/websites/${websiteId}`, {
    method: "PUT",
    headers: getAdminHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(profileData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update profile");
  }
  return res.json();
}

export async function fetchCompanyDocs(websiteId) {
  const res = await fetch(`${BASE_URL}/api/v1/admin/websites/${websiteId}/docs`, {
    headers: getAdminHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json(); // { website_id, documents: [{ filename, size_bytes, modified_at, doc_type }] }
}

export async function deleteCompanyDoc(websiteId, filename) {
  const res = await fetch(`${BASE_URL}/api/v1/admin/websites/${websiteId}/docs/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: getAdminHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete document");
  }
  return res.json();
}

export async function fetchJobStatus(jobId) {
  const res = await fetch(`${BASE_URL}/api/v1/admin/onboard/${jobId}`, {
    headers: getAdminHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch job status");
  return res.json();
}

export async function triggerGenerateFinetune(websiteId, maxChunks = 40) {
  const form = new FormData();
  form.append("website_id", websiteId);
  form.append("max_chunks", maxChunks.toString());

  const res = await fetch(`${BASE_URL}/api/v1/admin/finetune/generate`, {
    method: "POST",
    headers: getAdminHeaders(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to trigger fine-tune generation");
  }
  return res.json(); // { job_id, website_id }
}

export async function uploadFinetuneDataset(websiteId, file) {
  const form = new FormData();
  form.append("website_id", websiteId);
  form.append("file", file);

  const res = await fetch(`${BASE_URL}/api/v1/admin/finetune/upload`, {
    method: "POST",
    headers: getAdminHeaders(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload dataset");
  }
  return res.json();
}

export function getFinetuneDownloadUrl(websiteId) {
  return `${BASE_URL}/api/v1/admin/finetune/${websiteId}?x_admin_key=${encodeURIComponent(ADMIN_KEY)}`;
}
