import type { DocumentInfo, Profile, SourceChunk } from "../types";

const BASE_URL = (import.meta.env.BACKEND_API_URL)

const jsonHeaders = { "Content-Type": "application/json" };

const authHeaders = (): Record<string, string> => {
  try {
    const token = JSON.parse(
      localStorage.getItem("scholarhub-session") || "{}",
    ).access_token;
    return { Authorization: `Bearer ${token}` };
  } catch {
    return {} as Record<string, string>;
  }
};

async function bodyOrError(res: Response) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok)
    throw new Error(body.error || body.detail || "Something went wrong");
  return body;
}

export const userApi = {
  profile: async (token: string) => {
    const endpoint = `${BASE_URL}/u/profile`;

    let lastError: unknown;

      try {
        const res = await fetch(endpoint, {
          headers: { Authorization: `Bearer ${token}` },
        });

        const body = await res.json().catch(() => ({}));

        if (!res.ok) {
          lastError = new Error(
            body.error ||
              body.detail ||
              body.message ||
              "Could not load profile.",
          );

        }

        const profile = body.data as Profile;

        const user =
          body.user ??
          ({
            id: profile.id,
            email:
              profile.role === "student"
                ? profile.student_data.registered_email
                : "",
          } as { id: string; email: string });

        return {
          user: {
            id: user.id || profile.id,
            email: user.email || "",
          },
          profile,
        } as {
          user: { id: string; email: string };
          profile: Profile;
        };
      } catch (error) {
        lastError = error;
      }


    throw lastError ?? new Error("Could not load profile.");
  },
};

export const authApi = {
  check: (
    email: string,
    role?: "student" | "faculty" | null,
    action?: "login" | "register",
  ) =>
    fetch(`${BASE_URL}/auth/check`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        email: email.trim(),
        role: role || undefined,
        action: action || undefined,
      }),
    }).then(bodyOrError) as Promise<{
      status: "eligible" | "registered" | "already registered";
      name?: string;
      email?: string;
      registered_email?: string;
      role?: string;
      registration_token?: string;
      message?: string;
    }>,

  register: (
    registration_token: string,
    password: string,
    email?: string,
    role?: string,
  ) =>
    fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({
        registration_token,
        password,
        confirm_password: password,
        email,
        role,
      }),
    }).then(bodyOrError) as Promise<{
      status: string;
      message: string;
      email: string;
    }>,

  login: (email: string, password: string, role?: string) =>
    fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email: email.trim(), password, role }),
    }).then(bodyOrError) as Promise<{
      access_token: string;
      refresh_token?: string;
      expires_at?: number;
      user: { id: string; email: string };
    }>,

  resendConfirmation: (email: string) =>
    fetch(`${BASE_URL}/auth/resend-confirmation`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email: email.trim() }),
    }).then(bodyOrError) as Promise<{ message: string }>,

  me: (token: string) => userApi.profile(token),
};

export const documentApi = {
  list: (batchId?: string) => {
    const params = new URLSearchParams();
    if (batchId) {
      params.append("batch_id", batchId);
    }
    const query = params.toString() ? `?${params.toString()}` : "";
    return fetch(`${BASE_URL}/api/documents${query}`, { headers: authHeaders() }).then(
      bodyOrError,
    ) as Promise<DocumentInfo[]>;
  },

  upload: (
    files: File[],
    metadata: Record<string, string | string[] | null | undefined> = {},
  ) => {
    const data = new FormData();
    files.forEach((file) => data.append("files", file));
    Object.entries(metadata).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => data.append(key, item));
      } else if (value !== undefined && value !== null) {
        data.append(key, value);
      }
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

  fileUrl: (id: string, download: boolean = false) => {
    const query = download ? "?download=true" : "";
    return fetch(`${BASE_URL}/api/documents/${id}/file${query}`, {
      headers: authHeaders(),
    }).then(bodyOrError) as Promise<{
      url: string;
      expires_in: number;
      filename: string;
    }>;
  },

  openDocument: async (id: string) => {
    const data = await documentApi.fileUrl(id, false);
    if (!data?.url) {
      throw new Error("File URL is not available.");
    }
    window.open(data.url, "_blank", "noopener,noreferrer");
    return data;
  },

  downloadDocument: async (id: string, preferredFilename?: string) => {
    const data = await documentApi.fileUrl(id, true);
    if (!data?.url) {
      throw new Error("File URL is not available.");
    }
    const finalFilename = preferredFilename || data.filename || "document";

    try {
      const res = await fetch(data.url);
      if (!res.ok) throw new Error("Failed to fetch file content");
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = finalFilename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch {
      // Direct navigation fallback if blob fetch is blocked by CORS
      const a = document.createElement("a");
      a.href = data.url;
      a.download = finalFilename;
      a.target = "_blank";
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
    return data;
  },
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
  subjectList?: Array<string | { id: string; name: string; code?: string; subject_code?: string }>,
) {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { ...jsonHeaders, ...authHeaders() },
    body: JSON.stringify({ message, history, subject_list: subjectList }),
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
