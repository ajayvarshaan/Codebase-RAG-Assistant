const API_BASE_URL = "http://127.0.0.1:8000";

export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem("token");

  const headers = new Headers(init.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let url: string;

  if (typeof input === "string") {
    if (input.startsWith("http://") || input.startsWith("https://")) {
      url = input;
    } else {
      url = `${API_BASE_URL}${input}`;
    }
  } else if (input instanceof URL) {
    url = input.toString();
  } else {
    url = input.url;
  }

  return fetch(url, {
    ...init,
    headers,
  });
}