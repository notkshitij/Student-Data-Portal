import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AdminFormConfigResponse, AdminFormField, FieldValidationConfig, FieldType } from "../types/admin";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

interface AdminFormBuilderProps {
  campaignId: string;
  disabled: boolean;
  campaignStatus?: string;
}

// A sortable item component for each field strictly for the LIVE PREVIEW
const SortablePreviewField = ({ 
  field, 
  disabled,
}: { 
  field: AdminFormField;
  disabled: boolean;
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: field.id, disabled });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 1 : 0,
    position: "relative" as const,
    marginBottom: "1.25rem",
    backgroundColor: "#ffffff",
    border: "1px solid #e5e7eb",
    borderRadius: "8px",
    padding: "1.25rem",
    boxShadow: isDragging ? "0 10px 15px -3px rgba(0, 0, 0, 0.1)" : "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  };

  const fieldConfig = field.validation_config;
  const isRequired = fieldConfig?.rules?.required;

  return (
    <div ref={setNodeRef} style={style}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
        
        {/* Drag Handle */}
        {!disabled && (
          <div 
            {...attributes} 
            {...listeners} 
            style={{ 
              cursor: "grab", 
              padding: "0.25rem", 
              color: "#9ca3af",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginTop: "0.125rem",
              touchAction: "none"
            }}
            title="Drag to reorder"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M8 6C8 7.10457 7.10457 8 6 8C4.89543 8 4 7.10457 4 6C4 4.89543 4.89543 4 6 4C7.10457 4 8 4.89543 8 6Z" fill="currentColor"/>
              <path d="M8 12C8 13.1046 7.10457 14 6 14C4.89543 14 4 13.1046 4 12C4 10.8954 4.89543 10 6 10C7.10457 10 8 10.8954 8 12Z" fill="currentColor"/>
              <path d="M8 18C8 19.1046 7.10457 20 6 20C4.89543 20 4 19.1046 4 18C4 16.8954 4.89543 16 6 16C7.10457 16 8 16.8954 8 18Z" fill="currentColor"/>
              <path d="M20 6C20 7.10457 19.1046 8 18 8C16.8954 8 16 7.10457 16 6C16 4.89543 16.8954 4 18 4C19.1046 4 20 4.89543 20 6Z" fill="currentColor"/>
              <path d="M20 12C20 13.1046 19.1046 14 18 14C16.8954 14 16 13.1046 16 12C16 10.8954 16.8954 10 18 10C19.1046 10 20 10.8954 20 12Z" fill="currentColor"/>
              <path d="M20 18C20 19.1046 19.1046 20 18 20C16.8954 20 16 19.1046 16 18C16 16.8954 16.8954 16 18 16C19.1046 16 20 16.8954 20 18Z" fill="currentColor"/>
            </svg>
          </div>
        )}

        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: "0.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <label className="field-label" style={{ fontWeight: 600, margin: 0, fontSize: "1rem" }}>
              {field.field_name} {isRequired && <span style={{ color: "#ef4444" }}>*</span>}
            </label>
            <span style={{ 
              fontSize: "0.7rem", 
              padding: "0.125rem 0.5rem", 
              borderRadius: "9999px",
              backgroundColor: field.requires_student_input ? "#e0e7ff" : "#f1f5f9",
              color: field.requires_student_input ? "#4338ca" : "#475569",
              fontWeight: 500
            }}>
              {field.requires_student_input ? "Collectable" : "Display only"}
            </span>
          </div>

          {/* Render Preview Input / Display */}
          {!field.requires_student_input ? (
            <div className="field-readonly-value" style={{ padding: "0.75rem", backgroundColor: "#f8fafc", borderRadius: "6px", color: "#64748b", border: "1px dashed #cbd5e1", fontSize: "0.875rem" }}>
              <span className="empty-value">Existing imported value</span>
            </div>
          ) : fieldConfig && (
            <div style={{ pointerEvents: "none" }}>
              {/* Input Preview (disabled pointer events so we don't accidentally interact while trying to drag) */}
              <div>
                {fieldConfig.type === "textarea" ? (
                  <textarea 
                    className="field-input" 
                    placeholder={`Enter ${field.field_name.toLowerCase()}...`}
                    rows={2}
                    readOnly
                  />
                ) : fieldConfig.type === "select" ? (
                  <select className="field-input" disabled>
                    <option value="">Select an option...</option>
                    {(fieldConfig.rules.options || []).map((opt, i) => (
                      <option key={i} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <input 
                    type={
                      fieldConfig.type === "number" ? "number" : 
                      fieldConfig.type === "email" ? "email" : 
                      fieldConfig.type === "date" ? "date" : 
                      fieldConfig.type === "phone" ? "tel" : "text"
                    }
                    className="field-input"
                    placeholder={`Enter ${field.field_name.toLowerCase()}...`}
                    readOnly
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const AdminFormBuilder: React.FC<AdminFormBuilderProps> = ({ campaignId, disabled, campaignStatus }) => {
  // ONE canonical ordered array of ALL fields (collectable + non-collectable)
  const [orderedFields, setOrderedFields] = useState<AdminFormField[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

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
      // Sort by field_order — this is the canonical order from the backend
      setOrderedFields(data.fields.sort((a, b) => a.field_order - b.field_order));
      setIsDirty(false);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      setOrderedFields((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        setIsDirty(true);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    setError(null);
    
    // Build the complete ordering for ALL fields
    const fieldOrders = orderedFields.map((f, idx) => ({
      id: f.id,
      field_order: idx,
    }));

    // Build validation config updates for collectable fields only
    const fieldConfigs = orderedFields
      .filter(f => f.requires_student_input && f.validation_config)
      .map(f => ({
        id: f.id,
        validation_config: f.validation_config!,
      }));

    const updatePayload = {
      field_orders: fieldOrders,
      fields: fieldConfigs,
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
      setIsDirty(false);
      await fetchFormConfig(); // Refresh after save to ensure canonical state
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during saving.");
    } finally {
      setSaving(false);
    }
  };

  const updateFieldConfig = (fieldId: string, updates: Partial<FieldValidationConfig>) => {
    setIsDirty(true);
    setOrderedFields(prev => prev.map(f => {
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

  const handleOptionChange = (fieldId: string, index: number, newValue: string) => {
    setIsDirty(true);
    setOrderedFields(prev => prev.map(f => {
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
    setIsDirty(true);
    setOrderedFields(prev => prev.map(f => {
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
    setIsDirty(true);
    setOrderedFields(prev => prev.map(f => {
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

  if (orderedFields.length === 0) {
    return (
      <div style={{ marginTop: "2rem", padding: "2rem", backgroundColor: "#f9fafb", borderRadius: "8px", textAlign: "center" }}>
        <h3 style={{ color: "#374151" }}>No Fields</h3>
        <p style={{ color: "#6b7280" }}>
          There are no fields in this campaign's imported data.
        </p>
      </div>
    );
  }

  const collectFields = orderedFields.filter(f => f.requires_student_input);

  return (
    <div className="admin-form-builder" style={{ marginTop: "2rem" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h3>Form Builder</h3>
        <p style={{ color: "#94a3b8", fontSize: "0.95rem" }}>
          Configure field requirements on the left, and drag-and-drop fields in the Live Preview on the right to set their order.
        </p>
      </div>

      {saveMessage && (
        <div style={{ padding: "1rem", backgroundColor: "#ecfdf5", color: "#059669", borderRadius: "8px", marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{saveMessage}</span>
          <button onClick={() => setSaveMessage(null)} style={{ background: "none", border: "none", color: "#059669", cursor: "pointer", fontSize: "1.25rem" }}>&times;</button>
        </div>
      )}
      
      {error && (
        <div className="error-state" style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "#fef2f2", color: "#b91c1c", borderRadius: "8px" }}>
          {error}
        </div>
      )}

      {disabled && campaignStatus === "PUBLISHED" && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "#f3f4f6", color: "#4b5563", borderRadius: "8px", textAlign: "center" }}>
          This campaign is currently published. Form configuration is read-only while the campaign is live.
        </div>
      )}
      {!disabled && campaignStatus === "CLOSED" && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "#fef9c3", color: "#854d0e", borderRadius: "8px", textAlign: "center", border: "1px solid #fef08a" }}>
          This campaign is closed. You can modify the form configuration before reopening it.
        </div>
      )}

      {/* Two-column responsive layout */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
        gap: "2rem",
        alignItems: "start"
      }}>
        
        {/* Left Column: Configuration */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div>
            <h4 style={{ marginBottom: "0.75rem", color: "#f1f5f9" }}>Field Configuration</h4>
            <p style={{ color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1rem" }}>
              Configure validation rules for fields that require student input.
            </p>
            
            {collectFields.length === 0 ? (
              <div style={{ padding: "1rem", backgroundColor: "#1e293b", borderRadius: "8px", color: "#94a3b8", textAlign: "center" }}>
                No collectable fields in this campaign.
              </div>
            ) : (
              collectFields.map(field => (
                <div key={`config-${field.id}`} style={{
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  padding: "1.5rem",
                  backgroundColor: "#ffffff",
                  boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
                  color: "#111827",
                  marginBottom: "1rem"
                }}>
                  <div style={{ marginBottom: "1rem" }}>
                    <strong style={{ fontSize: "1.1rem" }}>{field.field_name}</strong>
                    <div style={{ fontSize: "0.875rem", color: "#6b7280", marginTop: "0.25rem" }}>
                      Type: <span style={{ textTransform: "capitalize" }}>{field.validation_config?.type || "Text"}</span>
                    </div>
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
              ))
            )}
          </div>
          
          {!disabled && (
            <div style={{ marginTop: "1rem", position: "sticky", bottom: "1rem", zIndex: 10 }}>
              <button 
                type="button"
                className="btn btn-primary" 
                onClick={handleSave}
                disabled={saving || !isDirty}
                style={{ 
                  width: "100%",
                  padding: "1rem", 
                  fontSize: "1.1rem",
                  boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
                  opacity: (!isDirty && !saving) ? 0.7 : 1
                }}
              >
                {saving ? "Saving Changes..." : "Save Form"}
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Live Form Preview (Drag and Drop Ordering) */}
        <div style={{ position: "sticky", top: "2rem", alignSelf: "flex-start" }}>
          <h4 style={{ marginBottom: "0.75rem", color: "#f1f5f9" }}>Live Form Preview</h4>
          <p style={{ color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1rem" }}>
            Drag and drop fields here to reorder them.
          </p>
          
          <div style={{ 
            border: "1px solid #e5e7eb", 
            borderRadius: "8px", 
            padding: "1.5rem", 
            backgroundColor: "#f8fafc",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
            color: "#111827",
            maxHeight: "calc(100vh - 8rem)",
            overflowY: "auto"
          }}>
            <h5 style={{ marginBottom: "1.5rem", borderBottom: "1px solid #e5e7eb", paddingBottom: "0.75rem", color: "#111827", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              Student Form View
              <span style={{ fontSize: "0.75rem", fontWeight: "normal", color: "#6b7280" }}>Interactive ordering</span>
            </h5>
            
            <form onSubmit={e => e.preventDefault()}>
              <DndContext 
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext 
                  items={orderedFields.map(f => f.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {orderedFields.map((field) => (
                    <SortablePreviewField 
                      key={field.id}
                      field={field} 
                      disabled={disabled}
                    />
                  ))}
                </SortableContext>
              </DndContext>
              
              <div style={{ marginTop: "2rem" }}>
                <button type="button" className="btn btn-primary" disabled style={{ width: "100%", opacity: 0.5, cursor: "not-allowed" }}>
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
