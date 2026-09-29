import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { StudentCampaignDetailResponse } from "../types";
import { DynamicField } from "./DynamicField";

interface CampaignDetailProps {
  campaignId: string;
  onBack: () => void;
}

type FieldView = "input" | "verified" | "all";

export const CampaignDetail: React.FC<CampaignDetailProps> = ({ campaignId, onBack }) => {
  const [campaign, setCampaign] = useState<StudentCampaignDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  
  // Track responses
  const [responses, setResponses] = useState<Record<string, string>>({});
  // Track frontend field errors
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  // Which group of fields is visible
  const [view, setView] = useState<FieldView>("input");

  const fetchCampaign = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${config.apiBaseUrl}/api/student/campaigns/${campaignId}`, {
        credentials: "include",
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error("Your session has expired. Please log in again.");
        } else if (response.status === 403 || response.status === 404) {
          throw new Error("This campaign is not available.");
        }
        throw new Error("Failed to load campaign data.");
      }
      
      const data: StudentCampaignDetailResponse = await response.json();
      setCampaign(data);
      
      // Initialize responses state with existing values
      const initialResponses: Record<string, string> = {};
      data.fields.forEach(f => {
        if (f.requires_student_input) {
          initialResponses[f.field_id] = f.value || "";
        }
      });
      setResponses(initialResponses);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaign();
  }, [campaignId]);

  const handleResponseChange = (fieldId: string, value: string) => {
    setResponses(prev => ({
      ...prev,
      [fieldId]: value
    }));
    // Clear error for this field when typing
    if (fieldErrors[fieldId]) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next[fieldId];
        return next;
      });
    }
  };

  const validateFrontend = (): boolean => {
    if (!campaign) return false;
    
    let isValid = true;
    const errors: Record<string, string> = {};
    
    for (const field of campaign.fields) {
      if (!field.requires_student_input) continue;
      
      const val = (responses[field.field_id] || "").trim();
      const config = field.validation_config;
      
      if (!config) continue;
      
      if (config.rules.required && !val) {
        errors[field.field_id] = "This field is required.";
        isValid = false;
        continue;
      }
      
      if (!val) continue; // Optional field, skip other checks if empty
      
      if (config.type === "email") {
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
          errors[field.field_id] = "Please enter a valid email address.";
          isValid = false;
        } else if (config.rules.allowed_domains && config.rules.allowed_domains.length > 0) {
          const domain = val.split("@")[1]?.toLowerCase();
          if (!config.rules.allowed_domains.map(d => d.toLowerCase()).includes(domain)) {
            errors[field.field_id] = `Domain must be one of: ${config.rules.allowed_domains.join(", ")}`;
            isValid = false;
          }
        }
      }
    }
    
    setFieldErrors(errors);
    return isValid;
  };

  const scrollToFirstError = () => {
    window.setTimeout(() => {
      const el = document.querySelector(".dynamic-field.has-error");
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }, 80);
  };

  const handleSave = async (showSuccessMessage: boolean = true) => {
    setError(null);
    if (showSuccessMessage) setSaveMessage(null);
    setFieldErrors({});
    
    // 1. Frontend validation (not authoritative, but good UX)
    if (!validateFrontend()) {
      setError("Please fix the errors in the form before saving.");
      // Make sure the fields with errors are actually visible
      setView(v => (v === "verified" ? "input" : v));
      scrollToFirstError();
      return false;
    }
    
    setSaving(true);
    
    // 2. Prepare payload
    const payload = {
      responses: Object.entries(responses).map(([field_id, value]) => ({
        field_id,
        value: value.trim() === "" ? null : value.trim()
      }))
    };
    
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/student/campaigns/${campaignId}/responses`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        if (response.status === 400 && data.detail?.field_errors) {
          setFieldErrors(data.detail.field_errors);
          scrollToFirstError();
          throw new Error("Please fix the highlighted errors.");
        }
        throw new Error(data.detail || "Failed to save responses.");
      }
      
      if (showSuccessMessage) {
        setSaveMessage(data.message || "Responses saved successfully!");
      }
      
      // Refresh to get normalized values from backend
      await fetchCampaign();
      return true;
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during save.");
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleFinalSubmit = async () => {
    if (!window.confirm("Are you sure you want to submit? After submission, you will not be able to change your responses.")) {
      return;
    }
    
    setSubmitting(true);
    setError(null);
    setSaveMessage(null);
    
    // Auto-save first
    const saveOk = await handleSave(false);
    if (!saveOk) {
      setSubmitting(false);
      return;
    }
    
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/student/campaigns/${campaignId}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include"
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        if (response.status === 400 && data.detail?.field_errors) {
          setFieldErrors(data.detail.field_errors);
          throw new Error("Please fix the highlighted errors before submitting.");
        }
        throw new Error(data.detail || "Failed to submit campaign.");
      }
      
      setSaveMessage("Campaign submitted successfully. Your responses are now locked.");
      
      // Refresh to get new status
      await fetchCampaign();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during submission.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && !campaign) {
    return (
      <div className="page-loader" role="status" aria-live="polite">
        <span className="spinner spinner--lg" />
        <span>Loading campaign details...</span>
      </div>
    );
  }

  if (error && !campaign) {
    return (
      <div className="error-state">
        <p>{error}</p>
        <button className="btn" onClick={onBack}>Back to Dashboard</button>
      </div>
    );
  }

  if (!campaign) {
    return null;
  }

  const isSubmitted = campaign.submission_status === "SUBMITTED";
  const isClosed = campaign.campaign_status === "CLOSED";
  const isLocked = isSubmitted || isClosed;

  // Field groups + progress
  const editableFields = campaign.fields.filter(f => f.requires_student_input);
  const readonlyFields = campaign.fields.filter(f => !f.requires_student_input);
  const filledCount = editableFields.filter(f => (responses[f.field_id] || "").trim() !== "").length;
  const progressPct = editableFields.length
    ? Math.round((filledCount / editableFields.length) * 100)
    : 100;

  const effectiveView: FieldView =
    view === "input" && editableFields.length === 0 ? "all" : view;
  const visibleFields =
    effectiveView === "input"
      ? editableFields
      : effectiveView === "verified"
      ? readonlyFields
      : campaign.fields;

  const submitLabel = submitting
    ? "Submitting..."
    : isSubmitted
    ? "Submitted & Locked"
    : isClosed
    ? "Campaign Closed"
    : "Final Submit";

  return (
    <div className="campaign-detail">
      <div className="cd-header">
        <div className="cd-header-main">
          <h2 className="cd-title">{campaign.name}</h2>
          {campaign.description && <p className="cd-desc">{campaign.description}</p>}
          <div className="campaign-badges">
            <span className="badge badge-status">{campaign.campaign_status}</span>
            <span className={`badge badge-submission ${campaign.submission_status.toLowerCase()}`}>
              {campaign.submission_status}
            </span>
          </div>
        </div>

        {editableFields.length > 0 && (
          <div className="cd-progress">
            <div className="cd-progress-row">
              <span className="cd-progress-label">Your progress</span>
              <span className="cd-progress-count">
                <strong>{filledCount}</strong> / {editableFields.length} filled
              </span>
            </div>
            <div className="cd-progress-track">
              <div
                className={`cd-progress-fill ${progressPct === 100 ? "is-done" : ""}`}
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="campaign-form">
        <div className="cd-form-head">
          <h3 className="form-title">Student Information</h3>
          <p className="form-subtitle">
            {isSubmitted 
              ? `Your responses have been submitted and are locked. (Submitted at: ${new Date(campaign.submitted_at!).toLocaleString()})`
              : isClosed
              ? "This campaign is closed and is no longer accepting submissions or changes."
              : "Please verify the information below. Editable fields marked with an asterisk (*) require your input."
            }
          </p>
        </div>

        <div className="cd-tabs" role="tablist">
          {editableFields.length > 0 && (
            <button
              role="tab"
              aria-selected={effectiveView === "input"}
              className={`cd-tab ${effectiveView === "input" ? "active" : ""}`}
              onClick={() => setView("input")}
            >
              Needs your input <span className="cd-tab-count">{editableFields.length}</span>
            </button>
          )}
          {readonlyFields.length > 0 && (
            <button
              role="tab"
              aria-selected={effectiveView === "verified"}
              className={`cd-tab ${effectiveView === "verified" ? "active" : ""}`}
              onClick={() => setView("verified")}
            >
              Already provided <span className="cd-tab-count">{readonlyFields.length}</span>
            </button>
          )}
          <button
            role="tab"
            aria-selected={effectiveView === "all"}
            className={`cd-tab ${effectiveView === "all" ? "active" : ""}`}
            onClick={() => setView("all")}
          >
            All fields <span className="cd-tab-count">{campaign.fields.length}</span>
          </button>
        </div>
        
        {saveMessage && <div className="cd-alert cd-alert--success">{saveMessage}</div>}
        {error && <div className="cd-alert cd-alert--error">{error}</div>}
        
        <div className="fields-grid">
          {visibleFields.map(field => (
            <DynamicField 
              key={field.field_id} 
              field={field} 
              value={field.requires_student_input ? responses[field.field_id] || "" : undefined}
              onChange={field.requires_student_input ? (val) => handleResponseChange(field.field_id, val) : undefined}
              error={fieldErrors[field.field_id]}
              disabled={isLocked || saving || submitting}
            />
          ))}
        </div>
        
        <div className="cd-actionbar">
          <span className="cd-actionbar-info">
            {editableFields.length === 0
              ? "Nothing to fill in - just review and submit"
              : filledCount === editableFields.length
              ? "All fields filled - ready to submit"
              : `${filledCount} of ${editableFields.length} required fields filled`}
          </span>
          <div className="cd-actionbar-buttons">
            <button 
              className="btn btn-secondary" 
              onClick={() => handleSave(true)}
              disabled={saving || submitting || isLocked}
            >
              {saving ? "Saving..." : "Save Draft"}
            </button>
            
            <button 
              className="btn btn-primary" 
              onClick={handleFinalSubmit}
              disabled={saving || submitting || isLocked}
            >
              {submitLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
