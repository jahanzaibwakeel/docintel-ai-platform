export type User = {
  id: number;
  email: string;
  full_name: string;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type PasswordResetRequestResponse = {
  message: string;
  reset_token: string | null;
};

export type Workspace = {
  id: number;
  name: string;
  document_quota: number | null;
  page_quota: number | null;
  storage_quota_mb: number | null;
  created_at: string;
};

export type WorkspaceMember = {
  id: number;
  workspace_id: number;
  user_id: number;
  user_email: string | null;
  role: "owner" | "admin" | "member" | "viewer";
  created_at: string;
};

export type WorkspaceInvitation = {
  id: number;
  workspace_id: number;
  email: string;
  role: WorkspaceMember["role"];
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

export type WorkspaceInviteResponse = {
  status: "member" | "invited";
  member: WorkspaceMember | null;
  invitation: WorkspaceInvitation | null;
};

export type WorkspaceInvitationList = {
  invitations: WorkspaceInvitation[];
  pending_count: number;
};

export type AuditLog = {
  id: number;
  workspace_id: number | null;
  actor_id: number | null;
  document_id: number | null;
  action: string;
  details: Record<string, unknown> | null;
  created_at: string;
};

export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";
export type DocumentReviewStatus = "unreviewed" | "in_review" | "approved" | "needs_changes";

export type DocumentItem = {
  id: number;
  filename: string;
  title: string | null;
  collection_id: number | null;
  content_type: string;
  status: DocumentStatus;
  summary: string | null;
  key_fields: Record<string, string[]> | null;
  document_type: string | null;
  document_type_confidence: number | null;
  structured_fields: Record<string, Array<{ value: string; confidence: number; source?: string }>> | null;
  risk_flags: Array<{ label: string; severity: "low" | "medium" | "high"; confidence: number; evidence: string }> | null;
  tags: string[];
  favorite: boolean;
  review_status: DocumentReviewStatus;
  review_notes: string | null;
  extraction_diagnostics: ExtractionDiagnostics | null;
  error_message: string | null;
  page_count: number | null;
  file_size_bytes: number | null;
  retention_expires_at: string | null;
  deleted_at: string | null;
  deleted_by_id: number | null;
  processing_started_at: string | null;
  processing_completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentCollection = {
  id: number;
  workspace_id: number;
  created_by_id: number | null;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentAnnotation = {
  id: number;
  document_id: number;
  user_id: number | null;
  page_number: number;
  quote_text: string | null;
  note: string;
  color: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentPermission = {
  id: number;
  document_id: number;
  user_id: number;
  role: "viewer" | "commenter" | "editor";
  granted_by_id: number | null;
  created_at: string;
  updated_at: string;
};

export type WorkspaceUsage = {
  workspace_id: number;
  document_count: number;
  page_count: number;
  storage_bytes: number;
  storage_mb: number;
  document_quota: number | null;
  page_quota: number | null;
  storage_quota_mb: number | null;
  document_quota_used_percent: number | null;
  page_quota_used_percent: number | null;
  storage_quota_used_percent: number | null;
};

export type ExtractionDiagnostics = {
  ocr_enabled?: boolean;
  page_count?: number;
  ocr_page_count?: number;
  native_page_count?: number;
  failed_ocr_page_count?: number;
  pages?: Array<{
    page_number: number;
    method: string;
    character_count: number;
    error?: string | null;
  }>;
};

export type DocumentDetail = DocumentItem & {
  extracted_text: string | null;
};

export type SearchResult = {
  document_id: number;
  filename: string;
  chunk_index: number;
  page_number: number | null;
  text: string;
  score: number;
  vector_score: number;
  keyword_score: number;
};

export type SavedSearch = {
  id: number;
  user_id: number;
  workspace_id: number | null;
  name: string;
  query: string;
  filters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  document_id: number | null;
  filename: string | null;
  chunk_index: number;
  page_number: number | null;
  text: string;
  score: number | null;
  validated: boolean;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
  confidence: number;
  prompt_version: string;
  grounded: boolean;
};

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
};

export type DocumentComparison = {
  left: { id: number; filename: string; document_type: string | null };
  right: { id: number; filename: string; document_type: string | null };
  similarity: number;
  summary: { left: string | null; right: string | null; changed: boolean };
  field_changes: Record<string, { only_in_left: string[]; only_in_right: string[]; shared: string[] }>;
  risk_changes: { only_in_left: string[]; only_in_right: string[]; shared: string[] };
  term_changes: { common: string[]; only_in_left: string[]; only_in_right: string[] };
};

export type AdminStats = {
  users: number;
  workspaces: number;
  documents: number;
  ready_documents: number;
  failed_documents: number;
  processing_documents: number;
  uploaded_documents: number;
};

export type AdminOpsHealth = AdminStats & {
  status: string;
  recent_failures: AdminDocument[];
  metrics: Record<string, number>;
};

export type AdminDocument = {
  id: number;
  filename: string;
  owner_email: string | null;
  workspace_id: number | null;
  status: string;
  document_type: string | null;
  error_message: string | null;
  created_at: string;
  processing_started_at: string | null;
  processing_completed_at: string | null;
};

export type NotificationItem = {
  id: number;
  user_id: number;
  workspace_id: number | null;
  document_id: number | null;
  kind: string;
  title: string;
  message: string;
  read_at: string | null;
  created_at: string;
};

export type NotificationList = {
  unread_count: number;
  notifications: NotificationItem[];
};

export type AiProviderStatus = {
  provider: string;
  configured: boolean;
  healthy: boolean | null;
  model: string;
  embedding_model: string;
  embedding_dimensions: number;
  max_context_chars: number;
  request_timeout_seconds: number;
  pii_redaction_enabled: boolean;
  external_ai_with_pii_allowed: boolean;
  detail: string;
};
