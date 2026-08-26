import { useRef, useState } from "react";
import * as I from "lucide-react";
import { documentApi } from "../../api/client";
import type { DocumentInfo } from "../../types";

const subjects = [
  "Software Engineering and Testing",
  "Machine Learning and NLP on AWS Cloud",
  "Multimedia and Animation",
  "Internet of Things (IoT)",
  "Software Engineering and Testing Lab",
  "Machine Learning and NLP on AWS Cloud Lab",
  "Project-II",
];

const errorMessage = (value: unknown, fallback: string) =>
  typeof value === "object" && value !== null && "message" in value
    ? String((value as { message?: unknown }).message ?? fallback)
    : fallback;

export function UploadPage({
  documents,
  setDocuments,
}: {
  documents: DocumentInfo[];
  setDocuments: (docs: DocumentInfo[]) => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const picker = useRef<HTMLInputElement>(null);

  const upload = async () => {
    if (!files.length) return;
    setBusy(true);
    setMessage("Uploading and processing document…");
    try {
      await documentApi.upload(files);
      setDocuments(await documentApi.list());
      setFiles([]);
      setMessage("Ready for search ✓");
    } catch (e: unknown) {
      setMessage(errorMessage(e, "Upload failed."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <h1>Upload material</h1>
      <p className="lede">
        Add useful course materials for your permitted batches.
      </p>
      <div
        className="upload-zone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          setFiles(Array.from(e.dataTransfer.files));
        }}
        onClick={() => picker.current?.click()}
      >
        <I.UploadCloud />
        <h2>Drop files here or browse</h2>
        <p>PDF, DOCX, PPTX, and images · Maximum 25 MB per file</p>
        <input
          ref={picker}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,image/*"
          hidden
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
        />
      </div>
      {files.length > 0 && (
        <div className="file-queue">
          {files.map((f) => (
            <div key={f.name}>
              <I.FileText />
              <span>
                {f.name}
                <small>{(f.size / 1024 / 1024).toFixed(1)} MB</small>
              </span>
              <button onClick={() => setFiles((p) => p.filter((x) => x !== f))}>
                <I.X />
              </button>
            </div>
          ))}
        </div>
      )}
      <div className="upload-meta">
        <label>
          Title
          <input placeholder="Use file name" />
        </label>
        <label>
          Category
          <select>
            <option>Course material</option>
            <option>Notes</option>
            <option>Assignment</option>
            <option>Notice</option>
          </select>
        </label>
        <label>
          Subject
          <select>
            <option>Select subject</option>
            {subjects.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="api-note">
        <I.Info /> The current upload API accepts files only; title, category,
        subject, and batch metadata await an expanded secure upload contract.
      </p>
      {message && (
        <p className={message.includes("failed") ? "form-error" : "success"}>
          {message}
        </p>
      )}
      <button
        className="primary"
        disabled={!files.length || busy}
        onClick={upload}
      >
        {busy ? "Processing…" : "Upload material"}
        <I.Upload />
      </button>
    </div>
  );
}
