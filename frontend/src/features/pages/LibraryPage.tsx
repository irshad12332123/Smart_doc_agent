import { useEffect, useMemo, useState } from "react";
import * as I from "lucide-react";
import type { DocumentInfo } from "../../types";
import { documentApi } from "../../api/client";
import { DocumentCard, Empty } from "../../components/ui/common";

const filterOptions = [
  { id: "All", label: "All Materials" },
  { id: "PDF", label: "PDFs" },
  { id: "DOCX", label: "Word Docs" },
  { id: "PPTX", label: "Presentations" },
];

export function LibraryPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [docError, setDocError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    documentApi
      .list()
      .then((items) => {
        if (active) setDocuments(items);
      })
      .catch(() => {
        if (active) setDocError("Documents could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const rows = useMemo(
    () =>
      documents.filter((d) => {
        const matchesFilter =
          filter === "All" ||
          d.filetype.toUpperCase() === filter ||
          (filter === "DOCX" && (d.filetype.toUpperCase() === "DOC" || d.filetype.toUpperCase() === "DOCX")) ||
          (filter === "PPTX" && (d.filetype.toUpperCase() === "PPT" || d.filetype.toUpperCase() === "PPTX"));

        const matchesSearch =
          d.filename.toLowerCase().includes(search.toLowerCase()) ||
          (d.description && d.description.toLowerCase().includes(search.toLowerCase()));

        return matchesFilter && matchesSearch;
      }),
    [documents, search, filter],
  );

  return (
    <div className="page library-page">
      <div className="page-header">
        <div className="page-title-group">
          <h1>Document Library</h1>
          <p className="lede">
            Browse, filter, and inspect verified academic resources and notes.
          </p>
        </div>
        <div className="page-stat-badge">
          <I.FileText />
          <span>{documents.length} Total Resources</span>
        </div>
      </div>

      <div className="library-tools">
        <div className="mini-search">
          <I.Search className="search-icon" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or topic…"
            aria-label="Search documents"
          />
          {search && (
            <button
              className="clear-search-btn"
              onClick={() => setSearch("")}
              title="Clear search"
            >
              <I.X />
            </button>
          )}
        </div>

        <div className="filter-chips">
          {filterOptions.map((f) => (
            <button
              className={`filter-btn ${filter === f.id ? "selected" : ""}`}
              onClick={() => setFilter(f.id)}
              key={f.id}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <Empty message="Loading documents…" />
      ) : docError ? (
        <Empty message={docError} />
      ) : rows.length > 0 ? (
        <div className="library-grid">
          {rows.map((d) => (
            <DocumentCard document={d} key={d.doc_id} />
          ))}
        </div>
      ) : (
        <Empty
          message={
            search || filter !== "All"
              ? "No documents matched your search criteria."
              : "No documents have been uploaded to your library yet."
          }
          actionLabel={search || filter !== "All" ? "Reset Filters" : undefined}
          onAction={() => {
            setSearch("");
            setFilter("All");
          }}
        />
      )}
    </div>
  );
}
