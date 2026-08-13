import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import SourcesDrawer from "./components/SourcesDrawer";
import StatusPill from "./components/StatusPill";
import {
  deleteDocument,
  fetchDocuments,
  fetchHealth,
  streamChat,
  uploadFiles,
  type HealthStatus,
} from "./api/client";
import type { ChatMessage, DocumentInfo, SourceChunk } from "./types";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  const [drawerSources, setDrawerSources] = useState<SourceChunk[]>([]);
  const [activeSourceByMsg, setActiveSourceByMsg] = useState<Record<string, number | null>>({});

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
    fetchHealth().then(setHealth).catch(() => setHealth(null));
    const interval = setInterval(() => {
      fetchHealth().then(setHealth).catch(() => setHealth(null));
    }, 15000);
    return () => clearInterval(interval);
  }, [refreshDocuments]);

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    setUploadError(null);
    try {
      await uploadFiles(files);
      await refreshDocuments();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    await deleteDocument(docId);
    await refreshDocuments();
  };

  const handleSend = async (text: string) => {
    const userMsg: ChatMessage = { id: uid(), role: "user", content: text };
    const assistantId = uid();
    const assistantMsg: ChatMessage = { id: assistantId, role: "assistant", content: "", streaming: true };

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setSending(true);

    let accumulated = "";

    await streamChat(text, history, {
      onSources: (sources) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, sources } : m))
        );
      },
      onToken: (token) => {
        accumulated += token;
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: accumulated } : m))
        );
      },
      onDone: () => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m))
        );
        setSending(false);
      },
      onError: (message) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: message || "Something went wrong.", streaming: false, error: true }
              : m
          )
        );
        setSending(false);
      },
    });
  };

  const handleCitationClick = (msgId: string, index: number) => {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg?.sources) return;
    setDrawerSources(msg.sources);
    setActiveSourceByMsg((prev) => ({
      ...prev,
      [msgId]: prev[msgId] === index ? null : index,
    }));
    setTimeout(() => {
      document.getElementById(`source-${index}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  };

  const lastAssistantSources = [...messages].reverse().find((m) => m.sources?.length)?.sources;
  const activeMsgId = [...messages].reverse().find((m) => m.sources?.length)?.id;

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden" style={{ background: "var(--bg)" }}>
      <header
        className="flex items-center justify-between px-5 py-3 border-b shrink-0"
        style={{ borderColor: "var(--border)" }}
      >
        <span className="text-xs font-mono" style={{ color: "var(--text-faint)" }}>
          local · private · runs entirely on your machine
        </span>
        <StatusPill health={health} />
      </header>

      <div className="flex flex-1 min-h-0">
        <Sidebar
          documents={documents}
          loading={docsLoading}
          uploading={uploading}
          indexedChunks={documents.reduce((sum, d) => sum + d.num_chunks, 0)}
          onUpload={handleUpload}
          onDelete={handleDelete}
        />

        <ChatWindow
          messages={messages}
          activeSourceByMsg={activeSourceByMsg}
          onCitationClick={handleCitationClick}
          onSend={handleSend}
          disabled={sending}
        />

        {lastAssistantSources && lastAssistantSources.length > 0 && (
          <SourcesDrawer
            sources={drawerSources}
            activeIndex={activeMsgId ? activeSourceByMsg[activeMsgId] ?? null : null}
            onClose={() => setDrawerSources([])}
            onSelect={(idx) => activeMsgId && handleCitationClick(activeMsgId, idx)}
          />
        )}
      </div>

      {uploadError && (
        <div
          className="fixed bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg text-xs font-mono shadow-lg"
          style={{ background: "#3a2020", color: "#e07a5f", border: "1px solid #5a3030" }}
        >
          {uploadError}
        </div>
      )}
    </div>
  );
}
