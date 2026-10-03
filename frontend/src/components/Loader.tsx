import React from "react";
import "./Loader.css";

/**
 * Shared loading UI for the admin panel.
 *
 * - "page"    : centred spinner + label, for the first load of a section
 * - "overlay" : translucent layer over a card/table while existing data refreshes
 *               (the parent needs the `has-loader-overlay` class)
 * - "inline"  : tiny spinner that sits inside a button next to its label
 *
 * The spinner look itself (`.spinner`) lives in Dashboard.css.
 */
type LoaderProps = {
  variant?: "page" | "overlay" | "inline";
  label?: string;
};

export const Loader: React.FC<LoaderProps> = ({ variant = "page", label = "Loading..." }) => {
  if (variant === "inline") {
    return <span className="spinner spinner--btn" role="status" aria-label={label} />;
  }

  if (variant === "overlay") {
    return (
      <div className="loader-overlay" role="status" aria-live="polite">
        <span className="spinner spinner--lg" />
        <span>{label}</span>
      </div>
    );
  }

  return (
    <div className="page-loader" role="status" aria-live="polite">
      <span className="spinner spinner--lg" />
      <span>{label}</span>
    </div>
  );
};

/** Slim bar fixed to the top of the screen, shown while data refreshes in the background. */
export const TopProgressBar: React.FC<{ active: boolean }> = ({ active }) => (
  <div className={`top-progress${active ? " is-active" : ""}`} aria-hidden="true">
    <div className="top-progress-bar" />
  </div>
);
