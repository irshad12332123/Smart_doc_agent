export type Page =
  | "home"
  | "ask"
  | "library"
  | "notices"
  | "subjects"
  | "profile"
  | "upload"
  | "draft"
  | "admin";

export const nav = [
  { id: "home", label: "Home" },
  { id: "ask", label: "Ask AI" },
  { id: "library", label: "Library" },
  { id: "notices", label: "Notices" },
  { id: "subjects", label: "Subjects" },
  { id: "profile", label: "Profile" },
] as const;
