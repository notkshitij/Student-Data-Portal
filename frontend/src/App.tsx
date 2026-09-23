import { useEffect, useState } from "react";
import { config } from "./config";
import "./App.css";

type ConnectionStatus = "checking" | "connected" | "disconnected";

function App() {
  const [status, setStatus] = useState<ConnectionStatus>("checking");

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

      {/* Footer */}
      <footer className="app-footer">
        Endpoint: <code>{config.apiBaseUrl}/api/health</code>
      </footer>
    </div>
  );
}

export default App;
