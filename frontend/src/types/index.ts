import type { FieldValidationConfig } from "./admin";

export type CampaignStatus = "DRAFT" | "PUBLISHED" | "CLOSED";
export type SubmissionStatus = "PENDING" | "SUBMITTED";

export interface StudentCampaignListResponse {
  campaign_id: string;
  name: string;
  campaign_status: CampaignStatus;
  submission_status: SubmissionStatus;
  created_at: string;
}

export interface StudentCampaignFieldResponse {
  field_id: string;
  field_name: string;
  field_order: number;
  requires_student_input: boolean;
  value: string | null;
  validation_config: FieldValidationConfig | null;
}

export interface StudentCampaignDetailResponse {
  campaign_id: string;
  name: string;
  description: string | null;
  campaign_status: CampaignStatus;
  submission_status: SubmissionStatus;
  fields: StudentCampaignFieldResponse[];
}
