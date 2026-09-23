/**
 * Application configuration.
 *
 * Reads environment variables exposed by Vite (prefixed with VITE_).
 * Falls back to sensible defaults for local development.
 */

export const config = {
  /** Base URL for the backend API (no trailing slash). */
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
} as const;
