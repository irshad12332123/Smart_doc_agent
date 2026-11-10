export type Role = "student" | "faculty" | "admin";

export interface UserSummary {
  id: string;
  full_name: string;
  role: Role;
}

export interface BaseProfile {
  id: string;
  full_name: string;
}

// Student

export interface StudentSubject {
  id: string;
  name: string;
  subject_code: string;
}

export interface StudentData {
  student_id: string;
  registered_email: string;
  name: string;
  batch_id: string;
  batch_code: string;
  current_semester: number;
  course_name: string;
  student_role: string;
  subjects: StudentSubject[];
}

export interface StudentProfile extends BaseProfile {
  role: "student";
  student_data: StudentData;
}

// -----------------------------
// Faculty
// -----------------------------

export interface FacultySubject {
  id: string;
  name: string;
  subject_code: string;
}

export interface FacultyBatch {
  id: string;
  batch_code: string;
  subjects: FacultySubject[];
}

export interface FacultyCourse {
  id: string;
  name: string;
  code: string;
  batches: FacultyBatch[];
}

export interface FacultyData {
  courses: FacultyCourse[];
}

export interface FacultyProfile extends BaseProfile {
  role: "faculty";
  faculty_data: FacultyData;
}

// -----------------------------
// Admin
// -----------------------------

export interface AdminProfile extends BaseProfile {
  role: "admin";
}

export type Profile = StudentProfile | FacultyProfile | AdminProfile;

export interface Session {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
  user: { id: string; email: string };
  summary: UserSummary;
  profile?: Profile;
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
  file_url?: string | null;
  s3_key?: string | null;
  unit?: number | null;
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
