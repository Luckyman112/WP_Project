// Thin wrapper around fetch() for the Palate REST API.
// Sends the CSRF token required by Django's session authentication and
// turns non-2xx responses into ApiError with the server's validation data.

const csrfToken = () => document.querySelector('meta[name="csrf-token"]')?.content ?? "";

export class ApiError extends Error {
  constructor(status, data) {
    super(firstMessage(data) || `Request failed (${status})`);
    this.status = status;
    this.data = data ?? {};
  }
}

function firstMessage(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? String(first[0]) : typeof first === "object" ? firstMessage(first) : String(first ?? "");
}

export async function api(url, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRFToken"] = csrfToken();

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}

export const endpoints = {
  tastings: (params) => `/api/tastings/${params ? `?${params}` : ""}`,
  tasting: (id) => `/api/tastings/${id}/`,
  like: (id) => `/api/tastings/${id}/like/`,
  comments: (id) => `/api/tastings/${id}/comments/`,
  comment: (id, cid) => `/api/tastings/${id}/comments/${cid}/`,
  similar: (id, cross) => `/api/tastings/${id}/similar/${cross ? "?cross=1" : ""}`,
  almanac: (category) => `/api/almanac/${category ? `?category=${category}` : ""}`,
  palate: (username) => `/api/users/${encodeURIComponent(username)}/palate/`,
};
