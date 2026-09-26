import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AdminCampaignDetailResponse } from "../types/admin";
import { AdminFormBuilder } from "./AdminFormBuilder";
import { AdminCampaignProgress } from "./AdminCampaignProgress";

interface AdminCampaignDetailProps {
  campaignId: string;
  onBack: () => void;
}

export const AdminCampaignDetail: React.FC<AdminCampaignDetailProps> = ({ campaignId, onBack }) => {
  const [campaign, setCampaign] = useState<AdminCampaignDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [publishMessage, setPublishMessage] = useState<string | null>(null);

  const fetchCampaign = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}`, {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("Failed to load campaign details.");
      }
      const data = await response.json();
      setCampaign(data);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaign();
  }, [campaignId]);

  const handleClose = async () => {
    if (!window.confirm("Closing this campaign will prevent students from making further changes or submitting responses. Existing responses and submissions will be preserved. Continue?")) {
      return;
    }
    
    setIsClosing(true);
    setPublishMessage(null);
    setError(null);
    
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/close`, {
        method: "POST",
        credentials: "include",
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Failed to close campaign.");
      }
      
      setPublishMessage(data.message || "Campaign closed successfully!");
      // Refresh campaign to get updated status
      await fetchCampaign();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during closing.");
    } finally {
      setIsClosing(false);
    }
  };

  const handlePublish = async () => {
    if (!window.confirm("Are you sure you want to publish this campaign? It will become visible to students.")) {
      return;
    }
    
    setIsPublishing(true);
    setPublishMessage(null);
    setError(null);
    
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/publish`, {
        method: "POST",
        credentials: "include",
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Failed to publish campaign.");
      }
      
      setPublishMessage(data.message || "Campaign published successfully!");
      // Refresh campaign to get updated status
      await fetchCampaign();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during publishing.");
    } finally {
      setIsPublishing(false);
    }
  };

  if (loading && !campaign) {
    return <div className="loading-state">Loading campaign...</div>;
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

  return (
    <div className="campaign-detail">
      <button className="btn back-btn" onClick={onBack}>
        &larr; Back to Admin Dashboard
      </button>
      
      <div className="campaign-header">
        <h2>{campaign.name}</h2>
        <div className="campaign-badges">
          <span className="badge badge-status">{campaign.status}</span>
        </div>
      </div>
      
      {publishMessage && (
        <div style={{ padding: "1rem", backgroundColor: "#ecfdf5", color: "#059669", borderRadius: "8px", marginBottom: "1rem" }}>
          {publishMessage}
        </div>
      )}
      
      {error && (
        <div className="error-state">
          {error}
        </div>
      )}

      <div className="campaign-form" style={{ marginTop: "2rem" }}>
        <h3 className="form-title">Campaign Summary</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "1.5rem" }}>
          <div>
            <strong>Enrolled Students:</strong> {campaign.student_count}
          </div>
          <div>
            <strong>Total Dynamic Fields:</strong> {campaign.field_count}
          </div>
          <div>
            <strong>Fields Requiring Input:</strong> {campaign.collect_field_count}
          </div>
          <div>
            <strong>Created:</strong> {new Date(campaign.created_at).toLocaleString()}
          </div>
        </div>

        {campaign.status === "DRAFT" && (
          <div className="form-actions">
            <button 
              className="btn btn-primary" 
              onClick={handlePublish}
              disabled={isPublishing || campaign.student_count === 0 || campaign.field_count === 0}
            >
              {isPublishing ? "Publishing..." : "Publish Campaign"}
            </button>
          </div>
        )}

        {campaign.status === "PUBLISHED" && (
          <div className="form-actions">
            <button 
              className="btn btn-danger" 
              onClick={handleClose}
              disabled={isClosing}
              style={{ backgroundColor: "#ef4444", color: "white", borderColor: "#ef4444" }}
            >
              {isClosing ? "Closing..." : "Close Campaign"}
            </button>
          </div>
        )}
      </div>

      <AdminFormBuilder 
        campaignId={campaignId} 
        disabled={campaign.status !== "DRAFT"} 
      />

      <AdminCampaignProgress campaignId={campaignId} />
    </div>
  );
};
