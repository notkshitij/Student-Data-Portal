import React, { useEffect, useState, useCallback, useRef } from "react";
import { config } from "../config";
import type { AdminCampaignListResponse } from "../types/admin";
import { AdminCampaignDetail } from "./AdminCampaignDetail";
import { AdminAuditLogs } from "./AdminAuditLogs";
import { Loader, TopProgressBar } from "./Loader";

interface AdminDashboardProps {
  user: any;
  onLogout?: () => void;
}

type SidebarTab = "dashboard" | "campaigns" | "audit";

const navIconProps = {
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

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
  // First load shows the full loader; later refreshes keep the content on screen
  const [refreshing, setRefreshing] = useState(false);
  const hasLoadedOnce = useRef(false);
  const [menuOpen, setMenuOpen] = useState(false);
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
      if (hasLoadedOnce.current) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      const response = await fetch(`${config.apiBaseUrl}/api/admin/campaigns`, {
        credentials: "include",
      });
      
      if (!response.ok) {
        throw new Error("Failed to load campaigns.");
      }
      
      const data = await response.json();
      setCampaigns(data);
      hasLoadedOnce.current = true;
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, [activeTab]); // Refetch if switching tabs just in case

  // All admin pages: drop the blue photo background and let the white panel fill the screen
  useEffect(() => {
    document.body.classList.add("admin-fullscreen");
    return () => document.body.classList.remove("admin-fullscreen");
  }, []);

  const campaignDetailView = selectedCampaignId ? (
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
  ) : null;

  // Mobile navigation helpers + dashboard stats
  const mobileTitle =
    activeTab === "dashboard" ? "Overview" : activeTab === "campaigns" ? "Campaigns" : "Audit Logs";

  const goMobileTab = (tab: SidebarTab) => {
    setMenuOpen(false);
    setActiveTab(tab);
    window.scrollTo({ top: 0 });
  };

  // Calculate Dashboard stats
  const totalCampaigns = campaigns.length;
  const draftCampaigns = campaigns.filter(c => c.status === "DRAFT").length;
  const publishedCampaigns = campaigns.filter(c => c.status === "PUBLISHED").length;
  const closedCampaigns = campaigns.filter(c => c.status === "CLOSED").length;
  const totalStudents = campaigns.reduce((acc, c) => acc + c.student_count, 0);
  const avgStudents = totalCampaigns ? Math.round(totalStudents / totalCampaigns) : 0;

  const statusSegments = [
    { key: "published", label: "Published (Live)", count: publishedCampaigns },
    { key: "draft", label: "Drafts", count: draftCampaigns },
    { key: "closed", label: "Closed", count: closedCampaigns },
  ];

  const recentCampaigns = [...campaigns]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 5);

  const attentionItems = campaigns.flatMap(c => {
    const items: { id: string; name: string; msg: string; level: "warn" | "info" }[] = [];
    if (c.status !== "CLOSED" && !c.has_excel) {
      items.push({ id: c.campaign_id, name: c.name, msg: "Excel source is missing", level: "warn" });
    }
    if (c.status === "DRAFT" && c.has_excel) {
      items.push({ id: c.campaign_id, name: c.name, msg: "Draft - ready to review & publish", level: "info" });
    }
    return items;
  });

  return (
    <div className="admin-layout">
      <TopProgressBar active={refreshing} />

      {/* Mobile-only top bar (hidden on desktop via CSS) */}
      <header className="admin-mobile-topbar">
        <img src="/logo.png" alt="" className="admin-mobile-logo" />
        <div className="admin-mobile-title">
          {selectedCampaignId ? (
            <button
              type="button"
              className="admin-mobile-back"
              onClick={() => {
                setSelectedCampaignId(null);
                fetchCampaigns();
              }}
            >
              &lsaquo; Campaigns
            </button>
          ) : (
            <span>{mobileTitle}</span>
          )}
        </div>
        <button
          type="button"
          className="admin-mobile-avatar"
          onClick={() => setMenuOpen((open) => !open)}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          aria-label="Account menu"
        >
          {(user?.email || "A").charAt(0).toUpperCase()}
        </button>
      </header>

      {menuOpen && (
        <>
          <div className="admin-mobile-menu-backdrop" onClick={() => setMenuOpen(false)} />
          <div className="admin-mobile-menu" role="menu">
            <div className="admin-mobile-menu-email">{user?.email}</div>
            {onLogout && (
              <button
                type="button"
                role="menuitem"
                className="admin-mobile-menu-signout"
                onClick={() => {
                  setMenuOpen(false);
                  onLogout();
                }}
              >
                Sign Out
              </button>
            )}
          </div>
        </>
      )}

      {/* Mobile-only bottom tab bar (hidden on desktop via CSS) */}
      <nav className="admin-mobile-bottomnav" aria-label="Admin navigation">
        <button
          type="button"
          className={`admin-mobile-tab ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => goMobileTab("dashboard")}
        >
          <svg {...navIconProps}>
            <rect x="3" y="3" width="7" height="9" rx="1.5" />
            <rect x="14" y="3" width="7" height="5" rx="1.5" />
            <rect x="14" y="12" width="7" height="9" rx="1.5" />
            <rect x="3" y="16" width="7" height="5" rx="1.5" />
          </svg>
          <span>Overview</span>
        </button>
        <button
          type="button"
          className={`admin-mobile-tab ${activeTab === "campaigns" ? "active" : ""}`}
          onClick={() => goMobileTab("campaigns")}
        >
          <svg {...navIconProps}>
            <rect x="5" y="3" width="14" height="18" rx="2" />
            <path d="M9 8h6M9 12h6M9 16h4" />
          </svg>
          <span>Campaigns</span>
        </button>
        <button
          type="button"
          className={`admin-mobile-tab ${activeTab === "audit" ? "active" : ""}`}
          onClick={() => goMobileTab("audit")}
        >
          <svg {...navIconProps}>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
          </svg>
          <span>Audit Logs</span>
        </button>
      </nav>

      {/* Sidebar Navigation */}
      <div className="admin-sidebar">
        <div className="admin-profile">
          <img src="/logo.png" alt="Logo" className="admin-profile-logo" />
          <div>
            <h2 className="admin-profile-title">Admin Panel</h2>
            <div className="admin-profile-email">{user?.email}</div>
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
            className="admin-nav-item admin-nav-signout"
            onClick={onLogout}
          >
            Sign Out
          </button>
        )}
      </div>

      {/* Main Content Area */}
      <div className="admin-main-content">
        {campaignDetailView}
        {!selectedCampaignId && activeTab === "dashboard" && (
          <div>
            <h2 className="admin-page-title">System Overview</h2>
            {loading ? (
              <Loader label="Loading dashboard..." />
            ) : error ? (
              <div className="error-state">{error} <button onClick={fetchCampaigns} style={{ marginLeft: "1rem" }}>Retry</button></div>
            ) : (
              <>
                <div className="admin-stats-grid">
                  <div className="stat-card">
                    <span className="stat-label">Total Campaigns</span>
                    <span className="stat-value">{totalCampaigns}</span>
                  </div>
                  <div className="stat-card stat-card--live">
                    <span className="stat-label">Published (Live)</span>
                    <span className="stat-value">{publishedCampaigns}</span>
                  </div>
                  <div className="stat-card stat-card--draft">
                    <span className="stat-label">Drafts</span>
                    <span className="stat-value">{draftCampaigns}</span>
                  </div>
                  <div className="stat-card stat-card--closed">
                    <span className="stat-label">Closed</span>
                    <span className="stat-value">{closedCampaigns}</span>
                  </div>
                  <div className="stat-card stat-card--students">
                    <span className="stat-label">Total Enrolled Students</span>
                    <span className="stat-value">{totalStudents}</span>
                  </div>
                </div>
                
                <div className="admin-panel-card">
                  <h3 className="admin-panel-title">Quick Actions</h3>
                  <div className="admin-panel-actions">
                    <button className="btn btn-primary" onClick={() => setActiveTab("campaigns")}>
                      View All Campaigns
                    </button>
                    <button className="btn btn-secondary" onClick={() => setActiveTab("audit")}>
                      View Audit Logs
                    </button>
                  </div>
                </div>

                <div className="admin-insights-grid">
                  {/* Status breakdown */}
                  <div className="admin-panel-card admin-insight-card">
                    <h3 className="admin-panel-title">Campaign Status</h3>
                    {totalCampaigns === 0 ? (
                      <p className="admin-muted">No campaigns yet. Create one to get started.</p>
                    ) : (
                      <>
                        <div className="status-bar">
                          {statusSegments.map(s => s.count > 0 && (
                            <div
                              key={s.key}
                              className={`status-bar-seg seg-${s.key}`}
                              style={{ width: `${(s.count / totalCampaigns) * 100}%` }}
                              title={`${s.label}: ${s.count}`}
                            />
                          ))}
                        </div>
                        <ul className="status-legend">
                          {statusSegments.map(s => (
                            <li key={s.key}>
                              <span className={`status-dot seg-${s.key}`} />
                              <span className="status-legend-name">{s.label}</span>
                              <span className="status-legend-count">{s.count}</span>
                              <span className="status-legend-pct">{Math.round((s.count / totalCampaigns) * 100)}%</span>
                            </li>
                          ))}
                        </ul>
                        <div className="admin-insight-footer">
                          Avg. <strong>{avgStudents}</strong> students per campaign
                        </div>
                      </>
                    )}
                  </div>

                  {/* Recent campaigns */}
                  <div className="admin-panel-card admin-insight-card admin-insight-card--tall">
                    <div className="admin-insight-head">
                      <h3 className="admin-panel-title">Recent Campaigns</h3>
                      <button className="admin-link-btn" onClick={() => setActiveTab("campaigns")}>View all</button>
                    </div>
                    {recentCampaigns.length === 0 ? (
                      <p className="admin-muted">Nothing here yet.</p>
                    ) : (
                      <ul className="recent-list">
                        {recentCampaigns.map(c => (
                          <li key={c.campaign_id} className="recent-item" onClick={() => setSelectedCampaignId(c.campaign_id)}>
                            <div className="recent-main">
                              <span className="recent-name">{c.name}</span>
                              <span className="recent-meta">
                                {c.student_count} students · {c.field_count} fields · Updated {new Date(c.updated_at).toLocaleDateString()}
                              </span>
                            </div>
                            <span className={`badge badge-${c.status.toLowerCase()}`}>{c.status}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Needs attention */}
                  <div className="admin-panel-card admin-insight-card">
                    <h3 className="admin-panel-title">Needs Attention</h3>
                    {attentionItems.length === 0 ? (
                      <p className="admin-muted">All good - nothing needs your attention right now.</p>
                    ) : (
                      <ul className="attention-list">
                        {attentionItems.map((a, i) => (
                          <li key={`${a.id}-${i}`} className="attention-item" onClick={() => setSelectedCampaignId(a.id)}>
                            <span className={`attention-dot attention-dot--${a.level}`} />
                            <div>
                              <div className="attention-name">{a.name}</div>
                              <div className="attention-msg">{a.msg}</div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {!selectedCampaignId && activeTab === "campaigns" && (
          <div>
            <div className="admin-page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: "2rem" }}>
              <h2 style={{ margin: 0 }}>Campaigns</h2>
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                + Create Campaign
              </button>
            </div>
            
            {loading ? (
              <Loader label="Loading campaigns..." />
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
                        Excel Source: {campaign.has_excel ? <span className="status-ok">Uploaded</span> : <span className="status-missing">Missing</span>}
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

        {!selectedCampaignId && activeTab === "audit" && (
          <div>
            <AdminAuditLogs />
          </div>
        )}
      </div>

      {showCreateModal && (
        <div
          className="modal-overlay"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !isCreating) {
              setShowCreateModal(false);
              setCreateError(null);
            }
          }}
        >
          <div className="modal-content">
            <h3>Create New Campaign</h3>
            {createError && <div className="error-message" style={{ marginBottom: "1rem" }}>{createError}</div>}
            
            <div className="form-group" style={{ marginBottom: "1rem" }}>
              <label htmlFor="newCampaignName">Campaign Name *</label>
              <input 
                id="newCampaignName"
                type="text" 
                value={newCampaignName} 
                onChange={e => setNewCampaignName(e.target.value)}
                placeholder="e.g. Fall 2026 Student Data"
                autoFocus
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="newCampaignDesc">Description (Optional)</label>
              <textarea 
                id="newCampaignDesc"
                value={newCampaignDesc} 
                onChange={e => setNewCampaignDesc(e.target.value)}
                placeholder="Brief description..."
                rows={3}
              />
            </div>

            <div className="modal-actions">
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
                {isCreating ? <><Loader variant="inline" />Creating...</> : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
