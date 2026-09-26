import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AdminCampaignDetailResponse } from "../types/admin";
import { AdminFormBuilder } from "./AdminFormBuilder";
import { AdminCampaignProgress } from "./AdminCampaignProgress";

interface AdminCampaignDetailProps {
  campaignId: string;
  onBack: () => void;
  initialTab?: string;
  onTabChange?: (tab: string) => void;
}

export const AdminCampaignDetail: React.FC<AdminCampaignDetailProps> = ({ campaignId, onBack, initialTab, onTabChange }) => {
  const [campaign, setCampaign] = useState<AdminCampaignDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [publishMessage, setPublishMessage] = useState<string | null>(null);
  
  const validTabs = ["overview", "form", "students"] as const;
  type TabType = typeof validTabs[number];
  const resolvedInitialTab = validTabs.includes(initialTab as TabType) ? (initialTab as TabType) : "overview";
  const [activeTab, setActiveTabLocal] = useState<TabType>(resolvedInitialTab);

  const setActiveTab = (tab: TabType) => {
    setActiveTabLocal(tab);
    onTabChange?.(tab);
  };

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

  const handleReopen = async () => {
    if (!window.confirm("Reopen Campaign?\n\nThis will change the campaign from CLOSED to PUBLISHED.\n\nThe updated form configuration will become active for eligible students.\nStudents who have already submitted will remain locked.")) {
      return;
    }
    
    setIsPublishing(true); // Reusing publishing state for loading
    setPublishMessage(null);
    setError(null);
    
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/reopen`, {
        method: "POST",
        credentials: "include",
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Failed to reopen campaign.");
      }
      
      setPublishMessage(data.message || "Campaign reopened successfully!");
      // Refresh campaign to get updated status
      await fetchCampaign();
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during reopening.");
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

  if (loading && !campaign) {
    return <div className="loading-state">Loading campaign...</div>;
  }

  if (!campaign) {
    return null;
  }

  return (
    <div className="campaign-detail">
      <button className="btn back-btn" onClick={onBack} style={{ marginBottom: "2rem" }}>
        &larr; Back to Admin Dashboard
      </button>
      
      <div className="campaign-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: "2rem" }}>
        <div>
          <h2 style={{ margin: "0 0 0.5rem 0" }}>{campaign.name}</h2>
          <div className="campaign-badges">
            <span className={`badge badge-${campaign.status.toLowerCase()}`}>{campaign.status}</span>
          </div>
        </div>
        
        <div style={{ display: "flex", gap: "1rem" }}>
          {campaign.status === "DRAFT" && (
            <button 
              className="btn btn-primary" 
              onClick={handlePublish}
              disabled={isPublishing || campaign.student_count === 0 || campaign.field_count === 0}
            >
              {isPublishing ? "Publishing..." : "Publish Campaign"}
            </button>
          )}

          {campaign.status === "PUBLISHED" && (
            <button 
              className="btn btn-danger" 
              onClick={handleClose}
              disabled={isClosing}
              style={{ backgroundColor: "#ef4444", color: "white", borderColor: "#ef4444" }}
            >
              {isClosing ? "Closing..." : "Close Campaign"}
            </button>
          )}

          {campaign.status === "CLOSED" && (
            <button 
              className="btn btn-primary" 
              onClick={handleReopen}
              disabled={isPublishing}
              style={{ backgroundColor: "#4f46e5", color: "white", borderColor: "#4f46e5" }}
            >
              {isPublishing ? "Reopening..." : "Reopen Campaign"}
            </button>
          )}
        </div>
      </div>
      
      {publishMessage && (
        <div style={{ padding: "1rem", backgroundColor: "#ecfdf5", color: "#059669", borderRadius: "8px", marginBottom: "1rem" }}>
          {publishMessage}
        </div>
      )}
      
      {error && (
        <div className="error-state" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: "1rem", borderBottom: "1px solid #334155", marginBottom: "2rem" }}>
        <button 
          onClick={() => setActiveTab("overview")}
          style={{ 
            padding: "0.75rem 1.5rem", 
            border: "none",
            borderBottom: activeTab === "overview" ? "2px solid #6366f1" : "2px solid transparent",
            background: "transparent",
            color: activeTab === "overview" ? "#f8fafc" : "#94a3b8",
            fontWeight: activeTab === "overview" ? 600 : 500,
            cursor: "pointer",
            fontSize: "1rem",
            transition: "all 0.2s"
          }}
        >
          Overview
        </button>
        <button 
          onClick={() => setActiveTab("form")}
          style={{ 
            padding: "0.75rem 1.5rem", 
            border: "none",
            borderBottom: activeTab === "form" ? "2px solid #6366f1" : "2px solid transparent",
            background: "transparent",
            color: activeTab === "form" ? "#f8fafc" : "#94a3b8",
            fontWeight: activeTab === "form" ? 600 : 500,
            cursor: "pointer",
            fontSize: "1rem",
            transition: "all 0.2s"
          }}
        >
          Form Builder
        </button>
        <button 
          onClick={() => setActiveTab("students")}
          style={{ 
            padding: "0.75rem 1.5rem", 
            border: "none",
            borderBottom: activeTab === "students" ? "2px solid #6366f1" : "2px solid transparent",
            background: "transparent",
            color: activeTab === "students" ? "#f8fafc" : "#94a3b8",
            fontWeight: activeTab === "students" ? 600 : 500,
            cursor: "pointer",
            fontSize: "1rem",
            transition: "all 0.2s"
          }}
        >
          Students & Progress
        </button>
      </div>

      {activeTab === "overview" && (
        <div className="campaign-form">
          <h3 className="form-title">Campaign Summary</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "1.5rem" }}>
            <div>
              <strong style={{ color: "#475569" }}>Enrolled Students:</strong> {campaign.student_count}
            </div>
            <div>
              <strong style={{ color: "#475569" }}>Total Dynamic Fields:</strong> {campaign.field_count}
            </div>
            <div>
              <strong style={{ color: "#475569" }}>Fields Requiring Input:</strong> {campaign.collect_field_count}
            </div>
            <div>
              <strong style={{ color: "#475569" }}>Created:</strong> {new Date(campaign.created_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {activeTab === "form" && (
        <AdminFormBuilder 
          campaignId={campaignId} 
          disabled={campaign.status === "PUBLISHED"} 
          campaignStatus={campaign.status}
        />
      )}

      {activeTab === "students" && (
        <AdminCampaignProgress campaignId={campaignId} />
      )}
    </div>
  );
};
