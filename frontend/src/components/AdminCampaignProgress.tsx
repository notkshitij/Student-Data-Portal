import React, { useEffect, useState } from "react";
import { config } from "../config";
import type { 
  AdminCampaignProgressResponse, 
  AdminStudentListPaginatedResponse,
  AdminStudentDetailResponse
} from "../types/admin";

interface AdminCampaignProgressProps {
  campaignId: string;
}

export const AdminCampaignProgress: React.FC<AdminCampaignProgressProps> = ({ campaignId }) => {
  const [progress, setProgress] = useState<AdminCampaignProgressResponse | null>(null);
  const [studentsData, setStudentsData] = useState<AdminStudentListPaginatedResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<"ALL" | "PENDING" | "SUBMITTED">("ALL");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<AdminStudentDetailResponse | null>(null);
  const [studentLoading, setStudentLoading] = useState(false);

  const fetchProgressAndStudents = async () => {
    try {
      setLoading(true);
      
      const [progressRes, studentsRes] = await Promise.all([
        fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/progress`, { credentials: "include" }),
        fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/students?page=${page}&page_size=50${statusFilter !== "ALL" ? `&status=${statusFilter}` : ""}`, { credentials: "include" })
      ]);
      
      if (!progressRes.ok) throw new Error("Failed to load progress data");
      if (!studentsRes.ok) throw new Error("Failed to load students data");
      
      setProgress(await progressRes.json());
      setStudentsData(await studentsRes.json());
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProgressAndStudents();
  }, [campaignId, statusFilter, page]);

  const handleStudentClick = async (studentId: string) => {
    try {
      setStudentLoading(true);
      setError(null);
      const res = await fetch(`${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/students/${studentId}`, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to load student details");
      setSelectedStudent(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setStudentLoading(false);
    }
  };

  if (loading && !progress) return <div className="loading-state">Loading progress...</div>;
  if (error && !progress) return <div className="error-state">{error}</div>;
  if (!progress || !studentsData) return null;

  if (selectedStudent) {
    return (
      <div className="student-detail-view" style={{ marginTop: "2rem", borderTop: "1px solid #e2e8f0", paddingTop: "2rem" }}>
        <button className="btn back-btn" onClick={() => setSelectedStudent(null)} style={{ marginBottom: "1.5rem" }}>
          &larr; Back to Student List
        </button>
        
        <h3>Student Details: {selectedStudent.email}</h3>
        <div style={{ marginBottom: "1.5rem" }}>
          <span className={`badge badge-submission ${selectedStudent.status.toLowerCase()}`}>
            {selectedStudent.status}
          </span>
          {selectedStudent.submitted_at && (
            <span style={{ marginLeft: "1rem", color: "#64748b", fontSize: "0.875rem" }}>
              Submitted at: {new Date(selectedStudent.submitted_at).toLocaleString()}
            </span>
          )}
        </div>
        
        <table className="campaigns-table" style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ backgroundColor: "#f8fafc", borderBottom: "2px solid #e2e8f0" }}>
              <th style={{ padding: "0.75rem" }}>Field Name</th>
              <th style={{ padding: "0.75rem" }}>Type</th>
              <th style={{ padding: "0.75rem" }}>Original Data (Imported)</th>
              <th style={{ padding: "0.75rem" }}>Student Response</th>
            </tr>
          </thead>
          <tbody>
            {selectedStudent.fields.map(field => (
              <tr key={field.field_id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td style={{ padding: "0.75rem", fontWeight: 500 }}>{field.field_name}</td>
                <td style={{ padding: "0.75rem" }}>
                  {field.requires_student_input ? (
                    <span className="badge" style={{ backgroundColor: "#dbeafe", color: "#1e3a8a" }}>Collect</span>
                  ) : (
                    <span className="badge" style={{ backgroundColor: "#f1f5f9", color: "#475569" }}>Standard</span>
                  )}
                </td>
                <td style={{ padding: "0.75rem", color: field.requires_student_input && field.imported_value === "[COLLECT]" ? "#94a3b8" : "inherit" }}>
                  {field.imported_value || "-"}
                </td>
                <td style={{ padding: "0.75rem", fontWeight: field.requires_student_input ? 600 : 400 }}>
                  {field.requires_student_input ? (
                    field.student_response ? (
                      <span style={{ color: "#059669" }}>{field.student_response}</span>
                    ) : (
                      <span style={{ color: "#94a3b8", fontStyle: "italic" }}>No response yet</span>
                    )
                  ) : (
                    <span style={{ color: "#94a3b8" }}>N/A</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const handleExport = () => {
    window.location.href = `${config.apiBaseUrl}/api/admin/campaigns/${campaignId}/export?status=${statusFilter}`;
  };

  return (
    <div className="campaign-progress" style={{ marginTop: "2.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h3 className="form-title" style={{ margin: 0 }}>Submission Progress</h3>
        <button 
          className="btn btn-primary" 
          onClick={handleExport}
          title="Export CSV data for this campaign"
        >
          Export CSV ({statusFilter === "ALL" ? "All Students" : statusFilter === "PENDING" ? "Pending Only" : "Submitted Only"})
        </button>
      </div>
      
      <div style={{ padding: "1.5rem", backgroundColor: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem", fontWeight: 500 }}>
          <span>{progress.submitted_students} / {progress.total_students} submitted</span>
          <span>{progress.submission_percentage.toFixed(1)}%</span>
        </div>
        <div style={{ width: "100%", backgroundColor: "#e2e8f0", borderRadius: "9999px", height: "12px", overflow: "hidden" }}>
          <div 
            style={{ 
              width: `${progress.submission_percentage}%`, 
              backgroundColor: "#2563eb", 
              height: "100%",
              transition: "width 0.5s ease"
            }} 
          />
        </div>
        
        <div style={{ display: "flex", gap: "2rem", marginTop: "1rem", fontSize: "0.875rem", color: "#475569" }}>
          <div><strong>Submitted:</strong> {progress.submitted_students}</div>
          <div><strong>Pending:</strong> {progress.pending_students}</div>
          <div><strong>Total:</strong> {progress.total_students}</div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h4 style={{ margin: 0 }}>Enrolled Students</h4>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <select 
            value={statusFilter} 
            onChange={(e) => {
              setStatusFilter(e.target.value as "ALL" | "PENDING" | "SUBMITTED");
              setPage(1);
            }}
            className="form-control"
            style={{ width: "auto" }}
          >
            <option value="ALL">All Students</option>
            <option value="PENDING">Pending Only</option>
            <option value="SUBMITTED">Submitted Only</option>
          </select>
        </div>
      </div>
      
      {studentLoading && <div className="loading-state" style={{ padding: "1rem" }}>Loading student details...</div>}
      
      <div style={{ overflowX: "auto" }}>
        <table className="campaigns-table">
          <thead>
            <tr>
              <th>Student Email</th>
              <th>Status</th>
              <th>Submitted At</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {studentsData.items.map(student => (
              <tr key={student.student_id}>
                <td>{student.email}</td>
                <td>
                  <span className={`badge badge-submission ${student.status.toLowerCase()}`}>
                    {student.status}
                  </span>
                </td>
                <td>
                  {student.submitted_at 
                    ? new Date(student.submitted_at).toLocaleString() 
                    : "-"}
                </td>
                <td>
                  <button 
                    className="btn btn-secondary" 
                    style={{ padding: "0.25rem 0.75rem", fontSize: "0.875rem" }}
                    onClick={() => handleStudentClick(student.student_id)}
                  >
                    View Data
                  </button>
                </td>
              </tr>
            ))}
            {studentsData.items.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", padding: "2rem", color: "#64748b" }}>
                  No students found matching the selected filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* Basic Pagination */}
      {studentsData.total > studentsData.page_size && (
        <div style={{ display: "flex", justifyContent: "center", gap: "1rem", marginTop: "1.5rem" }}>
          <button 
            className="btn btn-secondary" 
            disabled={page === 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <span style={{ display: "flex", alignItems: "center" }}>
            Page {page} of {Math.ceil(studentsData.total / studentsData.page_size)}
          </span>
          <button 
            className="btn btn-secondary" 
            disabled={page >= Math.ceil(studentsData.total / studentsData.page_size)}
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
