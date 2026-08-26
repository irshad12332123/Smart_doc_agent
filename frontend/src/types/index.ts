export type Role = "student" | "faculty" | "admin";

export interface Profile {
  id: string;
  full_name: string;
  role: Role;
  [key: string]: unknown;
}

export interface Session {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
  user: { id: string; email: string };
  profile: Profile;
}

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  filetype: string;
  num_chunks: number;
  uploaded_at: string;
  description?: string;
  document_type?: string;
  subject_id?: string | null;
  mime_type?: string;
}

export interface SourceChunk {
  chunk_id: string;
  doc_id: string;
  filename: string;
  text: string;
  score: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
  documents?: DocumentInfo[];
  streaming?: boolean;
  error?: boolean;
}
