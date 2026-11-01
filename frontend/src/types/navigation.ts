export type Page =
  | "home"
  | "ask"
  | "library"
  | "subjects"
  | "profile"
  | "upload"
  | "admin";

export const nav = [
  { id: "home", label: "Home" },
  { id: "ask", label: "Ask AI" },
  { id: "library", label: "Library" },
  { id: "subjects", label: "Subjects" },
  { id: "profile", label: "Profile" },
] as const;
