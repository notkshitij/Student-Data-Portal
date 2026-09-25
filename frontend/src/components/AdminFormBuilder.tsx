import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AdminFormConfigResponse, AdminFormField, FieldValidationConfig, FieldType } from "../types/admin";

interface AdminFormBuilderProps {
  campaignId: string;
  disabled: boolean;
}

export const AdminFormBuilder: React.FC<AdminFormBuilderProps> = ({ campaignId, disabled }) => {
  const [fields, setFields] = useState<AdminFormField[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchFormConfig();
  }, [campaignId]);

  const fetchFormConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/form`, {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("Failed to load form configuration.");
      }
      const data: AdminFormConfigResponse = await response.json();
      setFields(data.fields);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    setError(null);
    
    // Only send the fields that require student input (collect fields)
    const updatePayload = {
      fields: fields
        .filter(f => f.requires_student_input && f.validation_config)
        .map(f => ({
          id: f.id,
          validation_config: f.validation_config!
        }))
    };

    try {
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/form`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(updatePayload)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Failed to save form configuration.");
      }
      
      setSaveMessage(data.message || "Form configuration saved successfully!");
      await fetchFormConfig(); // Refresh after save to get canonical normalized values
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during saving.");
    } finally {
      setSaving(false);
    }
  };

  const updateFieldConfig = (fieldId: string, updates: Partial<FieldValidationConfig>) => {
    setFields(prev => prev.map(f => {
      if (f.id === fieldId && f.validation_config) {
        return {
          ...f,
          validation_config: {
            ...f.validation_config,
            ...updates,
            rules: {
              ...f.validation_config.rules,
              ...(updates.rules || {})
            }
          }
        };
      }
      return f;
    }));
  };

  if (loading) return <div>Loading form configuration...</div>;

  return (
    <div className="admin-form-builder" style={{ marginTop: "2rem" }}>
      <h3>Form Configuration</h3>
      <p style={{ color: "#6b7280", marginBottom: "1rem" }}>
        Configure the validation rules for data collected from students. 
        Only fields marked with [COLLECT] in the original Excel file can be configured.
      </p>

      {saveMessage && (
        <div style={{ padding: "1rem", backgroundColor: "#ecfdf5", color: "#059669", borderRadius: "8px", marginBottom: "1rem" }}>
          {saveMessage}
        </div>
      )}
      
      {error && (
        <div className="error-state" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {fields.map(field => (
          <div key={field.id} style={{
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "1rem",
            backgroundColor: field.requires_student_input ? "#ffffff" : "#f9fafb"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <strong>{field.field_name}</strong>
              <span style={{ fontSize: "0.875rem", color: field.requires_student_input ? "#4f46e5" : "#9ca3af" }}>
                {field.requires_student_input ? "Student Input: Yes" : "Not collected from students"}
              </span>
            </div>

            {field.requires_student_input && field.validation_config && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1rem", marginTop: "1rem" }}>
                
                <div className="form-group">
                  <label className="form-label">Type</label>
                  <select 
                    className="form-input" 
                    value={field.validation_config.type}
                    disabled={disabled}
                    onChange={(e) => updateFieldConfig(field.id, { type: e.target.value as FieldType, rules: { required: field.validation_config!.rules.required } })}
                  >
                    <option value="text">Text</option>
                    <option value="textarea">Text Area</option>
                    <option value="number">Number</option>
                    <option value="email">Email</option>
                    <option value="phone">Phone</option>
                    <option value="date">Date</option>
                    <option value="select">Select</option>
                  </select>
                </div>

                <div className="form-group" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <input 
                    type="checkbox" 
                    id={`req-${field.id}`}
                    checked={field.validation_config.rules.required || false}
                    disabled={disabled}
                    onChange={(e) => updateFieldConfig(field.id, { rules: { required: e.target.checked } })}
                  />
                  <label htmlFor={`req-${field.id}`} style={{ margin: 0, fontWeight: "normal" }}>Required</label>
                </div>

                {/* Type-Specific Rules */}
                {(field.validation_config.type === "text" || field.validation_config.type === "textarea") && (
                  <div style={{ display: "flex", gap: "1rem" }}>
                    <div className="form-group">
                      <label className="form-label">Min Length</label>
                      <input 
                        type="number" 
                        className="form-input" 
                        value={field.validation_config.rules.min_length ?? ""}
                        disabled={disabled}
                        onChange={(e) => updateFieldConfig(field.id, { rules: { min_length: e.target.value ? parseInt(e.target.value) : null } })}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Max Length</label>
                      <input 
                        type="number" 
                        className="form-input" 
                        value={field.validation_config.rules.max_length ?? ""}
                        disabled={disabled}
                        onChange={(e) => updateFieldConfig(field.id, { rules: { max_length: e.target.value ? parseInt(e.target.value) : null } })}
                      />
                    </div>
                  </div>
                )}

                {field.validation_config.type === "number" && (
                  <div style={{ display: "flex", gap: "1rem" }}>
                    <div className="form-group">
                      <label className="form-label">Min Value</label>
                      <input 
                        type="number" 
                        className="form-input" 
                        value={field.validation_config.rules.min_value ?? ""}
                        disabled={disabled}
                        onChange={(e) => updateFieldConfig(field.id, { rules: { min_value: e.target.value ? parseFloat(e.target.value) : null } })}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Max Value</label>
                      <input 
                        type="number" 
                        className="form-input" 
                        value={field.validation_config.rules.max_value ?? ""}
                        disabled={disabled}
                        onChange={(e) => updateFieldConfig(field.id, { rules: { max_value: e.target.value ? parseFloat(e.target.value) : null } })}
                      />
                    </div>
                  </div>
                )}

                {field.validation_config.type === "email" && (
                  <div className="form-group">
                    <label className="form-label">Allowed Domains (comma-separated)</label>
                    <input 
                      type="text" 
                      className="form-input" 
                      placeholder="e.g. example.com, poornima.org"
                      disabled={disabled}
                      value={(field.validation_config.rules.allowed_domains || []).join(", ")}
                      onChange={(e) => updateFieldConfig(field.id, { rules: { allowed_domains: e.target.value ? e.target.value.split(",").map(d => d.trim()) : null } })}
                    />
                  </div>
                )}

                {field.validation_config.type === "select" && (
                  <div className="form-group">
                    <label className="form-label">Options (comma-separated)</label>
                    <input 
                      type="text" 
                      className="form-input" 
                      placeholder="e.g. Male, Female, Other"
                      disabled={disabled}
                      value={(field.validation_config.rules.options || []).join(", ")}
                      onChange={(e) => updateFieldConfig(field.id, { rules: { options: e.target.value ? e.target.value.split(",").map(o => o.trim()) : [] } })}
                    />
                  </div>
                )}

              </div>
            )}
          </div>
        ))}
      </div>

      {!disabled && (
        <div style={{ marginTop: "1.5rem" }}>
          <button 
            className="btn btn-primary" 
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      )}
    </div>
  );
};
