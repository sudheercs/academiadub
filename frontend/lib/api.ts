const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);
let refreshInFlight: Promise<Response> | null = null;

function readCookie(name: string) {
  if (typeof document === "undefined") return "";
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (unsafeMethods.has(method)) {
    const csrfToken = readCookie("csrftoken");
    if (csrfToken) headers.set("X-CSRFToken", csrfToken);
  }

  const requestInit: RequestInit = {
    ...init,
    headers,
    credentials: "include",
  };
  const response = await fetch(input, requestInit);
  const path = typeof input === "string" ? new URL(input, window.location.href).pathname : "";
  if (
    response.status !== 401 ||
    path.endsWith("/auth/login/") ||
    path.endsWith("/auth/refresh/") ||
    path.endsWith("/auth/logout/")
  ) {
    return response;
  }

  if (!refreshInFlight) {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const csrfToken = readCookie("csrftoken");
    refreshInFlight = fetch(`${apiBase}/api/auth/refresh/`, {
      method: "POST",
      credentials: "include",
      headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
    }).finally(() => {
      refreshInFlight = null;
    });
  }
  const refreshResponse = await refreshInFlight;
  return refreshResponse.ok ? fetch(input, requestInit) : response;
}

export async function initializeCsrf(apiBase: string) {
  const response = await fetch(`${apiBase}/api/auth/csrf/`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Could not initialize CSRF protection (${response.status}).`);
  }
}
