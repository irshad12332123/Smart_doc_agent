import type { DocumentInfo, SourceChunk } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface HealthStatus {
  ollama_ready: boolean;
  ollama_message: string;
  indexed_chunks: number;
  embed_model: string;
  chat_model: string;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) throw new Error("Failed to reach backend");
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${BASE_URL}/api/documents`);
  if (!res.ok) throw new Error("Failed to load documents");
  return res.json();
}

export async function uploadFiles(files: File[]): Promise<{
  documents: DocumentInfo[];
  total_chunks_added: number;
}> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE_URL}/api/ingest`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Upload failed");
  }
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/documents/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Delete failed");
}

export interface StreamHandlers {
  onSources: (sources: SourceChunk[]) => void;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

/**
 * Streams a chat response over Server-Sent Events. Reads the fetch body as a
 * stream and parses `data: {...}\n\n` frames incrementally, since the
 * browser EventSource API doesn't support POST bodies.
 */
export async function streamChat(
  message: string,
  history: { role: "user" | "assistant"; content: string }[],
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError(`Server error (${res.status})`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";

    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "sources") handlers.onSources(payload.sources || []);
        else if (payload.type === "token") handlers.onToken(payload.content || "");
        else if (payload.type === "done") handlers.onDone();
        else if (payload.type === "error") handlers.onError(payload.content || "Unknown error");
      } catch {
        // ignore malformed frame
      }
    }
  }
}
