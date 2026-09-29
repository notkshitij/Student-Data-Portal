import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { StudentCampaignListResponse } from "../types";
import { CampaignDetail } from "./CampaignDetail";

interface StudentDashboardProps {
  user: any;
}

function parseCampaignHash(): string | null {
  const m = window.location.hash.match(/^#campaign\/(.+)$/);
  return m ? decodeURIComponent(m[1]) : null;
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export const StudentDashboard: React.FC<StudentDashboardProps> = ({ user }) => {
  const [campaigns, setCampaigns] = useState<StudentCampaignListResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedCampaignId, setSelectedCampaignIdState] = useState<string | null>(parseCampaignHash());

  // Keep the open campaign in the URL hash so the browser / phone Back gesture
  // returns to the campaign list (there is no on-screen back button).
  const setSelectedCampaignId = (id: string | null) => {
    setSelectedCampaignIdState(id);
    if (id) {
      window.location.hash = `campaign/${id}`;
    } else {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
  };

  useEffect(() => {
    const onHashChange = () => setSelectedCampaignIdState(parseCampaignHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [selectedCampaignId]);

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

  const pendingCount = campaigns.filter(
    c => String(c.submission_status).toUpperCase() === "PENDING"
  ).length;
  const submittedCount = campaigns.length - pendingCount;

  return (
    <div className="student-dashboard">
      <div className="student-hero">
        <img src="/logo.png" alt="Logo" className="student-hero-logo" />
        <div className="student-hero-text">
          <span className="student-hero-kicker">{getGreeting()}</span>
          <h2 className="student-hero-title">Student Data Verification</h2>
          <p className="student-hero-sub">
            Review your details, fill in what's missing and submit.
          </p>
        </div>
      </div>

      <div className="student-user-chip" title={user?.email}>
        <span className="student-user-dot" />
        <span className="student-user-label">Signed in as</span>
        <span className="student-user-email">{user?.email}</span>
      </div>

      {!loading && !error && campaigns.length > 0 && (
        <div className="student-stats">
          <div className="student-stat">
            <span className="student-stat-value">{campaigns.length}</span>
            <span className="student-stat-label">Campaigns</span>
          </div>
          <div className="student-stat student-stat--pending">
            <span className="student-stat-value">{pendingCount}</span>
            <span className="student-stat-label">Pending</span>
          </div>
          <div className="student-stat student-stat--done">
            <span className="student-stat-value">{submittedCount}</span>
            <span className="student-stat-label">Submitted</span>
          </div>
        </div>
      )}

      {loading ? (
        <div className="page-loader" role="status" aria-live="polite">
          <span className="spinner spinner--lg" />
          <span>Loading your campaigns...</span>
        </div>
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
        <div className="student-campaign-list">
          {campaigns.map(campaign => {
            const isPending = String(campaign.submission_status).toUpperCase() === "PENDING";
            return (
              <div
                key={campaign.campaign_id}
                className="student-campaign"
                role="button"
                tabIndex={0}
                onClick={() => setSelectedCampaignId(campaign.campaign_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelectedCampaignId(campaign.campaign_id);
                  }
                }}
              >
                <div className="student-campaign-icon" aria-hidden="true">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
                    <path d="M14 3v5h5" />
                    <path d="M9 13l2 2 4-4" />
                  </svg>
                </div>

                <div className="student-campaign-body">
                  <div className="student-campaign-top">
                    <h3 className="student-campaign-name">{campaign.name}</h3>
                    <span className={`badge badge-submission ${campaign.submission_status.toLowerCase()}`}>
                      {campaign.submission_status}
                    </span>
                  </div>
                  <p className="student-campaign-hint">
                    {isPending
                      ? "Check your imported details and complete the missing information."
                      : "You've submitted your information. You can review it any time."}
                  </p>
                  <div className="student-campaign-footer">
                    <span className="campaign-date">
                      Added on {new Date(campaign.created_at).toLocaleDateString()}
                    </span>
                    <button className="student-open-btn" type="button">
                      {isPending ? "Review & Verify" : "View"} <span aria-hidden="true">&rarr;</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
