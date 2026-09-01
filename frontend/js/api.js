const API_BASE_URL = window.RETENTION_API_BASE_URL || "http://localhost:5000";

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch (_error) {
    // A non-JSON response is handled below with a generic message.
  }

  if (!response.ok) {
    const message = payload?.message || `Request failed with status ${response.status}.`;
    throw new Error(message);
  }

  return payload;
}
