import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AdminCampaignListResponse } from "../types/admin";
import { AdminCampaignDetail } from "./AdminCampaignDetail";
import { AdminAuditLogs } from "./AdminAuditLogs";

interface AdminDashboardProps {
  user: any;
  onLogout?: () => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState<"dashboard" | "campaigns" | "audit">("dashboard");
  const [campaigns, setCampaigns] = useState<AdminCampaignListResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns`, {
        credentials: "include",
      });
      
      if (!response.ok) {
        throw new Error("Failed to load campaigns.");
      }
      
      const data = await response.json();
      setCampaigns(data);
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, [activeTab]); // Refetch if switching tabs just in case

  if (selectedCampaignId) {
    return (
      <AdminCampaignDetail 
        campaignId={selectedCampaignId} 
        onBack={() => {
          setSelectedCampaignId(null);
          fetchCampaigns(); // Refresh list on back
        }} 
      />
    );
  }

  // Calculate Dashboard stats
  const totalCampaigns = campaigns.length;
  const draftCampaigns = campaigns.filter(c => c.status === "DRAFT").length;
  const publishedCampaigns = campaigns.filter(c => c.status === "PUBLISHED").length;
  const closedCampaigns = campaigns.filter(c => c.status === "CLOSED").length;
  const totalStudents = campaigns.reduce((acc, c) => acc + c.student_count, 0);

  return (
    <div className="admin-layout">
      {/* Sidebar Navigation */}
      <div className="admin-sidebar">
        <div style={{ padding: "0 1rem", marginBottom: "1rem" }}>
          <h2 style={{ fontSize: "1.25rem", margin: "0", color: "#f8fafc" }}>Admin Panel</h2>
          <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.25rem", wordBreak: "break-all" }}>
            {user?.email}
          </div>
        </div>
        
        <button 
          className={`admin-nav-item ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          Dashboard Overview
        </button>
        <button 
          className={`admin-nav-item ${activeTab === "campaigns" ? "active" : ""}`}
          onClick={() => setActiveTab("campaigns")}
        >
          Campaigns
        </button>
        <button 
          className={`admin-nav-item ${activeTab === "audit" ? "active" : ""}`}
          onClick={() => setActiveTab("audit")}
        >
          Audit Logs
        </button>

        {onLogout && (
          <button 
            className="admin-nav-item"
            style={{ marginTop: "auto", borderTop: "1px solid #334155", borderRadius: "0 0 8px 8px" }}
            onClick={onLogout}
          >
            Sign Out
          </button>
        )}
      </div>

      {/* Main Content Area */}
      <div className="admin-main-content">
        {activeTab === "dashboard" && (
          <div>
            <h2 style={{ marginBottom: "2rem" }}>System Overview</h2>
            {loading ? (
              <div className="loading-state">Loading statistics...</div>
            ) : error ? (
              <div className="error-state">{error} <button onClick={fetchCampaigns} style={{ marginLeft: "1rem" }}>Retry</button></div>
            ) : (
              <>
                <div className="admin-stats-grid">
                  <div className="stat-card">
                    <span className="stat-label">Total Campaigns</span>
                    <span className="stat-value">{totalCampaigns}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Published (Live)</span>
                    <span className="stat-value" style={{ color: "#34d399" }}>{publishedCampaigns}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Drafts</span>
                    <span className="stat-value" style={{ color: "#fbbf24" }}>{draftCampaigns}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Closed</span>
                    <span className="stat-value" style={{ color: "#94a3b8" }}>{closedCampaigns}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Total Enrolled Students</span>
                    <span className="stat-value" style={{ color: "#818cf8" }}>{totalStudents}</span>
                  </div>
                </div>
                
                <div style={{ padding: "2rem", backgroundColor: "#1e293b", borderRadius: "8px", border: "1px solid #334155" }}>
                  <h3 style={{ marginTop: 0 }}>Quick Actions</h3>
                  <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
                    <button className="btn btn-primary" onClick={() => setActiveTab("campaigns")}>
                      View All Campaigns
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === "campaigns" && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: "2rem" }}>
              <h2 style={{ margin: 0 }}>Campaigns</h2>
            </div>
            
            {loading ? (
              <div className="loading-state">Loading campaigns...</div>
            ) : error ? (
              <div className="error-state">{error} <button onClick={fetchCampaigns} style={{ marginLeft: "1rem" }}>Retry</button></div>
            ) : campaigns.length === 0 ? (
              <div className="empty-state">
                <h3>No campaigns found</h3>
                <p>No campaigns have been imported yet.</p>
              </div>
            ) : (
              <div className="campaign-list">
                {campaigns.map(campaign => (
                  <div 
                    key={campaign.campaign_id} 
                    className="campaign-card"
                    onClick={() => setSelectedCampaignId(campaign.campaign_id)}
                  >
                    <div className="campaign-card-header">
                      <h3 style={{ margin: 0 }}>{campaign.name}</h3>
                      <span className={`badge badge-${campaign.status.toLowerCase()}`}>
                        {campaign.status}
                      </span>
                    </div>
                    <div className="campaign-card-footer" style={{ flexDirection: "column", alignItems: "flex-start", gap: "0.5rem" }}>
                      <span className="campaign-date" style={{ color: "#4b5563" }}>
                        {campaign.student_count} Students | {campaign.field_count} Fields
                      </span>
                      <span className="campaign-date" style={{ color: "#9ca3af", fontSize: "0.75rem" }}>
                        Created on {new Date(campaign.created_at).toLocaleDateString()}
                      </span>
                      <button className="btn btn-secondary" style={{ width: "100%", marginTop: "0.5rem" }}>
                        Manage Campaign
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "audit" && (
          <div>
            <h2 style={{ marginBottom: "2rem" }}>Audit Logs</h2>
            <AdminAuditLogs onBack={() => setActiveTab("dashboard")} />
          </div>
        )}
      </div>
    </div>
  );
};
