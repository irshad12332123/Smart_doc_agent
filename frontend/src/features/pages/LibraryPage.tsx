import { useMemo, useState } from "react";
import * as I from "lucide-react";
import type { DocumentInfo } from "../../types";
import { DocumentCard, Empty } from "../../components/ui/common";

export function LibraryPage({
  documents,
  docError,
}: {
  documents: DocumentInfo[];
  docError: string;
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");

  const rows = useMemo(
    () =>
      documents.filter(
        (d) =>
          (filter === "All" || d.filetype.toUpperCase() === filter) &&
          d.filename.toLowerCase().includes(search.toLowerCase()),
      ),
    [documents, search, filter],
  );

  return (
    <div className="page">
      <h1>Document Library</h1>
      <p className="lede">
        Browse, filter, and manage your academic resources and notes.
      </p>
      <div className="library-tools">
        <label className="mini-search">
          <I.Search />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documents"
          />
        </label>
        {['All', 'PDF', 'DOCX', 'PPTX'].map((f) => (
          <button
            className={filter === f ? 'selected' : ''}
            onClick={() => setFilter(f)}
            key={f}
          >
            {f === 'All' ? 'All Subjects' : f}
          </button>
        ))}
      </div>
      {docError ? (
        <Empty message={docError} />
      ) : (
        <div className="library-grid">
          {rows.map((d) => (
            <DocumentCard document={d} key={d.doc_id} />
          ))}
        </div>
      )}
      {!docError && rows.length === 0 && (
        <Empty message="No documents match this filter." />
      )}
    </div>
  );
}
