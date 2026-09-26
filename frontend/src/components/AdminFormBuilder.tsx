import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AdminFormConfigResponse, AdminFormField, FieldValidationConfig, FieldType } from "../types/admin";

interface AdminFormBuilderProps {
  campaignId: string;
  disabled: boolean;
  campaignStatus?: string;
}

export const AdminFormBuilder: React.FC<AdminFormBuilderProps> = ({ campaignId, disabled, campaignStatus }) => {
  const [allFields, setAllFields] = useState<AdminFormField[]>([]);
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
      setAllFields(data.fields.sort((a, b) => a.field_order - b.field_order));
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const collectFields = allFields.filter(f => f.requires_student_input);
  // Sort collectFields by their current relative ordering
  collectFields.sort((a, b) => a.field_order - b.field_order);

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    setError(null);
    
    // We update the field_order on the backend based on their index in collectFields
    // We preserve the ordering of non-collect fields? The backend doesn't let us update non-collect fields.
    // So we just send the collectFields with their new field_order.
    const updatePayload = {
      fields: collectFields.map((f, idx) => ({
        id: f.id,
        field_order: idx, // New sequential order
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
      await fetchFormConfig(); // Refresh after save
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during saving.");
    } finally {
      setSaving(false);
    }
  };

  const updateFieldConfig = (fieldId: string, updates: Partial<FieldValidationConfig>) => {
    setAllFields(prev => prev.map(f => {
      if (f.id === fieldId && f.validation_config) {
        let newRules: any = {
          ...f.validation_config.rules,
          ...(updates.rules || {})
        };
        
        // If type changes, reset rules to just 'required'
        if (updates.type && updates.type !== f.validation_config.type) {
          newRules = { required: newRules.required };
          if (updates.type === 'select') {
             newRules.options = [];
          }
        }

        return {
          ...f,
          validation_config: {
            ...f.validation_config,
            ...updates,
            rules: newRules
          }
        };
      }
      return f;
    }));
  };

  const moveField = (index: number, direction: "up" | "down") => {
    if (disabled) return;
    const newCollectFields = [...collectFields];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    
    if (targetIndex < 0 || targetIndex >= newCollectFields.length) return;
    
    const temp = newCollectFields[index];
    newCollectFields[index] = newCollectFields[targetIndex];
    newCollectFields[targetIndex] = temp;
    
    // Re-assign field orders based on array position so they sort correctly
    const updatedCollectFields = newCollectFields.map((f, i) => ({ ...f, field_order: i }));
    
    // Merge back into allFields
    setAllFields(prev => prev.map(f => {
      const updated = updatedCollectFields.find(uf => uf.id === f.id);
      return updated ? updated : f;
    }));
  };

  const handleOptionChange = (fieldId: string, index: number, newValue: string) => {
    setAllFields(prev => prev.map(f => {
      if (f.id === fieldId && f.validation_config?.type === 'select') {
        const newOptions = [...(f.validation_config.rules.options || [])];
        newOptions[index] = newValue;
        return {
          ...f,
          validation_config: { ...f.validation_config, rules: { ...f.validation_config.rules, options: newOptions } }
        };
      }
      return f;
    }));
  };

  const addOption = (fieldId: string) => {
    setAllFields(prev => prev.map(f => {
      if (f.id === fieldId && f.validation_config?.type === 'select') {
        const newOptions = [...(f.validation_config.rules.options || []), "New Option"];
        return {
          ...f,
          validation_config: { ...f.validation_config, rules: { ...f.validation_config.rules, options: newOptions } }
        };
      }
      return f;
    }));
  };

  const removeOption = (fieldId: string, index: number) => {
    setAllFields(prev => prev.map(f => {
      if (f.id === fieldId && f.validation_config?.type === 'select') {
        const newOptions = [...(f.validation_config.rules.options || [])];
        newOptions.splice(index, 1);
        return {
          ...f,
          validation_config: { ...f.validation_config, rules: { ...f.validation_config.rules, options: newOptions } }
        };
      }
      return f;
    }));
  };

  if (loading) return <div className="loading-state">Loading form configuration...</div>;

  if (collectFields.length === 0) {
    return (
      <div style={{ marginTop: "2rem", padding: "2rem", backgroundColor: "#f9fafb", borderRadius: "8px", textAlign: "center" }}>
        <h3 style={{ color: "#374151" }}>No Collectable Fields</h3>
        <p style={{ color: "#6b7280" }}>
          There are no fields marked for collection (e.g., [COLLECT]) in this campaign's imported data.
          No student form will be displayed.
        </p>
      </div>
    );
  }

  return (
    <div className="admin-form-builder" style={{ marginTop: "2rem" }}>
      <h3>Form Builder</h3>
      <p style={{ color: "#6b7280", marginBottom: "1rem" }}>
        Configure the information students must provide. These fields were identified from your imported data.
      </p>

      {saveMessage && (
        <div style={{ padding: "1rem", backgroundColor: "#ecfdf5", color: "#059669", borderRadius: "8px", marginBottom: "1rem" }}>
          {saveMessage}
        </div>
      )}
      
      {error && (
        <div className="error-state" style={{ marginBottom: "1rem", padding: "1rem", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "8px" }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", gap: "2rem" }}>
        {/* Builder Column */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "1rem" }}>
          <h4 style={{ marginBottom: "0.5rem", color: "#f1f5f9" }}>Available / Collectable Fields</h4>
          {collectFields.map((field, index) => (
            <div key={field.id} style={{
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
              padding: "1.5rem",
              backgroundColor: "#ffffff",
              boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
              color: "#111827"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                <div>
                  <strong style={{ fontSize: "1.1rem" }}>{field.field_name}</strong>
                  <div style={{ fontSize: "0.875rem", color: "#6b7280", marginTop: "0.25rem" }}>
                    Type: <span style={{ textTransform: "capitalize" }}>{field.validation_config?.type || "Text"}</span>
                  </div>
                </div>
                {!disabled && (
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button 
                      onClick={() => moveField(index, "up")} 
                      disabled={index === 0}
                      className="btn btn-secondary" 
                      style={{ padding: "0.25rem 0.5rem", fontSize: "0.875rem" }}
                      aria-label={`Move ${field.field_name} up`}
                    >
                      ↑ Move Up
                    </button>
                    <button 
                      onClick={() => moveField(index, "down")} 
                      disabled={index === collectFields.length - 1}
                      className="btn btn-secondary" 
                      style={{ padding: "0.25rem 0.5rem", fontSize: "0.875rem" }}
                      aria-label={`Move ${field.field_name} down`}
                    >
                      ↓ Move Down
                    </button>
                  </div>
                )}
              </div>

              {field.validation_config && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1rem" }}>
                  
                  <div className="dynamic-field">
                    <label className="field-label" htmlFor={`type-${field.id}`}>Field Type</label>
                    <select 
                      id={`type-${field.id}`}
                      className="field-input" 
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

                  <div className="dynamic-field" style={{ flexDirection: "row", alignItems: "center", gap: "0.5rem" }}>
                    <input 
                      type="checkbox" 
                      id={`req-${field.id}`}
                      checked={field.validation_config.rules.required || false}
                      disabled={disabled}
                      onChange={(e) => updateFieldConfig(field.id, { rules: { required: e.target.checked } })}
                    />
                    <label htmlFor={`req-${field.id}`} className="field-label" style={{ margin: 0, fontWeight: "normal" }}>Required field</label>
                  </div>

                  {/* Type-Specific Rules */}
                  {(field.validation_config.type === "text" || field.validation_config.type === "textarea") && (
                    <div style={{ display: "flex", gap: "1rem" }}>
                      <div className="dynamic-field">
                        <label className="field-label" htmlFor={`minlen-${field.id}`}>Min Length</label>
                        <input 
                          id={`minlen-${field.id}`}
                          type="number" 
                          className="field-input" 
                          value={field.validation_config.rules.min_length ?? ""}
                          disabled={disabled}
                          onChange={(e) => updateFieldConfig(field.id, { rules: { min_length: e.target.value ? parseInt(e.target.value) : null } })}
                        />
                      </div>
                      <div className="dynamic-field">
                        <label className="field-label" htmlFor={`maxlen-${field.id}`}>Max Length</label>
                        <input 
                          id={`maxlen-${field.id}`}
                          type="number" 
                          className="field-input" 
                          value={field.validation_config.rules.max_length ?? ""}
                          disabled={disabled}
                          onChange={(e) => updateFieldConfig(field.id, { rules: { max_length: e.target.value ? parseInt(e.target.value) : null } })}
                        />
                      </div>
                    </div>
                  )}

                  {field.validation_config.type === "number" && (
                    <div style={{ display: "flex", gap: "1rem" }}>
                      <div className="dynamic-field">
                        <label className="field-label" htmlFor={`minval-${field.id}`}>Min Value</label>
                        <input 
                          id={`minval-${field.id}`}
                          type="number" 
                          className="field-input" 
                          value={field.validation_config.rules.min_value ?? ""}
                          disabled={disabled}
                          onChange={(e) => updateFieldConfig(field.id, { rules: { min_value: e.target.value ? parseFloat(e.target.value) : null } })}
                        />
                      </div>
                      <div className="dynamic-field">
                        <label className="field-label" htmlFor={`maxval-${field.id}`}>Max Value</label>
                        <input 
                          id={`maxval-${field.id}`}
                          type="number" 
                          className="field-input" 
                          value={field.validation_config.rules.max_value ?? ""}
                          disabled={disabled}
                          onChange={(e) => updateFieldConfig(field.id, { rules: { max_value: e.target.value ? parseFloat(e.target.value) : null } })}
                        />
                      </div>
                    </div>
                  )}

                  {field.validation_config.type === "email" && (
                    <div className="dynamic-field">
                      <label className="field-label" htmlFor={`domains-${field.id}`}>Allowed Domains (comma-separated)</label>
                      <input 
                        id={`domains-${field.id}`}
                        type="text" 
                        className="field-input" 
                        placeholder="e.g. example.com, poornima.org"
                        disabled={disabled}
                        value={(field.validation_config.rules.allowed_domains || []).join(", ")}
                        onChange={(e) => updateFieldConfig(field.id, { rules: { allowed_domains: e.target.value ? e.target.value.split(",").map(d => d.trim()).filter(Boolean) : null } })}
                      />
                    </div>
                  )}

                  {field.validation_config.type === "select" && (
                    <div className="dynamic-field">
                      <label className="field-label">Select Options</label>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        {(field.validation_config.rules.options || []).map((opt, optIndex) => (
                          <div key={optIndex} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                            <input 
                              type="text" 
                              className="field-input" 
                              value={opt}
                              disabled={disabled}
                              placeholder="Option value"
                              onChange={(e) => handleOptionChange(field.id, optIndex, e.target.value)}
                            />
                            {!disabled && (
                              <button 
                                onClick={() => removeOption(field.id, optIndex)}
                                className="btn btn-secondary"
                                style={{ padding: "0.5rem", color: "#ef4444", borderColor: "#fca5a5" }}
                                title="Remove Option"
                              >
                                ✕
                              </button>
                            )}
                          </div>
                        ))}
                        {!disabled && (
                          <button 
                            onClick={() => addOption(field.id)}
                            className="btn btn-secondary"
                            style={{ alignSelf: "flex-start", marginTop: "0.5rem" }}
                          >
                            + Add Option
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                </div>
              )}
            </div>
          ))}

          {!disabled && (
            <div style={{ marginTop: "1rem" }}>
              <button 
                className="btn btn-primary" 
                onClick={handleSave}
                disabled={saving}
                style={{ width: "100%", padding: "1rem", fontSize: "1.1rem" }}
              >
                {saving ? "Saving Changes..." : "Save Changes"}
              </button>
            </div>
          )}
          {disabled && campaignStatus === "PUBLISHED" && (
            <div style={{ marginTop: "1rem", padding: "1rem", backgroundColor: "#f3f4f6", color: "#4b5563", borderRadius: "8px", textAlign: "center" }}>
              This campaign is currently published.<br/>Form configuration is read-only while the campaign is live.
            </div>
          )}
          {!disabled && campaignStatus === "CLOSED" && (
            <div style={{ marginTop: "1rem", padding: "1rem", backgroundColor: "#fef9c3", color: "#854d0e", borderRadius: "8px", textAlign: "center", border: "1px solid #fef08a" }}>
              This campaign is closed.<br/>You can modify the form configuration before reopening it.
            </div>
          )}
        </div>

        {/* Live Preview Column */}
        <div style={{ flex: 1, position: "sticky", top: "2rem", alignSelf: "flex-start" }}>
          <h4 style={{ marginBottom: "0.5rem", color: "#111827" }}>Live Preview</h4>
          <div style={{ 
            border: "1px solid #e5e7eb", 
            borderRadius: "8px", 
            padding: "2rem", 
            backgroundColor: "#ffffff",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
            color: "#111827"
          }}>
            <h5 style={{ marginBottom: "1.5rem", borderBottom: "1px solid #e5e7eb", paddingBottom: "0.5rem", color: "#111827" }}>Student Form Preview</h5>
            <form onSubmit={e => e.preventDefault()}>
              {collectFields.map(field => {
                const config = field.validation_config;
                if (!config) return null;
                const isRequired = config.rules.required;
                
                return (
                  <div key={`preview-${field.id}`} className="dynamic-field" style={{ marginBottom: "1.5rem" }}>
                    <label className="field-label" style={{ fontWeight: 600 }}>
                      {field.field_name} {isRequired && <span style={{ color: "#ef4444" }}>*</span>}
                    </label>
                    
                    {config.type === "textarea" ? (
                      <textarea 
                        className="field-input" 
                        placeholder={`Enter ${field.field_name.toLowerCase()}...`}
                        rows={3}
                        readOnly
                      />
                    ) : config.type === "select" ? (
                      <select className="field-input" disabled>
                        <option value="">Select an option...</option>
                        {(config.rules.options || []).map((opt, i) => (
                          <option key={i} value={opt}>{opt}</option>
                        ))}
                      </select>
                    ) : (
                      <input 
                        type={
                          config.type === "number" ? "number" : 
                          config.type === "email" ? "email" : 
                          config.type === "date" ? "date" : 
                          config.type === "phone" ? "tel" : "text"
                        }
                        className="field-input"
                        placeholder={`Enter ${field.field_name.toLowerCase()}...`}
                        readOnly
                      />
                    )}
                    
                    {/* Render validation hints */}
                    <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "0.25rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                      {(config.type === "text" || config.type === "textarea") && config.rules.min_length != null && (
                        <span>Min chars: {config.rules.min_length}</span>
                      )}
                      {(config.type === "text" || config.type === "textarea") && config.rules.max_length != null && (
                        <span>Max chars: {config.rules.max_length}</span>
                      )}
                      {config.type === "number" && config.rules.min_value != null && (
                        <span>Min value: {config.rules.min_value}</span>
                      )}
                      {config.type === "number" && config.rules.max_value != null && (
                        <span>Max value: {config.rules.max_value}</span>
                      )}
                      {config.type === "email" && config.rules.allowed_domains && config.rules.allowed_domains.length > 0 && (
                        <span>Domains: {config.rules.allowed_domains.join(", ")}</span>
                      )}
                    </div>
                  </div>
                );
              })}
              
              <div style={{ marginTop: "2rem" }}>
                <button type="button" className="btn btn-primary" disabled style={{ width: "100%", opacity: 0.7 }}>
                  Submit Information
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
