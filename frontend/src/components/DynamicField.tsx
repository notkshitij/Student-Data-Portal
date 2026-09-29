import React from "react";
import type { StudentCampaignFieldResponse } from "../types";

interface DynamicFieldProps {
  field: StudentCampaignFieldResponse;
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export const DynamicField: React.FC<DynamicFieldProps> = ({ field, value, onChange, error, disabled }) => {
  const config = field.validation_config;
  
  let inputElement = null;
  
  if (field.requires_student_input) {
    const isRequired = config?.rules?.required;
    const type = config?.type || "text";
    const isFilled = (value || "").trim() !== "";
    const wrapperClass = [
      "dynamic-field",
      "dynamic-field--editable",
      isFilled ? "is-filled" : "",
      error ? "has-error" : "",
      type === "textarea" ? "dynamic-field--wide" : "",
    ].filter(Boolean).join(" ");
    
    if (type === "textarea") {
      inputElement = (
        <textarea
          id={`field-${field.field_id}`}
          className={`field-input ${error ? "field-error" : ""}`}
          value={value || ""}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={`Enter ${field.field_name}...`}
          disabled={disabled}
          rows={3}
        />
      );
    } else if (type === "select") {
      inputElement = (
        <select
          id={`field-${field.field_id}`}
          className={`field-input ${error ? "field-error" : ""}`}
          value={value || ""}
          onChange={(e) => onChange?.(e.target.value)}
          disabled={disabled}
        >
          <option value="">-- Select an option --</option>
          {(config?.rules?.options || []).map((opt: string) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      );
    } else {
      inputElement = (
        <input
          type={type === "email" ? "email" : type === "number" ? "number" : type === "date" ? "date" : type === "phone" ? "tel" : "text"}
          inputMode={type === "phone" ? "tel" : type === "number" ? "numeric" : type === "email" ? "email" : undefined}
          autoComplete="off"
          id={`field-${field.field_id}`}
          className={`field-input ${error ? "field-error" : ""}`}
          value={value || ""}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={`Enter ${field.field_name}...`}
          disabled={disabled}
        />
      );
    }
    
    return (
      <div className={wrapperClass}>
        <label htmlFor={`field-${field.field_id}`} className="field-label">
          {field.field_name}
          {isRequired && <span className="required-marker">*</span>}
          {isFilled && !error && (
            <svg className="field-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          )}
        </label>
        {inputElement}
        {error && <div className="field-error-text" style={{ color: "#ef4444", fontSize: "0.875rem", marginTop: "0.25rem" }}>{error}</div>}
      </div>
    );
  }

  // Read-only field
  return (
    <div className="dynamic-field dynamic-field--readonly">
      <label htmlFor={`field-${field.field_id}`} className="field-label">
        {field.field_name}
      </label>
      <div className="field-readonly-value">
        <span className="field-readonly-text">
          {field.value || <span className="empty-value">No value provided</span>}
        </span>
        <svg className="field-lock" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="5" y="11" width="14" height="10" rx="2" />
          <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        </svg>
      </div>
    </div>
  );
};
