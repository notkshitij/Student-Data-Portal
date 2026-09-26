import type { CampaignStatus } from "./index";

export interface AdminCampaignListResponse {
  campaign_id: string;
  name: string;
  status: CampaignStatus;
  student_count: number;
  field_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminCampaignDetailResponse {
  campaign_id: string;
  name: string;
  description: string | null;
  status: CampaignStatus;
  student_count: number;
  field_count: number;
  collect_field_count: number;
  created_at: string;
  updated_at: string;
}

export interface GenericAdminResponse {
  message: string;
}

export type FieldType = "text" | "textarea" | "number" | "email" | "phone" | "date" | "select";

export interface BaseValidationRules {
  required?: boolean;
}

export interface TextValidationRules extends BaseValidationRules {
  min_length?: number | null;
  max_length?: number | null;
}

export interface NumberValidationRules extends BaseValidationRules {
  min_value?: number | null;
  max_value?: number | null;
}

export interface EmailValidationRules extends BaseValidationRules {
  allowed_domains?: string[] | null;
}

export interface SelectValidationRules extends BaseValidationRules {
  options?: string[];
}

export interface DateValidationRules extends BaseValidationRules {}
export interface PhoneValidationRules extends BaseValidationRules {}

export interface FieldValidationConfig {
  type: FieldType;
  rules: TextValidationRules & NumberValidationRules & EmailValidationRules & SelectValidationRules;
}

export interface AdminFormField {
  id: string;
  field_name: string;
  field_order: number;
  requires_student_input: boolean;
  validation_config: FieldValidationConfig | null;
}

export interface AdminFormConfigResponse {
  campaign_id: string;
  fields: AdminFormField[];
}

export interface AdminFormFieldUpdate {
  id: string;
  validation_config: FieldValidationConfig;
}

export interface FieldOrderUpdate {
  id: string;
  field_order: number;
}

export interface AdminFormConfigUpdateRequest {
  field_orders: FieldOrderUpdate[];
  fields: AdminFormFieldUpdate[];
}

export interface AdminCampaignProgressResponse {
  campaign_id: string;
  campaign_name: string;
  campaign_status: CampaignStatus;
  total_students: number;
  pending_students: number;
  submitted_students: number;
  submission_percentage: number;
}

export interface AdminStudentListResponse {
  student_id: string;
  email: string;
  status: "PENDING" | "SUBMITTED";
  submitted_at: string | null;
}

export interface AdminStudentListPaginatedResponse {
  items: AdminStudentListResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminStudentDetailField {
  field_id: string;
  field_name: string;
  field_order: number;
  requires_student_input: boolean;
  imported_value: string | null;
  student_response: string | null;
  validation_config: FieldValidationConfig | null;
}

export interface AdminStudentDetailResponse {
  student_id: string;
  email: string;
  campaign_id: string;
  status: "PENDING" | "SUBMITTED";
  submitted_at: string | null;
  fields: AdminStudentDetailField[];
}

export interface AuditLogResponse {
  id: string;
  user_id: string | null;
  user_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, any> | null;
  created_at: string;
}

export interface AuditLogPaginatedResponse {
  items: AuditLogResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
