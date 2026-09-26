import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AuditLogPaginatedResponse } from "../types/admin";
interface AdminAuditLogsProps {
  onBack: () => void;
}

export const AdminAuditLogs: React.FC<AdminAuditLogsProps> = ({ onBack }) => {
  const [data, setData] = useState<AuditLogPaginatedResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [campaignId, setCampaignId] = useState("");
  
  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: "50",
      });
      
      if (action) params.append("action", action);
      if (entityType) params.append("entity_type", entityType);
      if (campaignId) params.append("campaign_id", campaignId);
      
      const response = await fetch(`${config.apiBaseUrl}/api/admin/audit-logs?${params.toString()}`, {
        credentials: "include",
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || "Failed to fetch audit logs");
      }
      
      const resData = await response.json();
      setData(resData);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchLogs();
  }, [page]);
  
  const handleFilter = (e: React.FormEvent) => {
    e.preventDefault();
    if (page === 1) {
      fetchLogs();
    } else {
      setPage(1); // will trigger useEffect
    }
  };
  
  const handleClear = () => {
    setAction("");
    setEntityType("");
    setCampaignId("");
    if (page === 1) {
      setTimeout(fetchLogs, 0); // Wait for state to clear
    } else {
      setPage(1);
    }
  };

  return (
    <div className="admin-audit-logs">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2>Audit Logs & Activity</h2>
        <button onClick={onBack} style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer", textDecoration: "underline", padding: 0 }}>← Back to Dashboard</button>
      </div>
      
      <div className="card" style={{ marginBottom: "2rem" }}>
        <form onSubmit={handleFilter} style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <label htmlFor="action">Action</label>
            <input
              id="action"
              type="text"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="e.g. campaign_published"
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <label htmlFor="entityType">Entity Type</label>
            <input
              id="entityType"
              type="text"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              placeholder="e.g. campaign"
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <label htmlFor="campaignId">Campaign ID</label>
            <input
              id="campaignId"
              type="text"
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
              placeholder="UUID"
            />
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button type="submit" disabled={loading}>Filter</button>
            <button type="button" onClick={handleClear} disabled={loading} style={{ background: "#f3f4f6", color: "#374151" }}>Clear</button>
          </div>
        </form>
      </div>
      
      {error && <div className="error-message" style={{ marginBottom: "1rem" }}>{error}</div>}
      
      <div className="card">
        {loading && !data ? (
          <div>Loading audit logs...</div>
        ) : !data || data.items.length === 0 ? (
          <div>No audit logs found.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>User</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((log) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: "nowrap" }}>{new Date(log.created_at).toLocaleString()}</td>
                    <td><span style={{ fontWeight: 600, color: "#111827" }}>{log.action}</span></td>
                    <td>
                      <div>{log.entity_type}</div>
                      <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>{log.entity_id}</div>
                    </td>
                    <td>{log.user_email || "System"}</td>
                    <td>
                      {log.details ? (
                        <pre style={{ margin: 0, fontSize: "0.85rem", background: "#f9fafb", padding: "0.5rem", borderRadius: "4px" }}>
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      ) : (
                        <span style={{ color: "#9ca3af", fontStyle: "italic" }}>No details</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem" }}>
              <div>
                Showing page {data.page} of {data.total_pages} (Total: {data.total})
              </div>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button 
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={data.page <= 1 || loading}
                >
                  Previous
                </button>
                <button 
                  onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                  disabled={data.page >= data.total_pages || loading}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
