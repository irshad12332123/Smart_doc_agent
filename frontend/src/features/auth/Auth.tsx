import { useState } from "react";
import * as I from "lucide-react";
import { authApi, userApi } from "../../api/client";
import { useTheme } from "../../context/ThemeContext";
import type { Session } from "../../types";
import { Error } from "../../components/ui/common";

export function Auth({ onSession }: { onSession: (value: Session) => void }) {
  const { theme, toggleTheme } = useTheme();
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
        setError("This ID is already registered. Please sign in with your password.");
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
          : "Could not verify your university record. Please double-check your ID.",
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
      setError("Account created successfully! Sign in to enter your workspace.");
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Could not create your account.")
          : "Could not create your account. Please try again.",
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
          ? String((err as { message?: unknown }).message ?? "Invalid email or password.")
          : "Invalid email or password. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Top right theme toggle for Auth page */}
      <div className="auth-top-actions">
        <button
          className="theme-toggle-btn auth-theme-toggle"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme"}
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <I.Sun className="theme-icon" /> : <I.Moon className="theme-icon" />}
        </button>
      </div>

      <div className="auth-aside">
        <div className="logo auth-logo">
          <span className="brand-mark">
            <I.GraduationCap />
          </span>
          <div className="logo-text">
            <span className="brand-title">ScholarHub</span>
            <span className="brand-subtitle">Academic Knowledge Hub</span>
          </div>
        </div>

        <div className="auth-copy">
          <div className="eyebrow-pill">
            <I.Sparkles />
            <span>AI-POWERED ACADEMIC PORTAL</span>
          </div>
          <h1 className="auth-title">
            Everything your batch needs.
            <br />
            <span className="hero-gradient-text">In one place.</span>
          </h1>
          <p className="auth-desc">
            Instantly search notes, syllabus modules, faculty notices, and assignments with AI-backed citations and source document previews.
          </p>

          <div className="auth-features-list">
            <div className="auth-feature-item">
              <div className="feature-icon-wrap">
                <I.CheckCircle2 />
              </div>
              <div>
                <strong>Batch-Verified Context</strong>
                <p>Curated specifically for your semester and registered subjects.</p>
              </div>
            </div>
            <div className="auth-feature-item">
              <div className="feature-icon-wrap">
                <I.BookOpenCheck />
              </div>
              <div>
                <strong>Cited AI Search</strong>
                <p>Direct answers linked to exact pages and lecture slides.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="auth-foot">
          <span>Official University Academic Network · End-to-End Encrypted</span>
        </div>
      </div>

      <section className="auth-card">
        <div className="auth-inner">
          {view === "choose" && (
            <>
              <span className="eyebrow">GET STARTED</span>
              <h2>Welcome to ScholarHub</h2>
              <p className="muted">
                Select your role to access your personalized academic environment.
              </p>
              <div className="role-options">
                <button
                  className="role-card-btn"
                  onClick={() => {
                    setKind("student");
                    setView("verify");
                  }}
                >
                  <div className="role-icon-box role-student">
                    <I.GraduationCap />
                  </div>
                  <div className="role-meta">
                    <b>Student Portal</b>
                    <small>Access batch study resources, notes & AI query</small>
                  </div>
                  <I.ChevronRight className="role-arrow" />
                </button>

                <button
                  className="role-card-btn"
                  onClick={() => {
                    setKind("faculty");
                    setView("verify");
                  }}
                >
                  <div className="role-icon-box role-faculty">
                    <I.BookOpen />
                  </div>
                  <div className="role-meta">
                    <b>Faculty Portal</b>
                    <small>Upload learning materials & broadcast notices</small>
                  </div>
                  <I.ChevronRight className="role-arrow" />
                </button>

                <button
                  className="role-card-btn"
                  onClick={() => {
                    setView("login");
                  }}
                >
                  <div className="role-icon-box role-admin">
                    <I.ShieldCheck />
                  </div>
                  <div className="role-meta">
                    <b>Administrator</b>
                    <small>University management & access control</small>
                  </div>
                  <I.ChevronRight className="role-arrow" />
                </button>
              </div>

              <div className="auth-footer-link">
                <span>Already have an account?</span>{" "}
                <button onClick={() => setView("login")} className="link-btn">
                  Sign in
                </button>
              </div>
            </>
          )}

          {view === "verify" && (
            <>
              <button className="back" onClick={() => setView("choose")}>
                <I.ArrowLeft /> Back to Role Selection
              </button>
              <span className="eyebrow">{kind.toUpperCase()} VERIFICATION</span>
              <h2>Verify University Record</h2>
              <p className="muted">
                Enter your official {kind} enrollment number or registry ID.
              </p>
              <form onSubmit={submitVerify} className="auth-form">
                <label className="form-field">
                  <span className="field-label">
                    {kind === "student" ? "Student Roll / ID Number" : "Faculty Employee ID"}
                  </span>
                  <input
                    autoFocus
                    value={id}
                    onChange={(e) => setId(e.target.value)}
                    placeholder={
                      kind === "student"
                        ? "e.g. 24031009031"
                        : "Enter faculty employee ID"
                    }
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? (
                    <>
                      <I.Loader2 className="spinning-loader" />
                      <span>Verifying Record…</span>
                    </>
                  ) : (
                    <>
                      <span>Continue</span>
                      <I.ArrowRight />
                    </>
                  )}
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
              <h2>Welcome, {eligible.name.split(" ")[0]}</h2>
              <p className="muted">
                Your university profile was confirmed. Create a secure password to activate your account.
              </p>
              <div className="verified">
                <I.BadgeCheck />
                <span>
                  <small>OFFICIAL REGISTERED EMAIL</small>
                  <b>{eligible.email}</b>
                </span>
              </div>
              <form onSubmit={submitRegister} className="auth-form">
                <label className="form-field">
                  <span className="field-label">Set Account Password</span>
                  <input
                    type="password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? (
                    <>
                      <I.Loader2 className="spinning-loader" />
                      <span>Creating Account…</span>
                    </>
                  ) : (
                    <>
                      <span>Activate & Enter Workspace</span>
                      <I.ArrowRight />
                    </>
                  )}
                </button>
              </form>
            </>
          )}

          {view === "login" && (
            <>
              <button className="back" onClick={() => setView("choose")}>
                <I.ArrowLeft /> Back
              </button>
              <span className="eyebrow">SIGN IN</span>
              <h2>Welcome Back</h2>
              <p className="muted">
                Sign in using your verified university email and password.
              </p>
              <form onSubmit={submitLogin} className="auth-form">
                <label className="form-field">
                  <span className="field-label">Email Address</span>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="student@university.edu"
                    required
                  />
                </label>
                <label className="form-field">
                  <span className="field-label">Password</span>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? (
                    <>
                      <I.Loader2 className="spinning-loader" />
                      <span>Signing in…</span>
                    </>
                  ) : (
                    <>
                      <span>Sign In</span>
                      <I.ArrowRight />
                    </>
                  )}
                </button>
              </form>
              <div className="auth-footer-link">
                <span>Need help with your account?</span>{" "}
                <button
                  disabled
                  className="link-btn"
                  title="Contact IT Helpdesk for password resets"
                >
                  Contact Administrator
                </button>
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
