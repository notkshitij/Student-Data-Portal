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

export interface AdminFormConfigUpdateRequest {
  fields: AdminFormFieldUpdate[];
}
