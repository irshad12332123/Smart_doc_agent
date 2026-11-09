import { useState } from "react";
import * as I from "lucide-react";
import { authApi, userApi } from "../../api/client";
import { useTheme } from "../../context/ThemeContext";
import type { Session } from "../../types";

type AuthMode = "register" | "login" | "admin";
type RoleKind = "student" | "faculty";
type RegStep = "verify" | "activate" | "confirmed";
type LoginStep = "email" | "password";

export function Auth({ onSession }: { onSession: (value: Session) => void }) {
  const { theme, toggleTheme } = useTheme();

  // Primary mode: REGISTER, LOGIN, ADMIN
  const [mode, setMode] = useState<AuthMode>("login");

  // Role for Register and Login (faculty, student)
  const [role, setRole] = useState<RoleKind | null>(null);

  // Sub-steps
  const [regStep, setRegStep] = useState<RegStep>("verify");
  const [loginStep, setLoginStep] = useState<LoginStep>("email");

  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Verification record result for registration
  const [eligible, setEligible] = useState<{
    name: string;
    email: string;
    token: string;
  } | null>(null);

  // Confirmation email sent tracking
  const [confirmationEmail, setConfirmationEmail] = useState("");

  // Name verified during login
  const [loginVerifiedName, setLoginVerifiedName] = useState("");

  // Status & feedback
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [resending, setResending] = useState(false);

  // Switch top-level mode
  const handleSelectMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setError("");
    setSuccessMsg("");
    setRole(null);
    setRegStep("verify");
    setLoginStep("email");
    setPassword("");
    setConfirmPassword("");
  };

  // Switch role (faculty / student)
  const handleSelectRole = (nextRole: RoleKind) => {
    setRole(nextRole);
    setError("");
    setSuccessMsg("");
    setRegStep("verify");
    setLoginStep("email");
  };

  // Back button handler
  const handleBack = () => {
    setError("");
    setSuccessMsg("");
    if (mode === "register") {
      if (regStep === "confirmed") {
        setRegStep("verify");
      } else if (regStep === "activate") {
        setRegStep("verify");
      } else {
        setRole(null);
      }
    } else if (mode === "login") {
      if (loginStep === "password") {
        setLoginStep("email");
        setPassword("");
      } else if (role !== null) {
        setRole(null);
      }
    }
  };

  // =========================================================================
  // REGISTER FLOW
  // =========================================================================

  // Step 1 (Register): Check email eligibility in DB
  const submitVerifyEmailForRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!role || !email.trim()) return;
    setBusy(true);
    setError("");
    setSuccessMsg("");

    try {
      const result = await authApi.check(email.trim(), role, "register");
      if (result.status === "eligible" && result.name && result.registration_token) {
        setEligible({
          name: result.name,
          email: result.email || email.trim(),
          token: result.registration_token,
        });
        setRegStep("activate");
      } else if (result.status === "already registered" || result.status === "registered") {
        setError("Either user doesn't exist or already registered.");
      } else {
        setError(result.message || "Either user doesn't exist or already registered.");
      }
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Either user doesn't exist or already registered.")
          : "Either user doesn't exist or already registered.",
      );
    } finally {
      setBusy(false);
    }
  };

  // Step 2 (Register): Set password & initiate Supabase registration with confirmation mail
  const submitRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eligible || !password) return;
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (confirmPassword && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    setSuccessMsg("");

    try {
      await authApi.register(eligible.token, password, eligible.email, role || undefined);
      setConfirmationEmail(eligible.email);
      setRegStep("confirmed");
      setSuccessMsg("Registration initiated! A verification email has been sent by Supabase.");
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

  // =========================================================================
  // LOGIN FLOW
  // =========================================================================

  // Step 1 (Login): Verify email exists in DB and is already registered
  const submitCheckEmailForLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!role || !email.trim()) return;
    setBusy(true);
    setError("");
    setSuccessMsg("");

    try {
      const result = await authApi.check(email.trim(), role, "login");
      if (result.status === "registered" || result.status === "already registered") {
        setLoginVerifiedName(result.name || "");
        setLoginStep("password");
      } else {
        setError("Account is not registered. Please register.");
      }
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Account is not registered. Please register.")
          : "Account is not registered. Please register.",
      );
    } finally {
      setBusy(false);
    }
  };

  // Step 2 (Login): Enter password and authenticate
  const submitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setBusy(true);
    setError("");
    setSuccessMsg("");

    try {
      const login = await authApi.login(email.trim(), password, role || undefined);
      const me = await userApi.profile(login.access_token);
      onSession({ ...login, ...me });
    } catch (err: unknown) {
      const msg =
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Invalid email or password.")
          : "Invalid credentials. Please verify your email and password.";
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  // Resend confirmation email helper
  const handleResendConfirmation = async (emailToResend: string) => {
    if (!emailToResend.trim()) return;
    setResending(true);
    try {
      await authApi.resendConfirmation(emailToResend.trim());
      setSuccessMsg("Confirmation email has been resent. Please check your inbox!");
      setError("");
    } catch (err: unknown) {
      setError(
        typeof err === "object" && err && "message" in err
          ? String((err as { message?: unknown }).message ?? "Could not resend email.")
          : "Could not resend confirmation email.",
      );
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Top right theme toggle */}
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

      {/* RIGHT: Boxy Interactive Auth Card */}
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
                {mode === "register" && (error.toLowerCase().includes("already registered") || error.toLowerCase().includes("either user")) && (
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
                {mode === "login" && error.toLowerCase().includes("not registered") && (
                  <button
                    type="button"
                    className="alert-link-btn"
                    onClick={() => {
                      setMode("register");
                      setError("");
                    }}
                  >
                    Switch to Register →
                  </button>
                )}
                {error.toLowerCase().includes("confirm your email") && (
                  <button
                    type="button"
                    className="alert-link-btn"
                    disabled={resending}
                    onClick={() => handleResendConfirmation(email)}
                  >
                    {resending ? "Resending…" : "Resend Confirmation Email →"}
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
                      Choose whether you are registering as Faculty or Student.
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
                    <span>Already have an account?</span>{" "}
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

              {/* Step 2: Verification with Official Email */}
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
                    <h2 className="pane-title">Verify Official Email</h2>
                    <p className="pane-subtitle">
                      Enter your official university email to verify eligibility for registration.
                    </p>
                  </div>

                  <form onSubmit={submitVerifyEmailForRegister} className="boxy-form">
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
                              ? "e.g. 24031009001@rayatbahrauniversity.edu.in"
                              : "e.g. faculty@rayatbahrauniversity.edu.in"
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
                          <span>CHECKING RECORD…</span>
                        </>
                      ) : (
                        <>
                          <span>VERIFY & PROCEED</span>
                          <I.ArrowRight />
                        </>
                      )}
                    </button>
                  </form>

                  <div className="auth-footer-prompt">
                    <span>Already registered?</span>{" "}
                    <button
                      type="button"
                      className="boxy-inline-link"
                      onClick={() => {
                        setMode("login");
                        setRole(role);
                      }}
                    >
                      Sign In
                    </button>
                  </div>
                </div>
              )}

              {/* Step 3: Record Verified -> Create Password & Register */}
              {role !== null && regStep === "activate" && eligible && (
                <div className="auth-step-pane">
                  <button type="button" className="auth-back-btn" onClick={handleBack}>
                    <I.ArrowLeft />
                    <span>BACK</span>
                  </button>

                  <div className="pane-header">
                    <span className="boxy-eyebrow">STEP 2: CREATE PASSWORD</span>
                    <h2 className="pane-title">Welcome, {eligible.name.split(" ")[0]}</h2>
                    <p className="pane-subtitle">
                      Your university record is verified. Set your password to complete registration.
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

                    <label className="boxy-field">
                      <span className="field-label">CONFIRM PASSWORD</span>
                      <div className="input-wrap">
                        <input
                          type={showPassword ? "text" : "password"}
                          minLength={8}
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="Re-enter your password"
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
                          <span>SENDING CONFIRMATION EMAIL…</span>
                        </>
                      ) : (
                        <>
                          <span>REGISTER & SEND CONFIRMATION EMAIL</span>
                          <I.ArrowRight />
                        </>
                      )}
                    </button>
                  </form>
                </div>
              )}

              {/* Step 4: Confirmation Email Dispatched Screen */}
              {role !== null && regStep === "confirmed" && (
                <div className="auth-step-pane">
                  <div className="pane-header">
                    <span className="boxy-eyebrow">STEP 3: EMAIL VERIFICATION</span>
                    <h2 className="pane-title">Check Your Email</h2>
                    <p className="pane-subtitle">
                      A confirmation email has been sent through Supabase to{" "}
                      <strong>{confirmationEmail}</strong>.
                    </p>
                  </div>

                  <div className="boxy-verified-banner" style={{ borderLeftColor: "var(--accent)" }}>
                    <div className="verified-badge-icon">
                      <I.MailCheck />
                    </div>
                    <div className="verified-details">
                      <span className="verified-label">CONFIRMATION LINK DISPATCHED</span>
                      <strong className="verified-email">{confirmationEmail}</strong>
                      <span className="verified-name">
                        Please open the link sent to your email to confirm your account before logging in.
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "16px" }}>
                    <button
                      type="button"
                      className="auth-action-btn primary-action full"
                      onClick={() => {
                        setMode("login");
                        setRole(role);
                        setEmail(confirmationEmail);
                        setPassword("");
                        setLoginStep("password");
                        setError("");
                        setSuccessMsg("Please confirm your email first, then enter your password to sign in.");
                      }}
                    >
                      <span>PROCEED TO SIGN IN</span>
                      <I.ArrowRight />
                    </button>

                    <button
                      type="button"
                      className="boxy-inline-link"
                      style={{ textAlign: "center", marginTop: "8px" }}
                      disabled={resending}
                      onClick={() => handleResendConfirmation(confirmationEmail)}
                    >
                      {resending ? "Resending email…" : "Didn't receive email? Resend Confirmation Email"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =============================================================
              MODE: LOGIN
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

              {/* Step 2: Email Entry & Verification */}
              {role !== null && loginStep === "email" && (
                <div className="auth-step-pane">
                  <button type="button" className="auth-back-btn" onClick={handleBack}>
                    <I.ArrowLeft />
                    <span>CHANGE ROLE</span>
                  </button>

                  <div className="pane-header">
                    <span className="boxy-eyebrow">
                      {role.toUpperCase()} WORKSPACE SIGN IN
                    </span>
                    <h2 className="pane-title">Enter Official Email</h2>
                    <p className="pane-subtitle">
                      Enter your verified university email to proceed to sign in.
                    </p>
                  </div>

                  <form onSubmit={submitCheckEmailForLogin} className="boxy-form">
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

                    <button
                      type="submit"
                      className="auth-action-btn primary-action full"
                      disabled={busy}
                    >
                      {busy ? (
                        <>
                          <I.Loader2 className="spinning-loader" />
                          <span>VERIFYING EMAIL…</span>
                        </>
                      ) : (
                        <>
                          <span>CONTINUE</span>
                          <I.ArrowRight />
                        </>
                      )}
                    </button>
                  </form>

                  <div className="auth-footer-prompt">
                    <span>Need to register your email first?</span>{" "}
                    <button
                      type="button"
                      className="boxy-inline-link"
                      onClick={() => {
                        setMode("register");
                        setRole(role);
                      }}
                    >
                      Begin Registration
                    </button>
                  </div>
                </div>
              )}

              {/* Step 3: Password Entry & Authentication */}
              {role !== null && loginStep === "password" && (
                <div className="auth-step-pane">
                  <button type="button" className="auth-back-btn" onClick={handleBack}>
                    <I.ArrowLeft />
                    <span>CHANGE EMAIL</span>
                  </button>

                  <div className="pane-header">
                    <span className="boxy-eyebrow">
                      {role.toUpperCase()} SIGN IN
                    </span>
                    <h2 className="pane-title">
                      Welcome Back{loginVerifiedName ? `, ${loginVerifiedName.split(" ")[0]}` : ""}
                    </h2>
                    <p className="pane-subtitle">
                      Enter password for <strong>{email}</strong>.
                    </p>
                  </div>

                  <form onSubmit={submitLogin} className="boxy-form">
                    <label className="boxy-field">
                      <span className="field-label">PASSWORD</span>
                      <div className="input-wrap has-action">
                        <input
                          autoFocus
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
                    <span>Didn't receive or confirm your email?</span>{" "}
                    <button
                      type="button"
                      className="boxy-inline-link"
                      disabled={resending}
                      onClick={() => handleResendConfirmation(email)}
                    >
                      {resending ? "Resending…" : "Resend Confirmation Link"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =============================================================
              MODE: ADMIN
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
