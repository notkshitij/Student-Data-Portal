import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { StudentCampaignListResponse } from "../types";
import { CampaignDetail } from "./CampaignDetail";

interface StudentDashboardProps {
  user: any;
}

export const StudentDashboard: React.FC<StudentDashboardProps> = ({ user }) => {
  const [campaigns, setCampaigns] = useState<StudentCampaignListResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchCampaigns = async () => {
      try {
        const response = await fetch(`${config.apiBaseUrl}/api/student/campaigns`, {
          credentials: "include",
        });
        
        if (!response.ok) {
          throw new Error("Failed to load campaigns.");
        }
        
        const data = await response.json();
        if (!cancelled) {
          setCampaigns(data);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || "An error occurred.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchCampaigns();

    return () => {
      cancelled = true;
    };
  }, []);

  // If a campaign is selected, render the detail view instead
  if (selectedCampaignId) {
    return (
      <CampaignDetail 
        campaignId={selectedCampaignId} 
        onBack={() => setSelectedCampaignId(null)} 
      />
    );
  }

  return (
    <div className="student-dashboard">
      <div className="dashboard-header">
        <h2>Welcome, {user?.email}</h2>
        <p>Please select a campaign below to review and verify your information.</p>
      </div>

      {loading ? (
        <div className="loading-state">Loading your campaigns...</div>
      ) : error ? (
        <div className="error-state">
          <p>{error}</p>
        </div>
      ) : campaigns.length === 0 ? (
        <div className="empty-state">
          <h3>No campaigns found</h3>
          <p>You do not have any active data verification campaigns at this time.</p>
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
                <span className={`badge badge-submission ${campaign.submission_status.toLowerCase()}`}>
                  {campaign.submission_status}
                </span>
              </div>
              <div className="campaign-card-footer">
                <span className="campaign-date">
                  Added on {new Date(campaign.created_at).toLocaleDateString()}
                </span>
                <button className="btn btn-secondary">Open</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
