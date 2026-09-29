import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { AuditLogPaginatedResponse } from "../types/admin";
import "./AdminAuditLogs.css";

/** Turn "campaign_published" into "Campaign published". */
function humanize(value: string): string {
  const text = value.replace(/[_-]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Pick a badge colour based on what the action does. */
function badgeClass(action: string): string {
  const a = action.toLowerCase();
  if (/(delete|remove|reject|fail|error)/.test(a)) return "audit-badge--danger";
  if (/(publish|create|import|submit|approve|login)/.test(a)) return "audit-badge--success";
  if (/(update|edit|change|save)/.test(a)) return "audit-badge--info";
  if (/(close|archive|logout)/.test(a)) return "audit-badge--muted";
  return "audit-badge--neutral";
}

export const AdminAuditLogs: React.FC = () => {
  const [data, setData] = useState<AuditLogPaginatedResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [campaignId, setCampaignId] = useState("");

  const fetchLogs = async (overrides?: {
    action?: string;
    entityType?: string;
    campaignId?: string;
  }) => {
    const a = overrides?.action ?? action;
    const e = overrides?.entityType ?? entityType;
    const c = overrides?.campaignId ?? campaignId;

    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: page.toString(),
        page_size: "50",
      });

      if (a) params.append("action", a);
      if (e) params.append("entity_type", e);
      if (c) params.append("campaign_id", c);

      const response = await fetch(
        `${config.apiBaseUrl}/api/admin/audit-logs?${params.toString()}`,
        { credentials: "include" }
      );

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || "Failed to fetch audit logs");
      }

      setData(await response.json());
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleFilter = (e: React.FormEvent) => {
    e.preventDefault();
    if (page === 1) {
      fetchLogs();
    } else {
      setPage(1); // triggers the effect above
    }
  };

  const handleClear = () => {
    setAction("");
    setEntityType("");
    setCampaignId("");
    if (page === 1) {
      fetchLogs({ action: "", entityType: "", campaignId: "" });
    } else {
      setPage(1);
    }
  };

  const hasFilters = Boolean(action || entityType || campaignId);

  return (
    <div className="admin-audit-logs">
      <div className="audit-header">
        <div>
          <h2 className="audit-title">Audit Logs &amp; Activity</h2>
          <p className="audit-intro">
            A record of who did what across campaigns and student data.
          </p>
        </div>
      </div>

      {/* ---- Filters ---- */}
      <form className="audit-filters" onSubmit={handleFilter}>
        <div className="audit-field">
          <label htmlFor="action">Action</label>
          <input
            id="action"
            type="text"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            placeholder="e.g. campaign_published"
          />
        </div>
        <div className="audit-field">
          <label htmlFor="entityType">Entity Type</label>
          <input
            id="entityType"
            type="text"
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            placeholder="e.g. campaign"
          />
        </div>
        <div className="audit-field">
          <label htmlFor="campaignId">Campaign ID</label>
          <input
            id="campaignId"
            type="text"
            value={campaignId}
            onChange={(e) => setCampaignId(e.target.value)}
            placeholder="UUID"
          />
        </div>
        <div className="audit-filter-actions">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            Filter
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleClear}
            disabled={loading || !hasFilters}
          >
            Clear
          </button>
        </div>
      </form>

      {error && (
        <div className="error-message" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {/* ---- Results ---- */}
      <div className="audit-card">
        {loading && !data ? (
          <div className="audit-empty">
            <span className="audit-empty-text">Loading audit logs...</span>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="audit-empty">
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
              <path d="M14 3v5h5" />
              <path d="M9 13h6M9 17h4" />
            </svg>
            <div className="audit-empty-title">No audit logs found</div>
            <div className="audit-empty-text">
              {hasFilters
                ? "Nothing matches these filters. Try changing or clearing them."
                : "Activity will show up here once admins start making changes."}
            </div>
          </div>
        ) : (
          <>
            <div className="audit-table-wrap">
              <table className="data-table audit-table">
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
                  {data.items.map((log) => {
                    const created = new Date(log.created_at);
                    return (
                      <tr key={log.id}>
                        <td className="audit-time">
                          <div>{created.toLocaleDateString()}</div>
                          <div className="audit-sub">{created.toLocaleTimeString()}</div>
                        </td>
                        <td>
                          <span className={`audit-badge ${badgeClass(log.action)}`}>
                            {humanize(log.action)}
                          </span>
                        </td>
                        <td>
                          <div className="audit-entity">{humanize(log.entity_type)}</div>
                          <div className="audit-sub">{log.entity_id}</div>
                        </td>
                        <td>{log.user_email || "System"}</td>
                        <td>
                          {log.details ? (
                            <details className="audit-details">
                              <summary>View details</summary>
                              <pre>{JSON.stringify(log.details, null, 2)}</pre>
                            </details>
                          ) : (
                            <span className="audit-sub">No details</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="audit-pagination">
              <div className="audit-sub">
                Page {data.page} of {data.total_pages} · {data.total} total
              </div>
              <div className="audit-pagination-btns">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={data.page <= 1 || loading}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={data.page >= data.total_pages || loading}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
