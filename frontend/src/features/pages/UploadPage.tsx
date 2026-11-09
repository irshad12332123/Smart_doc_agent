import { useEffect, useRef, useState } from "react";
import * as I from "lucide-react";
import { documentApi } from "../../api/client";
import type { DocumentInfo, Profile, StudentSubject } from "../../types";

const errorMessage = (value: unknown, fallback: string) =>
  typeof value === "object" && value !== null && "message" in value
    ? String((value as { message?: unknown }).message ?? fallback)
    : fallback;

export function UploadPage({
  profile,
  documents,
  setDocuments,
}: {
  profile: Profile;
  documents: DocumentInfo[];
  setDocuments: (docs: DocumentInfo[]) => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const [batchIds, setBatchIds] = useState<string[]>([]);

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const picker = useRef<HTMLInputElement>(null);

  const batches: { id: string; label: string }[] =
    profile.role === "student"
      ? [
          {
            id: profile.student_data.batch_id,
            label: profile.student_data.batch_code,
          },
        ]
      : profile.role === "faculty"
        ? profile.faculty_data.courses.flatMap((course) =>
            course.batches.map((batch) => ({
              id: batch.id,
              label: `${course.name} · ${batch.batch_code}`,
            })),
          )
        : [];

  const subjects: StudentSubject[] =
    profile.role === "student"
      ? profile.student_data.subjects
      : profile.role === "faculty"
        ? profile.faculty_data.courses.flatMap((course) =>
            course.batches.flatMap((batch) => batch.subjects),
          )
        : [];

  const validBatchIds = new Set(
    batches.map((batch) => batch.id).filter(Boolean),
  );

  useEffect(() => {
    if (profile.role === "student" && profile.student_data.batch_id) {
      setBatchIds([profile.student_data.batch_id]);
    }
  }, [profile]);

  const upload = async () => {
    if (!files.length) return;

    const resolvedBatchIds = (
      batchIds.length > 0
        ? batchIds
        : profile.role === "student"
          ? [profile.student_data.batch_id]
          : []
    ).filter((id) => validBatchIds.has(id));

    if (!resolvedBatchIds.length) {
      setMessage("Please select at least one batch.");
      return;
    }

    const payload = {
      batch_ids: resolvedBatchIds,
      subject_id: subjectId || null,
    };

    setBusy(true);
    setMessage("Uploading document to queue…");
    try {
      await documentApi.upload(files, payload);
      const studentBatchId =
        profile.role === "student" ? profile.student_data?.batch_id : undefined;
      setDocuments(await documentApi.list(studentBatchId));
      setFiles([]);
      setMessage("Accepted. Document queued for processing ✓");
    } catch (e: unknown) {
      console.error("[Upload Error]:", e);  
      setMessage(errorMessage(e, "Upload failed. Please check file format."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page upload-page">
      <div className="page-header">
        <div className="page-title-group">
          <h1>Upload Course Materials</h1>
          <p className="lede">
            Add lecture notes, assignment PDFs, presentations, and readings for your batches.
          </p>
        </div>
      </div>

      <div
        className="upload-dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          setFiles(Array.from(e.dataTransfer.files));
        }}
        onClick={() => picker.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") picker.current?.click();
        }}
        role="button"
        tabIndex={0}
      >
        <div className="upload-icon-circle">
          <I.UploadCloud />
        </div>
        <h2>Drag & drop study files here, or click to browse</h2>
        <p className="dropzone-hint">
          Supports PDF, DOCX, PPTX, and image files · Max 25 MB per document
        </p>
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
        <div className="file-queue-section">
          <h3>Selected Files ({files.length})</h3>
          <div className="file-queue-grid">
            {files.map((f) => (
              <div key={f.name} className="file-queue-item">
                <div className="file-icon-wrap">
                  <I.FileText />
                </div>
                <div className="file-info-col">
                  <strong title={f.name}>{f.name}</strong>
                  <small>{(f.size / 1024 / 1024).toFixed(2)} MB</small>
                </div>
                <button
                  type="button"
                  className="remove-file-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFiles((p) => p.filter((x) => x !== f));
                  }}
                  title="Remove file"
                >
                  <I.X />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel upload-form-panel">
        <h2 className="panel-title">
          <I.Layers /> Document Metadata & Access
        </h2>

        <div className="upload-meta-grid">
          <label className="form-field">
            <span className="field-label">Document Title (Optional)</span>
            <input placeholder="Defaults to file name if left blank" />
          </label>

          <label className="form-field">
            <span className="field-label">Subject / Course Module</span>
            <select
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
            >
              <option value="">No specific subject (General)</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.subject_code})
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span className="field-label">Target Batch Access</span>
            <select
              multiple
              value={batchIds}
              onChange={(e) =>
                setBatchIds(
                  Array.from(e.target.selectedOptions, (option) => {
                    const selectedId = batches.find(
                      (batch) =>
                        batch.id === option.value || batch.label === option.value,
                    )?.id;
                    return selectedId ?? option.value;
                  }).filter((id) => validBatchIds.has(id)),
                )
              }
            >
              {batches.map((batch) => (
                <option key={batch.id} value={batch.id}>
                  {batch.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="api-note">
          <I.Info /> Documents uploaded will automatically be chunked, embedded with vector search, and made queryable by students in your selected batches.
        </div>

        {message && (
          <div
            className={`status-message ${
              message.includes("failed") ? "form-error" : "status-success"
            }`}
          >
            {message.includes("failed") ? <I.CircleAlert /> : <I.CheckCircle2 />}
            <span>{message}</span>
          </div>
        )}

        <div className="upload-submit-row">
          <button
            className="primary upload-cta-btn"
            disabled={!files.length || busy}
            onClick={upload}
          >
            {busy ? (
              <>
                <I.Loader2 className="spinning-loader" />
                <span>Processing Document…</span>
              </>
            ) : (
              <>
                <I.Upload />
                <span>Upload & Index Materials</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
