/**
 * Application configuration.
 *
 * Reads environment variables exposed by Vite (prefixed with VITE_).
 * Falls back to sensible defaults for local development.
 */

export const config = {
  /** Base URL for the backend API (no trailing slash). */
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  /** Google OAuth Client ID */
  googleClientId: import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "your-google-client-id.apps.googleusercontent.com",
} as const;
