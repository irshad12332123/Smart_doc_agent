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

  // Log user profile data when loaded/changed
  useEffect(() => {
    console.log("[Auth] Current Profile Data:", profile);
  }, [profile]);

  // Extract explicit UUIDs and readable labels
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
              id: batch.id, // Explicit UUID
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

  // Automatically pre-select student's single batch ID
  useEffect(() => {
    if (profile.role === "student" && profile.student_data.batch_id) {
      setBatchIds([profile.student_data.batch_id]);
    }
  }, [profile]);

  const upload = async () => {
    if (!files.length) return;

    // Fallback validation: ensure at least one batch UUID exists
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

    console.log("[Upload] Submitting files:", files);
    console.log("[Upload] Metadata payload:", payload);

    setBusy(true);
    setMessage("Uploading and processing document…");
    try {
      await documentApi.upload(files, payload);
      setDocuments(await documentApi.list());
      setFiles([]);
      setMessage("Ready for search ✓");
    } catch (e: unknown) {
      console.error("[Upload Error]:", e);
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
          Subject
          <select
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
          >
            <option value="">No subject</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.subject_code})
              </option>
            ))}
          </select>
        </label>
        <label>
          Batches
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
      <p className="api-note">
        <I.Info /> Choose one or more permitted batches. Subject is optional.
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
