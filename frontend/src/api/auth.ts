const API_BASE_URL = "http://127.0.0.1:8000";

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

function getErrorMessage(data: any, fallback: string): string {
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((error: any) => error.msg || "Invalid input")
      .join(", ");
  }

  return fallback;
}

export async function signup(
  username: string,
  email: string,
  password: string
): Promise<User> {
  const response = await fetch(
    `${API_BASE_URL}/auth/signup`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username,
        email,
        password,
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      getErrorMessage(data, "Signup failed")
    );
  }

  return data;
}

export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const response = await fetch(
    `${API_BASE_URL}/auth/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      getErrorMessage(data, "Login failed")
    );
  }

  // Store JWT using the key used by the application
  localStorage.setItem(
    "token",
    data.access_token
  );

  return data;
}

export async function getCurrentUser(): Promise<User> {
  const token =
    localStorage.getItem("token");

  if (!token) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(
    `${API_BASE_URL}/auth/me`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  const data = await response.json();

  if (!response.ok) {
    localStorage.removeItem("token");

    throw new Error(
      getErrorMessage(
        data,
        "Authentication failed"
      )
    );
  }

  return data;
}

export function logout(): void {
  localStorage.removeItem("token");
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("token");
}

export function getAuthHeaders(): HeadersInit {
  const token =
    localStorage.getItem("token");

  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}