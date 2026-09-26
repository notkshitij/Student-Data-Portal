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

  const statusText: Record<ConnectionStatus, string> = {
    checking: "Checking…",
    connected: "Connected",
    disconnected: "Disconnected",
  };

  return (
    <div className="app-container">
      {/* Logo */}
      <div className="app-logo" aria-hidden="true">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5"
          />
        </svg>
      </div>

      {/* Header */}
      <header className="app-header">
        <h1 className="app-title">Student Data Verification Portal</h1>
        <p className="app-subtitle">
          Securely verify and collect student information with cell-level
          precision. Upload once, collect only what's missing.
        </p>
      </header>

      {/* Backend Status */}
      <div
        id="backend-status-card"
        className={`status-card ${status}`}
        role="status"
        aria-live="polite"
      >
        <div className={`status-indicator ${status}`} />
        <div className="status-content">
          <span className="status-label">Backend Status</span>
          <span id="backend-status-value" className={`status-value ${status}`}>
            {statusText[status]}
          </span>
        </div>
      </div>

      {/* Authentication */}
      <div className="auth-section" style={{ marginTop: "2rem", display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
        {isInitializingAuth ? (
          <div className="auth-loading" style={{ color: "#666" }}>
            Loading authentication state...
          </div>
        ) : isLoggedIn ? (
          <div className="auth-success" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem", width: "100%" }}>
            <div style={{ color: "green", fontWeight: "bold" }}>
              Successfully authenticated as {user?.email} ({user?.role})!
            </div>
            
            {user?.role === "STUDENT" ? (
              <div style={{ width: "100%", maxWidth: "800px", marginTop: "2rem" }}>
                <StudentDashboard user={user} />
              </div>
            ) : user?.role === "ADMIN" ? (
              <div style={{ width: "100%", marginTop: "2rem" }}>
                <AdminDashboard user={user} onLogout={handleLogout} />
              </div>
            ) : (
              <div style={{ padding: "2rem", textAlign: "center", color: "#666" }}>
                Unknown role: {user?.role}
              </div>
            )}

            {user?.role !== "ADMIN" && (
              <button 
                onClick={handleLogout}
                style={{
                  padding: "0.5rem 1rem",
                  fontSize: "0.875rem",
                  borderRadius: "0.375rem",
                  border: "1px solid #ccc",
                  backgroundColor: "#f9f9f9",
                  cursor: "pointer",
                  marginTop: "2rem"
                }}
              >
                Sign Out
              </button>
            )}
          </div>
        ) : (
          <>
            <button 
              onClick={() => googleLogin()}
              disabled={isLoggingIn || status !== "connected"}
              className="google-login-btn"
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "1rem",
                borderRadius: "0.375rem",
                border: "1px solid #ccc",
                backgroundColor: "#fff",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                fontWeight: 500
              }}
            >
              <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/><path fill="#FF3D00" d="m6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C16.318 4 9.656 8.337 6.306 14.691z"/><path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"/><path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/></svg>
              {isLoggingIn ? "Signing in..." : "Sign in with Google"}
            </button>
            {authError && (
              <div className="auth-error" style={{ color: "red", marginTop: "1rem" }}>
                {authError}
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <footer className="app-footer">
        Endpoint: <code>{config.apiBaseUrl}/api/health</code>
      </footer>
    </div>
  );
}

export default App;
