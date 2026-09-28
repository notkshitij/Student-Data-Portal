import React, { useEffect, useState, useCallback } from "react";
import { config } from "../config";
import type { AdminCampaignListResponse } from "../types/admin";
import { AdminCampaignDetail } from "./AdminCampaignDetail";
import { AdminAuditLogs } from "./AdminAuditLogs";

interface AdminDashboardProps {
  user: any;
  onLogout?: () => void;
}

type SidebarTab = "dashboard" | "campaigns" | "audit";

/**
 * Parse the URL hash to extract navigation state.
 * 
 * Supported formats:
 *   #admin                              → dashboard tab
 *   #admin/campaigns                    → campaigns tab
 *   #admin/audit                        → audit tab
 *   #admin/campaigns/{id}               → campaign detail, overview tab
 *   #admin/campaigns/{id}/form          → campaign detail, form tab
 *   #admin/campaigns/{id}/students      → campaign detail, students tab
 *   #admin/campaigns/{id}/overview      → campaign detail, overview tab
 */
function parseHash(): { sidebarTab: SidebarTab; campaignId: string | null; campaignTab: string | null } {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const parts = hash.split("/").filter(Boolean);

  // Default
  if (parts.length === 0 || parts[0] !== "admin") {
    return { sidebarTab: "dashboard", campaignId: null, campaignTab: null };
  }

  // #admin
  if (parts.length === 1) {
    return { sidebarTab: "dashboard", campaignId: null, campaignTab: null };
  }

  // #admin/campaigns
  if (parts[1] === "campaigns" && parts.length === 2) {
    return { sidebarTab: "campaigns", campaignId: null, campaignTab: null };
  }

  // #admin/campaigns/{id}
  if (parts[1] === "campaigns" && parts.length >= 3) {
    const campaignId = parts[2];
    const campaignTab = parts[3] || "overview";
    return { sidebarTab: "campaigns", campaignId, campaignTab };
  }

  // #admin/audit
  if (parts[1] === "audit") {
    return { sidebarTab: "audit", campaignId: null, campaignTab: null };
  }

  return { sidebarTab: "dashboard", campaignId: null, campaignTab: null };
}

function setHash(path: string) {
  window.location.hash = path;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ user, onLogout }) => {
  const initialState = parseHash();
  const [activeTab, setActiveTabState] = useState<SidebarTab>(initialState.sidebarTab);
  const [campaigns, setCampaigns] = useState<AdminCampaignListResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCampaignId, setSelectedCampaignIdState] = useState<string | null>(initialState.campaignId);
  const [initialCampaignTab, setInitialCampaignTab] = useState<string | null>(initialState.campaignTab);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCampaignName, setNewCampaignName] = useState("");
  const [newCampaignDesc, setNewCampaignDesc] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateCampaign = async () => {
    if (!newCampaignName.trim()) {
      setCreateError("Campaign name is required.");
      return;
    }
    
    setIsCreating(true);
    setCreateError(null);
    
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: newCampaignName,
          description: newCampaignDesc || null,
        }),
        credentials: "include",
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create campaign.");
      }
      
      const data = await response.json();
      
      setShowCreateModal(false);
      setNewCampaignName("");
      setNewCampaignDesc("");
      
      // Navigate to the newly created campaign
      setSelectedCampaignId(data.campaign_id);
      
    } catch (err: any) {
      setCreateError(err.message || "An error occurred.");
    } finally {
      setIsCreating(false);
    }
  };

  // Sync hash → state on popstate (browser back/forward)
  const handleHashChange = useCallback(() => {
    const state = parseHash();
    setActiveTabState(state.sidebarTab);
    setSelectedCampaignIdState(state.campaignId);
    setInitialCampaignTab(state.campaignTab);
  }, []);

  useEffect(() => {
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, [handleHashChange]);

  // Set initial hash if none exists
  useEffect(() => {
    if (!window.location.hash || window.location.hash === "#") {
      setHash("#admin");
    }
  }, []);

  // Wrappers that sync state → hash
  const setActiveTab = (tab: SidebarTab) => {
    setActiveTabState(tab);
    setSelectedCampaignIdState(null);
    setInitialCampaignTab(null);
    if (tab === "dashboard") setHash("#admin");
    else if (tab === "campaigns") setHash("#admin/campaigns");
    else if (tab === "audit") setHash("#admin/audit");
  };

  const setSelectedCampaignId = (id: string | null, tab?: string) => {
    setSelectedCampaignIdState(id);
    if (id) {
      setInitialCampaignTab(tab || "overview");
      setHash(`#admin/campaigns/${id}/${tab || "overview"}`);
    } else {
      setInitialCampaignTab(null);
      setHash("#admin/campaigns");
    }
  };

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
        initialTab={initialCampaignTab || "overview"}
        onBack={() => {
          setSelectedCampaignId(null);
          fetchCampaigns(); // Refresh list on back
        }}
        onTabChange={(tab: string) => {
          setInitialCampaignTab(tab);
          setHash(`#admin/campaigns/${selectedCampaignId}/${tab}`);
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
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                + Create Campaign
              </button>
            </div>
            
            {loading ? (
              <div className="loading-state">Loading campaigns...</div>
            ) : error ? (
              <div className="error-state">{error} <button onClick={fetchCampaigns} style={{ marginLeft: "1rem" }}>Retry</button></div>
            ) : campaigns.length === 0 ? (
              <div className="empty-state">
                <h3>No campaigns found</h3>
                <p>Click "Create Campaign" to get started.</p>
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
                      <span className="campaign-date" style={{ color: "#4b5563" }}>
                        Excel Source: {campaign.has_excel ? <span style={{ color: "#34d399" }}>Uploaded</span> : <span style={{ color: "#fbbf24" }}>Missing</span>}
                      </span>
                      <span className="campaign-date" style={{ color: "#9ca3af", fontSize: "0.75rem" }}>
                        Created on {new Date(campaign.created_at).toLocaleDateString()}
                      </span>
                      <button className="btn btn-secondary" style={{ width: "100%", marginTop: "0.5rem" }}>
                        {campaign.status === "DRAFT" ? "Open" : "Manage Campaign"}
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

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Create New Campaign</h3>
            {createError && <div className="error-message" style={{ marginBottom: "1rem" }}>{createError}</div>}
            
            <div className="form-group">
              <label>Campaign Name *</label>
              <input 
                type="text" 
                value={newCampaignName} 
                onChange={e => setNewCampaignName(e.target.value)}
                placeholder="e.g. Fall 2026 Student Data"
                autoFocus
              />
            </div>
            
            <div className="form-group" style={{ marginTop: "1rem" }}>
              <label>Description (Optional)</label>
              <textarea 
                value={newCampaignDesc} 
                onChange={e => setNewCampaignDesc(e.target.value)}
                placeholder="Brief description..."
                rows={3}
                style={{ width: "100%", padding: "0.75rem", borderRadius: "8px", border: "1px solid #334155", backgroundColor: "#0f172a", color: "#f8fafc" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "1.5rem" }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => {
                  setShowCreateModal(false);
                  setCreateError(null);
                }}
                disabled={isCreating}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary" 
                onClick={handleCreateCampaign}
                disabled={isCreating || !newCampaignName.trim()}
              >
                {isCreating ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
