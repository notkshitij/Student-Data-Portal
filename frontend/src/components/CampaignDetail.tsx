import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { StudentCampaignDetailResponse } from "../types";
import { DynamicField } from "./DynamicField";

interface CampaignDetailProps {
  campaignId: string;
  onBack: () => void;
}

export const CampaignDetail: React.FC<CampaignDetailProps> = ({ campaignId, onBack }) => {
  const [campaign, setCampaign] = useState<StudentCampaignDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  
  // Track responses
  const [responses, setResponses] = useState<Record<string, string>>({});
  // Track frontend field errors
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

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

  const handleSave = async () => {
    setError(null);
    setSaveMessage(null);
    setFieldErrors({});
    
    // 1. Frontend validation (not authoritative, but good UX)
    if (!validateFrontend()) {
      setError("Please fix the errors in the form before saving.");
      return;
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
          throw new Error("Please fix the highlighted errors.");
        }
        throw new Error(data.detail || "Failed to save responses.");
      }
      
      setSaveMessage(data.message || "Responses saved successfully!");
      
      // Refresh to get normalized values from backend
      await fetchCampaign();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during save.");
    } finally {
      setSaving(false);
    }
  };

  if (loading && !campaign) {
    return <div className="loading-state">Loading campaign details...</div>;
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

  return (
    <div className="campaign-detail">
      <button className="btn back-btn" onClick={onBack}>
        &larr; Back to Dashboard
      </button>
      
      <div className="campaign-header">
        <h2>{campaign.name}</h2>
        {campaign.description && <p className="campaign-description">{campaign.description}</p>}
        <div className="campaign-badges">
          <span className="badge badge-status">{campaign.campaign_status}</span>
          <span className={`badge badge-submission ${campaign.submission_status.toLowerCase()}`}>
            {campaign.submission_status}
          </span>
        </div>
      </div>

      <div className="campaign-form">
        <h3 className="form-title">Student Information</h3>
        <p className="form-subtitle">
          Please verify the information below. Editable fields marked with an asterisk (*) require your input.
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
        
        <div className="fields-grid">
          {campaign.fields.map(field => (
            <DynamicField 
              key={field.field_id} 
              field={field} 
              value={field.requires_student_input ? responses[field.field_id] || "" : undefined}
              onChange={field.requires_student_input ? (val) => handleResponseChange(field.field_id, val) : undefined}
              error={fieldErrors[field.field_id]}
              disabled={isSubmitted || saving}
            />
          ))}
        </div>
        
        <div className="form-actions">
          <button 
            className="btn btn-primary" 
            onClick={handleSave}
            disabled={saving || isSubmitted}
          >
            {saving ? "Saving..." : (isSubmitted ? "Cannot edit submitted campaign" : "Save Responses")}
          </button>
        </div>
      </div>
    </div>
  );
};
