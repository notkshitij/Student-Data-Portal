import { useEffect, useState } from "react";
import { useGoogleLogin } from "@react-oauth/google";
import { config } from "./config";
import { StudentDashboard } from "./components/StudentDashboard";
import { AdminDashboard } from "./components/AdminDashboard";
import "./App.css";
import "./Dashboard.css";

type ConnectionStatus = "checking" | "connected" | "disconnected";

function App() {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isInitializingAuth, setIsInitializingAuth] = useState(true);
  const [user, setUser] = useState<any>(null);

  const googleLogin = useGoogleLogin({
    flow: "auth-code",
    onSuccess: async (codeResponse) => {
      setIsLoggingIn(true);
      setAuthError(null);
      try {
        const res = await fetch(`${config.apiBaseUrl}/api/auth/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code: codeResponse.code }),
          credentials: "include",
        });

        if (!res.ok) {
          throw new Error("Login failed");
        }

        // Fetch user data after successful login
        const userRes = await fetch(`${config.apiBaseUrl}/api/auth/me`, {
          credentials: "include",
        });
        if (userRes.ok) {
          const userData = await userRes.json();
          setUser(userData);
          setIsLoggedIn(true);
        } else {
          throw new Error("Failed to fetch user data");
        }
      } catch (err) {
        setAuthError("Your Google account could not be used to access this portal.");
      } finally {
        setIsLoggingIn(false);
      }
    },
    onError: () => {
      setAuthError("Your Google account could not be used to access this portal.");
    },
  });

  const handleLogout = async () => {
    try {
      await fetch(`${config.apiBaseUrl}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (e) {
      console.error("Logout error", e);
    } finally {
      setIsLoggedIn(false);
      setUser(null);
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const response = await fetch(`${config.apiBaseUrl}/api/health`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled && data.status === "ok") {
          setStatus("connected");
        } else if (!cancelled) {
          setStatus("disconnected");
        }
      } catch {
        if (!cancelled) {
          setStatus("disconnected");
        }
      }
    }

    checkHealth();

    // Check if user is already logged in
    async function checkAuth() {
      try {
        const response = await fetch(`${config.apiBaseUrl}/api/auth/me`, {
          credentials: "include",
        });
        if (response.ok) {
          const userData = await response.json();
          if (!cancelled) {
            setUser(userData);
            setIsLoggedIn(true);
          }
        }
      } catch (e) {
        console.error("Failed to fetch current user", e);
      } finally {
        if (!cancelled) {
          setIsInitializingAuth(false);
        }
      }
    }

    checkAuth();

    return () => {
      cancelled = true;
    };
  }, []);

  const showDashboard = isLoggedIn && !isInitializingAuth;

  // ---- Signed in: no hero, the dashboard goes straight into the photo card ----
  if (showDashboard) {
    const roleLabel =
      user?.role === "ADMIN" ? "Admin" : user?.role === "STUDENT" ? "Student" : user?.role;

    return (
      <div className="app-container">
        <div className="dash-page">
          <div className="dash-topbar">
            <span className="role-badge">{roleLabel}</span>
          </div>

          {user?.role === "ADMIN" && (
            <main className="dashboard-shell dashboard-shell--admin">
              <AdminDashboard user={user} onLogout={handleLogout} />
            </main>
          )}

          {user?.role === "STUDENT" && (
            <main className="dashboard-shell dashboard-shell--student">
              <StudentDashboard user={user} />
              <div className="dashboard-shell-footer">
                <button className="btn-signout" onClick={handleLogout}>
                  Sign Out
                </button>
              </div>
            </main>
          )}

          {user?.role !== "ADMIN" && user?.role !== "STUDENT" && (
            <main className="dashboard-shell dashboard-shell--student">
              <p style={{ textAlign: "center", color: "#666" }}>
                Unknown role: {user?.role}
              </p>
              <div className="dashboard-shell-footer">
                <button className="btn-signout" onClick={handleLogout}>
                  Sign Out
                </button>
              </div>
            </main>
          )}
        </div>
      </div>
    );
  }

  // ---- Signed out: full-screen hero with the login button ----
  return (
    <div className="app-container">
      <section className="hero">
        {/* Logo */}
        <div className="app-logo" aria-hidden="true">
          <img
            src="/logo.png"
            alt="Student Data Verification Portal Logo"
            className="app-logo-img"
          />
        </div>

        {/* Header */}
        <header className="app-header">
          <h1 className="app-title">
            Upload once.
            <br />
            Collect only what's missing.
          </h1>
          <p className="app-subtitle">
            Securely verify and collect student information with cell-level
            precision.
          </p>
        </header>

        {/* Authentication */}
        <div className="auth-section">
          {isInitializingAuth ? (
            <div className="auth-loading">Loading authentication state...</div>
          ) : (
            <>
              <button
                onClick={() => googleLogin()}
                disabled={isLoggingIn || status !== "connected"}
                className="google-login-btn"
                style={{
                  padding: "0.85rem 1.75rem",
                  fontSize: "1rem",
                  borderRadius: "999px",
                  border: "1px solid rgba(20, 24, 29, 0.15)",
                  backgroundColor: "#ffffff",
                  color: "#14181d",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.6rem",
                  fontWeight: 700,
                  boxShadow: "0 10px 30px rgba(0, 0, 0, 0.25)"
                }}
              >
                <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/><path fill="#FF3D00" d="m6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C16.318 4 9.656 8.337 6.306 14.691z"/><path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"/><path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/></svg>
                {isLoggingIn ? "Signing in..." : "Sign in with Google"}
              </button>
              {authError && <div className="auth-error">{authError}</div>}
            </>
          )}
        </div>
      </section>
    </div>
  );
}

export default App;
