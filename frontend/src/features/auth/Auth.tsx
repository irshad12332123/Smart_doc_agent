import { useState } from "react";
import * as I from "lucide-react";
import { authApi, userApi } from "../../api/client";
import { useTheme } from "../../context/ThemeContext";
import type { Session } from "../../types";

type AuthMode = "register" | "login" | "admin";
type RoleKind = "student" | "faculty";
type RegStep = "verify" | "activate";

export function Auth({ onSession }: { onSession: (value: Session) => void }) {
  const { theme, toggleTheme } = useTheme();

  // Primary mode: 3 main buttons
  const [mode, setMode] = useState<AuthMode>("login");

  // Role for Register and Login (faculty, student)
  const [role, setRole] = useState<RoleKind | null>(null);

  // Register sub-step: verify ID -> activate (create password)
  const [regStep, setRegStep] = useState<RegStep>("verify");

  // Form fields
  const [idNumber, setIdNumber] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Verification record result
  const [eligible, setEligible] = useState<{
    name: string;
    email: string;
    token: string;
  } | null>(null);

  // Status & feedback
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [busy, setBusy] = useState(false);

  // Switch top-level mode
  const handleSelectMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setError("");
    setSuccessMsg("");
    if (nextMode === "admin") {
      setRole(null);
    } else {
      setRole(null);
    }
    setRegStep("verify");
  };

  // Switch role (faculty / student)
  const handleSelectRole = (nextRole: RoleKind) => {
    setRole(nextRole);
    setError("");
    setSuccessMsg("");
    setRegStep("verify");
  };

  // Back button handler
  const handleBack = () => {
    setError("");
    setSuccessMsg("");
    if (mode === "register") {
      if (regStep === "activate") {
        setRegStep("verify");
      } else {
        setRole(null);
      }
    } else if (mode === "login") {
      if (role !== null) {
        setRole(null);
      }
    }
  };

  // 1. Verification Step (Register Flow)
  const submitVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!role || !idNumber.trim()) return;
    setBusy(true);
    setError("");
    setSuccessMsg("");

    try {
      const result = await authApi.check(role, idNumber.trim());
      if (result.status === "registered") {
        setSuccessMsg("");
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
        setRegStep("activate");
      } else {
        setError(result.message || "Record found but could not generate verification token.");
      }
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Could not verify your university record.")
          : "Could not verify your record. Please verify your ID with the registry.",
      );
    } finally {
      setBusy(false);
    }
  };

  // 2. Account Activation Step (Register Flow)
  const submitRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eligible || !password) return;
    setBusy(true);
    setError("");
    setSuccessMsg("");

    try {
      await authApi.register(eligible.token, password);
      // Pre-fill email and redirect to login
      setEmail(eligible.email);
      setPassword("");
      setMode("login");
      setSuccessMsg("Account activated successfully! Sign in with your new password.");
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Could not create account.")
          : "Could not create account. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  // 3. Login Step (Student, Faculty, or Admin)
  const submitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setBusy(true);
    setError("");
    setSuccessMsg("");

    try {
      const login = await authApi.login(email.trim(), password);
      const me = await userApi.profile(login.access_token);
      onSession({ ...login, ...me });
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Invalid email or password.")
          : "Invalid credentials. Please verify your email and password.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Top right theme toggle with boxy aesthetic */}
      <div className="auth-top-actions">
        <button
          className="auth-theme-btn"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label="Toggle theme"
        >
          {theme === "dark" ? (
            <>
              <I.Sun className="theme-icon" />
              <span className="theme-label">LIGHT</span>
            </>
          ) : (
            <>
              <I.Moon className="theme-icon" />
              <span className="theme-label">DARK</span>
            </>
          )}
        </button>
      </div>

      {/* LEFT: concise product overview */}
      <div className="auth-aside">
        <div className="auth-hero-header">
          <div className="auth-brand-badge">
            <span className="brand-badge-box">
              <I.GraduationCap />
            </span>
            <div className="brand-badge-info">
              <span className="brand-badge-title">SCHOLARHUB</span>
              <span className="brand-badge-sub">INTELLIGENT AGENT</span>
            </div>
          </div>
          <span className="hero-script-tag">Academic workspace</span>
        </div>

        <div className="auth-hero-main">
          <div className="hero-cursive-eyebrow">ACADEMIC KNOWLEDGE MANAGEMENT</div>

          <h1 className="auth-hero-title">
            Your academic workspace, organized.
          </h1>

          <p className="auth-hero-desc">
            Find verified course materials and get AI answers grounded in your academic documents.
          </p>

          <div className="auth-hero-boxes">
            <div className="hero-feature-box">
              <span className="feature-box-tag">CURATED</span>
              <strong className="feature-box-title">Batch Syllabus</strong>
              <p className="feature-box-desc">Synchronized to your registered subjects and units</p>
            </div>
            <div className="hero-feature-box">
              <span className="feature-box-tag">GROUNDED</span>
              <strong className="feature-box-title">Cited Evidence</strong>
              <p className="feature-box-desc">Exact slide, page, and chunk previews with SLM checks</p>
            </div>
          </div>

        </div>
      </div>

      {/* RIGHT: Boxy Interactive Auth Card (Single Page for Login & Register) */}
      <section className="auth-card">
        <div className="auth-inner">
          {/* 3 Main Mode Buttons: REGISTER, LOGIN, ADMIN */}
          <div className="auth-mode-bar" role="tablist" aria-label="Authentication Modes">
            <button
              type="button"
              className={`auth-mode-btn ${mode === "register" ? "active active-register" : ""}`}
              onClick={() => handleSelectMode("register")}
            >
              <I.UserPlus className="mode-btn-icon" />
              <span>REGISTER</span>
            </button>

            <button
              type="button"
              className={`auth-mode-btn ${mode === "login" ? "active active-login" : ""}`}
              onClick={() => handleSelectMode("login")}
            >
              <I.LogIn className="mode-btn-icon" />
              <span>LOGIN</span>
            </button>

            <button
              type="button"
              className={`auth-mode-btn ${mode === "admin" ? "active active-admin" : ""}`}
              onClick={() => handleSelectMode("admin")}
            >
              <I.ShieldCheck className="mode-btn-icon" />
              <span>ADMIN</span>
            </button>
          </div>

          {/* Feedback messages */}
          {error && (
            <div className="boxy-alert boxy-alert-error">
              <I.AlertCircle className="alert-icon" />
              <div className="alert-content">
                <span>{error}</span>
                {mode === "register" && error.includes("already registered") && (
                  <button
                    type="button"
                    className="alert-link-btn"
                    onClick={() => {
                      setMode("login");
                      setError("");
                    }}
                  >
                    Switch to Login →
                  </button>
                )}
              </div>
            </div>
          )}

          {successMsg && (
            <div className="boxy-alert boxy-alert-success">
              <I.CheckCircle2 className="alert-icon" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* =============================================================
              MODE: REGISTER
              Followed by: FACULTY, STUDENT
              Register flow follows with the verification thing.
              ============================================================= */}
          {mode === "register" && (
            <div className="auth-flow-container">
              {/* Step 1: Role Selection (Faculty / Student) */}
              {role === null && (
                <div className="auth-step-pane">
                  <div className="pane-header">
                    <span className="boxy-eyebrow">STEP 1 OF 2</span>
                    <h2 className="pane-title">Select Affiliation</h2>
                    <p className="pane-subtitle">
                      Choose whether you are enrolling as Faculty or Student.
                    </p>
                  </div>

                  <div className="auth-role-grid">
                    <button
                      type="button"
                      className="auth-role-btn role-faculty"
                      onClick={() => handleSelectRole("faculty")}
                    >
                      <I.BookOpen className="role-btn-icon" />
                      <span>FACULTY</span>
                    </button>

                    <button
                      type="button"
                      className="auth-role-btn role-student"
                      onClick={() => handleSelectRole("student")}
                    >
                      <I.GraduationCap className="role-btn-icon" />
                      <span>STUDENT</span>
                    </button>
                  </div>

                  <div className="auth-footer-prompt">
                    <span>Already verified your record?</span>{" "}
                    <button
                      type="button"
                      className="boxy-inline-link"
                      onClick={() => handleSelectMode("login")}
                    >
                      Sign In Here
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2: Verification with University ID */}
              {role !== null && regStep === "verify" && (
                <div className="auth-step-pane">
                  <button type="button" className="auth-back-btn" onClick={handleBack}>
                    <I.ArrowLeft />
                    <span>CHANGE ROLE</span>
                  </button>

                  <div className="pane-header">
                    <span className="boxy-eyebrow">
                      {role.toUpperCase()} RECORD VERIFICATION
                    </span>
                    <h2 className="pane-title">Verify University Record</h2>
                    <p className="pane-subtitle">
                      Enter your official {role === "student" ? "student roll / registration number" : "faculty employee ID"} to verify eligibility.
                    </p>
                  </div>

                  <form onSubmit={submitVerify} className="boxy-form">
                    <label className="boxy-field">
                      <span className="field-label">
                        {role === "student" ? "STUDENT ROLL / ENROLLMENT ID" : "FACULTY EMPLOYEE ID"}
                      </span>
                      <div className="input-wrap">
                        <input
                          autoFocus
                          value={idNumber}
                          onChange={(e) => setIdNumber(e.target.value)}
                          placeholder={
                            role === "student"
                              ? "e.g. 24031009031"
                              : "e.g. FAC-2024-089"
                          }
                          required
                          className="boxy-input"
                        />
                      </div>
                    </label>

                    <button
                      type="submit"
                      className="auth-action-btn primary-action full"
                      disabled={busy}
                    >
                      {busy ? (
                        <>
                          <I.Loader2 className="spinning-loader" />
                          <span>VERIFYING RECORD…</span>
                        </>
                      ) : (
                        <>
                          <span>VERIFY RECORD</span>
                          <I.ArrowRight />
                        </>
                      )}
                    </button>
                  </form>
                </div>
              )}

              {/* Step 3: Record Verified -> Create Password & Activate */}
              {role !== null && regStep === "activate" && eligible && (
                <div className="auth-step-pane">
                  <button type="button" className="auth-back-btn" onClick={handleBack}>
                    <I.ArrowLeft />
                    <span>BACK</span>
                  </button>

                  <div className="pane-header">
                    <span className="boxy-eyebrow">STEP 2: ACCOUNT ACTIVATION</span>
                    <h2 className="pane-title">Welcome, {eligible.name.split(" ")[0]}</h2>
                    <p className="pane-subtitle">
                      Your university credentials have been verified. Set your portal password to activate your account.
                    </p>
                  </div>

                  <div className="boxy-verified-banner">
                    <div className="verified-badge-icon">
                      <I.CheckSquare />
                    </div>
                    <div className="verified-details">
                      <span className="verified-label">OFFICIAL REGISTERED EMAIL</span>
                      <strong className="verified-email">{eligible.email}</strong>
                      <span className="verified-name">Verified Name: {eligible.name}</span>
                    </div>
                  </div>

                  <form onSubmit={submitRegister} className="boxy-form">
                    <label className="boxy-field">
                      <span className="field-label">SET WORKSPACE PASSWORD</span>
                      <div className="input-wrap has-action">
                        <input
                          autoFocus
                          type={showPassword ? "text" : "password"}
                          minLength={8}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Minimum 8 characters"
                          required
                          className="boxy-input"
                        />
                        <button
                          type="button"
                          className="input-eye-btn"
                          onClick={() => setShowPassword(!showPassword)}
                          title={showPassword ? "Hide password" : "Show password"}
                        >
                          {showPassword ? <I.EyeOff /> : <I.Eye />}
                        </button>
                      </div>
                    </label>

                    <button
                      type="submit"
                      className="auth-action-btn primary-action full"
                      disabled={busy}
                    >
                      {busy ? (
                        <>
                          <I.Loader2 className="spinning-loader" />
                          <span>ACTIVATING WORKSPACE…</span>
                        </>
                      ) : (
                        <>
                          <span>ACTIVATE & ENTER WORKSPACE</span>
                          <I.ArrowRight />
                        </>
                      )}
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}

          {/* =============================================================
              MODE: LOGIN
              Followed by: FACULTY, STUDENT
              ============================================================= */}
          {mode === "login" && (
            <div className="auth-flow-container">
              {/* Step 1: Role Selection (Faculty / Student) */}
              {role === null && (
                <div className="auth-step-pane">
                  <div className="pane-header">
                    <span className="boxy-eyebrow">PORTAL SELECTION</span>
                    <h2 className="pane-title">Select Portal to Sign In</h2>
                    <p className="pane-subtitle">
                      Choose your academic affiliation to access your workspace.
                    </p>
                  </div>

                  <div className="auth-role-grid">
                    <button
                      type="button"
                      className="auth-role-btn role-faculty"
                      onClick={() => handleSelectRole("faculty")}
                    >
                      <I.BookOpen className="role-btn-icon" />
                      <span>FACULTY</span>
                    </button>

                    <button
                      type="button"
                      className="auth-role-btn role-student"
                      onClick={() => handleSelectRole("student")}
                    >
                      <I.GraduationCap className="role-btn-icon" />
                      <span>STUDENT</span>
                    </button>
                  </div>

                  <div className="auth-footer-prompt">
                    <span>New student or faculty member?</span>{" "}
                    <button
                      type="button"
                      className="boxy-inline-link"
                      onClick={() => handleSelectMode("register")}
                    >
                      Begin Registration
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2: Login Form for Chosen Role */}
              {role !== null && (
                <div className="auth-step-pane">
                  <button type="button" className="auth-back-btn" onClick={handleBack}>
                    <I.ArrowLeft />
                    <span>CHANGE ROLE</span>
                  </button>

                  <div className="pane-header">
                    <span className="boxy-eyebrow">
                      {role.toUpperCase()} WORKSPACE SIGN IN
                    </span>
                    <h2 className="pane-title">Welcome Back</h2>
                    <p className="pane-subtitle">
                      Sign in with your verified university credentials.
                    </p>
                  </div>

                  <form onSubmit={submitLogin} className="boxy-form">
                    <label className="boxy-field">
                      <span className="field-label">OFFICIAL UNIVERSITY EMAIL</span>
                      <div className="input-wrap">
                        <input
                          autoFocus
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder={
                            role === "student"
                              ? "student@university.edu"
                              : "faculty@university.edu"
                          }
                          required
                          className="boxy-input"
                        />
                      </div>
                    </label>

                    <label className="boxy-field">
                      <span className="field-label">PASSWORD</span>
                      <div className="input-wrap has-action">
                        <input
                          type={showPassword ? "text" : "password"}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Enter your account password"
                          required
                          className="boxy-input"
                        />
                        <button
                          type="button"
                          className="input-eye-btn"
                          onClick={() => setShowPassword(!showPassword)}
                          title={showPassword ? "Hide password" : "Show password"}
                        >
                          {showPassword ? <I.EyeOff /> : <I.Eye />}
                        </button>
                      </div>
                    </label>

                    <button
                      type="submit"
                      className="auth-action-btn primary-action full"
                      disabled={busy}
                    >
                      {busy ? (
                        <>
                          <I.Loader2 className="spinning-loader" />
                          <span>SIGNING IN…</span>
                        </>
                      ) : (
                        <>
                          <span>SIGN IN AS {role.toUpperCase()}</span>
                          <I.ArrowRight />
                        </>
                      )}
                    </button>
                  </form>

                  <div className="auth-footer-prompt">
                    <span>Need to register your ID first?</span>{" "}
                    <button
                      type="button"
                      className="boxy-inline-link"
                      onClick={() => {
                        setMode("register");
                        setRole(role);
                      }}
                    >
                      Verify Record
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =============================================================
              MODE: ADMIN
              DIRECT LOGIN (no role selection, no need for register flow)
              ============================================================= */}
          {mode === "admin" && (
            <div className="auth-flow-container">
              <div className="auth-step-pane">
                <div className="pane-header">
                  <h2 className="pane-title">Admin Sign In</h2>
                  <p className="pane-subtitle">
                    Direct access for authorized university administrators and platform controllers.
                  </p>
                </div>

                <form onSubmit={submitLogin} className="boxy-form">
                  <label className="boxy-field">
                    <span className="field-label">ADMINISTRATIVE EMAIL</span>
                    <div className="input-wrap">
                      <input
                        autoFocus
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="admin@university.edu"
                        required
                        className="boxy-input"
                      />
                    </div>
                  </label>

                  <label className="boxy-field">
                    <span className="field-label">MASTER PASSWORD</span>
                    <div className="input-wrap has-action">
                      <input
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter administrator password"
                        required
                        className="boxy-input"
                      />
                      <button
                        type="button"
                        className="input-eye-btn"
                        onClick={() => setShowPassword(!showPassword)}
                        title={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? <I.EyeOff /> : <I.Eye />}
                      </button>
                    </div>
                  </label>

                  <button
                    type="submit"
                    className="auth-action-btn admin-action full"
                    disabled={busy}
                  >
                    {busy ? (
                      <>
                        <I.Loader2 className="spinning-loader" />
                        <span>AUTHENTICATING CONSOLE…</span>
                      </>
                    ) : (
                      <>
                        <span>SIGN IN AS ADMIN</span>
                        <I.ShieldCheck />
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
