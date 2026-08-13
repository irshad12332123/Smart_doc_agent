export interface SourceChunk {
  chunk_id: string;
  doc_id: string;
  filename: string;
  text: string;
  score: number;
}

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  filetype: string;
  num_chunks: number;
  uploaded_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
  streaming?: boolean;
  error?: boolean;
}
