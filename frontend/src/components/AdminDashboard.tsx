import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AdminCampaignListResponse } from "../types/admin";
import { AdminCampaignDetail } from "./AdminCampaignDetail";
import { AdminAuditLogs } from "./AdminAuditLogs";

interface AdminDashboardProps {
  user: any;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ user }) => {
  const [campaigns, setCampaigns] = useState<AdminCampaignListResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [showAuditLogs, setShowAuditLogs] = useState(false);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
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
  }, []);

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

  if (showAuditLogs) {
    return <AdminAuditLogs onBack={() => setShowAuditLogs(false)} />;
  }

  return (
    <div className="student-dashboard">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Admin Dashboard ({user?.email})</h2>
          <p>Manage data verification campaigns.</p>
        </div>
        <button className="btn btn-secondary" onClick={() => setShowAuditLogs(true)}>
          View Audit Logs
        </button>
      </div>

      {loading ? (
        <div className="loading-state">Loading campaigns...</div>
      ) : error ? (
        <div className="error-state">
          <p>{error}</p>
        </div>
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
                <h3>{campaign.name}</h3>
                <span className="badge badge-status">
                  {campaign.status}
                </span>
              </div>
              <div className="campaign-card-footer" style={{ flexDirection: "column", alignItems: "flex-start", gap: "0.5rem" }}>
                <span className="campaign-date">
                  {campaign.student_count} Students | {campaign.field_count} Fields
                </span>
                <span className="campaign-date">
                  Created on {new Date(campaign.created_at).toLocaleDateString()}
                </span>
                <button className="btn btn-secondary" style={{ width: "100%", marginTop: "0.5rem" }}>Manage</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
