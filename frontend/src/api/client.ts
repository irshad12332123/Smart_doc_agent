import type { DocumentInfo, Profile, SourceChunk } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const jsonHeaders = { "Content-Type": "application/json" };

const authHeaders = () => {
  try {
    const token = JSON.parse(
      localStorage.getItem("scholarhub-session") || "{}",
    ).access_token;
    return { Authorization: `Bearer ${token}` };
  } catch {}
};

async function bodyOrError(res: Response) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok)
    throw new Error(body.error || body.detail || "Something went wrong");
  return body;
}

export const authApi = {
  check: (kind: "student" | "faculty", id: string) =>
    fetch(`${BASE_URL}/auth/check-${kind}`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ [`${kind}_id`]: id }),
    }).then(bodyOrError) as Promise<{
      status: "eligible" | "registered";
      name?: string;
      registered_email?: string;
      registration_token?: string;
      message: string;
    }>,

  register: (registration_token: string, password: string) =>
    fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        registration_token,
        password,
        confirm_password: password,
      }),
    }).then(bodyOrError),

  login: (email: string, password: string) =>
    fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email, password }),
    }).then(bodyOrError) as Promise<{
      access_token: string;
      refresh_token?: string;
      expires_at?: number;
      user: { id: string; email: string };
    }>,

  me: (token: string) =>
    fetch(`${BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(bodyOrError) as Promise<{
      user: { id: string; email: string };
      profile: Profile;
    }>,
};
export const documentApi = {
  list: () =>
    fetch(`${BASE_URL}/api/documents`, { headers: authHeaders() }).then(
      bodyOrError,
    ) as Promise<DocumentInfo[]>,

  upload: (
    files: File[],
    metadata: Record<string, string | undefined> = {},
  ) => {
    const data = new FormData();
    files.forEach((file) => data.append("files", file));
    Object.entries(metadata).forEach(([key, value]) => {
      if (value) data.append(key, value);
    });
    return fetch(`${BASE_URL}/api/ingest`, {
      method: "POST",
      headers: authHeaders(),
      body: data,
    }).then(bodyOrError) as Promise<{ documents: DocumentInfo[] }>;
  },

  remove: (id: string) =>
    fetch(`${BASE_URL}/api/documents/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    }).then((res) => {
      if (!res.ok) throw new Error("Could not delete document");
    }),

  fileUrl: (id: string) =>
    fetch(`${BASE_URL}/api/documents/${id}/file`, {
      headers: authHeaders(),
    }).then(bodyOrError) as Promise<{
      url: string;
      expires_in: number;
      filename: string;
    }>,
};

export async function streamChat(
  message: string,
  history: { role: "user" | "assistant"; content: string }[],
  handlers: {
    sources(s: SourceChunk[]): void;
    documents?(documents: DocumentInfo[]): void;
    token(t: string): void;
    done(): void;
    error(m: string): void;
  },
) {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { ...jsonHeaders, ...authHeaders() },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok || !res.body) {
    handlers.error(`AI service error (${res.status})`);
    return;
  }
  const reader = res.body.getReader(),
    decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const line = frame.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      try {
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "sources") handlers.sources(payload.sources || []);
        if (payload.type === "documents")
          handlers.documents?.(payload.documents || []);
        if (payload.type === "token") handlers.token(payload.content || "");
        if (payload.type === "done") handlers.done();
        if (payload.type === "error")
          handlers.error(payload.content || "Unable to answer right now.");
      } catch {
        /* Ignore malformed SSE chunks. */
      }
    }
  }
}
