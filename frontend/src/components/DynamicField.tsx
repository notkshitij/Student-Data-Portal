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
          type={type === "email" ? "email" : type === "number" ? "number" : type === "date" ? "date" : "text"}
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
      <div className="dynamic-field">
        <label htmlFor={`field-${field.field_id}`} className="field-label">
          {field.field_name}
          {isRequired && <span className="required-marker">*</span>}
        </label>
        {inputElement}
        {error && <div className="field-error-text" style={{ color: "#ef4444", fontSize: "0.875rem", marginTop: "0.25rem" }}>{error}</div>}
      </div>
    );
  }

  // Read-only field
  return (
    <div className="dynamic-field">
      <label htmlFor={`field-${field.field_id}`} className="field-label">
        {field.field_name}
      </label>
      <div className="field-readonly-value">
        {field.value || <span className="empty-value">No value provided</span>}
      </div>
    </div>
  );
};
