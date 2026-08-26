import { useState } from "react";
import * as I from "lucide-react";
import { authApi, userApi } from "../../api/client";
import type { Session } from "../../types";
import { Error } from "../../components/ui/common";

export function Auth({ onSession }: { onSession: (value: Session) => void }) {
  const [view, setView] = useState<"choose" | "verify" | "register" | "login">(
    "choose",
  );
  const [kind, setKind] = useState<"student" | "faculty">("student");
  const [id, setId] = useState("");
  const [eligible, setEligible] = useState<{
    name: string;
    email: string;
    token: string;
  } | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submitVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await authApi.check(kind, id);
      if (result.status === "registered") {
        setEmail("");
        setView("login");
        setError("This ID already has an account. Please sign in.");
      } else if (
        result.name &&
        result.registered_email &&
        result.registration_token
      ) {
        setEligible({
          name: result.name,
          email: result.registered_email,
          token: result.registration_token,
        });
        setView("register");
      }
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Could not verify your record.")
          : "Could not verify your record.",
      );
    } finally {
      setBusy(false);
    }
  };

  const submitRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eligible) return;
    setBusy(true);
    setError("");
    try {
      await authApi.register(eligible.token, password);
      setEmail(eligible.email);
      setPassword("");
      setView("login");
      setError("Account created. Sign in to continue.");
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Could not create your account.")
          : "Could not create your account.",
      );
    } finally {
      setBusy(false);
    }
  };

  const submitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const login = await authApi.login(email, password);
      const me = await userApi.profile(login.access_token);
      onSession({ ...login, ...me });
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Unable to sign in.")
          : "Unable to sign in.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-aside">
        <div className="logo">
          <span className="brand-mark">
            <I.GraduationCap />
          </span>
          <span>
            ScholarHub<small>Academic Knowledge Hub</small>
          </span>
        </div>
        <div className="auth-copy">
          <span className="eyebrow">YOUR ACADEMIC SPACE</span>
          <h1>
            Everything your batch needs.
            <br />
            In one place.
          </h1>
          <p>
            Find notes, assignments, notices, and answers—then open the original
            source.
          </p>
        </div>
        <div className="auth-foot">BCA · 2024–27 · Semester 5</div>
      </div>
      <section className="auth-card">
        <div className="auth-inner">
          {view === "choose" && (
            <>
              <span className="eyebrow">WELCOME TO SCHOLARHUB</span>
              <h2>How would you like to continue?</h2>
              <p className="muted">
                Your access is verified against the university registry.
              </p>
              <div className="role-options">
                <button
                  onClick={() => {
                    setKind("student");
                    setView("verify");
                  }}
                >
                  <I.GraduationCap />
                  <b>Continue as Student</b>
                  <small>Access your batch materials and AI assistant</small>
                  <I.ChevronRight />
                </button>
                <button
                  onClick={() => {
                    setKind("faculty");
                    setView("verify");
                  }}
                >
                  <I.BookOpen />
                  <b>Continue as Faculty</b>
                  <small>Share learning material with your batches</small>
                  <I.ChevronRight />
                </button>
                <button
                  onClick={() => {
                    setView("login");
                  }}
                >
                  <I.ShieldCheck />
                  <b>Administrator</b>
                  <small>Existing admin accounts only</small>
                  <I.ChevronRight />
                </button>
              </div>
              <p className="auth-link">
                Already registered?{" "}
                <button onClick={() => setView("login")}>Sign in</button>
              </p>
            </>
          )}
          {view === "verify" && (
            <>
              <button className="back" onClick={() => setView("choose")}>
                <I.ArrowLeft /> Back
              </button>
              <span className="eyebrow">{kind.toUpperCase()} VERIFICATION</span>
              <h2>Verify your university record</h2>
              <p className="muted">
                Enter your {kind} ID to securely find your official record.
              </p>
              <form onSubmit={submitVerify}>
                <label>
                  {kind === "student" ? "Student ID" : "Faculty ID"}
                  <input
                    autoFocus
                    value={id}
                    onChange={(e) => setId(e.target.value)}
                    placeholder={
                      kind === "student"
                        ? "e.g. 24031009031"
                        : "Enter your faculty ID"
                    }
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? "Verifying…" : "Verify my record"}
                  <I.ArrowRight />
                </button>
              </form>
            </>
          )}
          {view === "register" && eligible && (
            <>
              <button className="back" onClick={() => setView("verify")}>
                <I.ArrowLeft /> Back
              </button>
              <span className="eyebrow">RECORD VERIFIED</span>
              <h2>Welcome, {eligible.name.split(" ")[0]}.</h2>
              <p className="muted">
                Your {kind} record was found. Set a password to create your
                ScholarHub account.
              </p>
              <div className="verified">
                <I.BadgeCheck />
                <span>
                  <small>OFFICIAL EMAIL</small>
                  <b>{eligible.email}</b>
                </span>
              </div>
              <form onSubmit={submitRegister}>
                <label>
                  Create password
                  <input
                    type="password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? "Creating account…" : "Create my account"}
                  <I.ArrowRight />
                </button>
              </form>
            </>
          )}
          {view === "login" && (
            <>
              <button className="back" onClick={() => setView("choose")}>
                <I.ArrowLeft /> Back
              </button>
              <span className="eyebrow">WELCOME BACK</span>
              <h2>Sign in to ScholarHub</h2>
              <p className="muted">
                Use the email address registered with the university.
              </p>
              <form onSubmit={submitLogin}>
                <label>
                  Email address
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@university.edu"
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Your password"
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? "Signing in…" : "Sign in"}
                  <I.ArrowRight />
                </button>
              </form>
              <p className="auth-link">
                Forgot password?{" "}
                <button
                  disabled
                  title="No password reset endpoint is configured yet."
                >
                  Contact your administrator
                </button>
              </p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
