import type { AdminDocument, AdminStats, AiProviderStatus, AskResponse, AuditLog, AuthTokens, ChatMessage, Citation, DocumentAnnotation, DocumentCollection, DocumentComparison, DocumentDetail, DocumentItem, DocumentReviewStatus, NotificationList, PasswordResetRequestResponse, SavedSearch, SearchResult, User, Workspace, WorkspaceInvitation, WorkspaceInvitationList, WorkspaceInviteResponse, WorkspaceMember } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type DocumentFilters = {
  workspaceId?: number | null;
  status?: string;
  documentType?: string;
  riskSeverity?: string;
  tag?: string;
  favorite?: boolean;
  reviewStatus?: DocumentReviewStatus | "";
  collectionId?: number | null;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, token?: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(response.status, payload.detail ?? "Request failed");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthTokens>("/auth/login", null, {
      method: "POST",
      body: JSON.stringify({ email, password })
    }),
  register: (fullName: string, email: string, password: string) =>
    request<AuthTokens>("/auth/register", null, {
      method: "POST",
      body: JSON.stringify({ full_name: fullName, email, password })
    }),
  refresh: (refreshToken: string) =>
    request<AuthTokens>("/auth/refresh", null, {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken })
    }),
  logout: (token: string, refreshToken?: string | null) =>
    request<void>("/auth/logout", token, {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken })
    }),
  requestPasswordReset: (email: string) =>
    request<PasswordResetRequestResponse>("/auth/password-reset/request", null, {
      method: "POST",
      body: JSON.stringify({ email })
    }),
  confirmPasswordReset: (token: string, newPassword: string) =>
    request<void>("/auth/password-reset/confirm", null, {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword })
    }),
  me: (token: string) => request<User>("/auth/me", token),
  updateProfile: (token: string, fullName: string) =>
    request<User>("/auth/me", token, {
      method: "PATCH",
      body: JSON.stringify({ full_name: fullName })
    }),
  changePassword: (token: string, currentPassword: string, newPassword: string) =>
    request<void>("/auth/change-password", token, {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    }),
  workspaces: (token: string) => request<Workspace[]>("/workspaces", token),
  createWorkspace: (token: string, name: string) =>
    request<Workspace>("/workspaces", token, { method: "POST", body: JSON.stringify({ name }) }),
  updateWorkspace: (token: string, workspaceId: number, name: string) =>
    request<Workspace>(`/workspaces/${workspaceId}`, token, {
      method: "PATCH",
      body: JSON.stringify({ name })
    }),
  leaveWorkspace: (token: string, workspaceId: number) =>
    request<void>(`/workspaces/${workspaceId}/leave`, token, { method: "POST" }),
  members: (token: string, workspaceId: number) => request<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`, token),
  invitations: (token: string, workspaceId: number) => request<WorkspaceInvitationList>(`/workspaces/${workspaceId}/invitations`, token),
  addMember: (token: string, workspaceId: number, email: string, role: WorkspaceMember["role"]) =>
    request<WorkspaceInviteResponse>(`/workspaces/${workspaceId}/members`, token, {
      method: "POST",
      body: JSON.stringify({ email, role })
    }),
  updateMemberRole: (token: string, workspaceId: number, memberId: number, role: WorkspaceMember["role"]) =>
    request<WorkspaceMember>(`/workspaces/${workspaceId}/members/${memberId}`, token, {
      method: "PATCH",
      body: JSON.stringify({ role })
    }),
  removeMember: (token: string, workspaceId: number, memberId: number) =>
    request<void>(`/workspaces/${workspaceId}/members/${memberId}`, token, { method: "DELETE" }),
  resendInvitation: (token: string, workspaceId: number, invitationId: number) =>
    request<WorkspaceInvitation>(`/workspaces/${workspaceId}/invitations/${invitationId}/resend`, token, { method: "POST" }),
  revokeInvitation: (token: string, workspaceId: number, invitationId: number) =>
    request<WorkspaceInvitation>(`/workspaces/${workspaceId}/invitations/${invitationId}/revoke`, token, { method: "POST" }),
  acceptWorkspaceInvitation: (token: string, inviteToken: string) =>
    request<WorkspaceMember>("/workspaces/invitations/accept", token, {
      method: "POST",
      body: JSON.stringify({ token: inviteToken })
    }),
  savedSearches: (token: string, workspaceId?: number | null) =>
    request<SavedSearch[]>(workspaceId ? `/saved-searches?workspace_id=${workspaceId}` : "/saved-searches", token),
  createSavedSearch: (token: string, name: string, query: string, workspaceId: number | null, filters: DocumentFilters) =>
    request<SavedSearch>("/saved-searches", token, {
      method: "POST",
      body: JSON.stringify({ name, query, workspace_id: workspaceId, filters })
    }),
  updateSavedSearch: (token: string, id: number, name: string, query: string, workspaceId: number | null, filters: DocumentFilters) =>
    request<SavedSearch>(`/saved-searches/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify({ name, query, workspace_id: workspaceId, filters })
    }),
  deleteSavedSearch: (token: string, id: number) =>
    request<void>(`/saved-searches/${id}`, token, { method: "DELETE" }),
  collections: (token: string, workspaceId: number) =>
    request<DocumentCollection[]>(`/collections?workspace_id=${workspaceId}`, token),
  createCollection: (token: string, workspaceId: number, name: string, description?: string) =>
    request<DocumentCollection>("/collections", token, {
      method: "POST",
      body: JSON.stringify({ workspace_id: workspaceId, name, description: description || null })
    }),
  deleteCollection: (token: string, id: number) =>
    request<void>(`/collections/${id}`, token, { method: "DELETE" }),
  audit: (token: string, workspaceId: number) => request<AuditLog[]>(`/workspaces/${workspaceId}/audit`, token),
  adminStats: (token: string) => request<AdminStats>("/admin/stats", token),
  adminFailedDocuments: (token: string) => request<AdminDocument[]>("/admin/documents?failed_only=true", token),
  aiStatus: (token: string, healthCheck = false) => request<AiProviderStatus>(`/ai/status${healthCheck ? "?health_check=true" : ""}`, token),
  notifications: (token: string) => request<NotificationList>("/notifications", token),
  markNotificationRead: (token: string, id: number) => request<void>(`/notifications/${id}/read`, token, { method: "POST" }),
  askWorkspace: (token: string, workspaceId: number, question: string) =>
    request<AskResponse>(`/workspaces/${workspaceId}/ask`, token, {
      method: "POST",
      body: JSON.stringify({ question, limit: 8 })
    }),
  documents: (token: string, filters: DocumentFilters = {}) => {
    const params = new URLSearchParams();
    if (filters.workspaceId) params.set("workspace_id", String(filters.workspaceId));
    if (filters.status) params.set("status", filters.status);
    if (filters.documentType) params.set("document_type", filters.documentType);
    if (filters.riskSeverity) params.set("risk_severity", filters.riskSeverity);
    if (filters.tag) params.set("tag", filters.tag);
    if (filters.favorite !== undefined) params.set("favorite", String(filters.favorite));
    if (filters.reviewStatus) params.set("review_status", filters.reviewStatus);
    if (filters.collectionId) params.set("collection_id", String(filters.collectionId));
    const query = params.toString();
    return request<DocumentItem[]>(query ? `/documents?${query}` : "/documents", token);
  },
  document: (token: string, id: number) => request<DocumentDetail>(`/documents/${id}`, token),
  updateDocumentOrganization: (token: string, id: number, tags: string[], favorite: boolean, collectionId?: number | null) =>
    request<DocumentItem>(`/documents/${id}/organization`, token, {
      method: "PATCH",
      body: JSON.stringify({ tags, favorite, collection_id: collectionId || undefined })
    }),
  updateDocumentReview: (token: string, id: number, title: string, reviewStatus: DocumentReviewStatus, reviewNotes: string) =>
    request<DocumentItem>(`/documents/${id}/review`, token, {
      method: "PATCH",
      body: JSON.stringify({ title, review_status: reviewStatus, review_notes: reviewNotes })
    }),
  messages: (token: string, id: number) => request<ChatMessage[]>(`/documents/${id}/messages`, token),
  clearMessages: (token: string, id: number) =>
    request<void>(`/documents/${id}/messages`, token, { method: "DELETE" }),
  annotations: (token: string, id: number) => request<DocumentAnnotation[]>(`/documents/${id}/annotations`, token),
  createAnnotation: (token: string, id: number, pageNumber: number, note: string, quoteText?: string, color?: string) =>
    request<DocumentAnnotation>(`/documents/${id}/annotations`, token, {
      method: "POST",
      body: JSON.stringify({ page_number: pageNumber, note, quote_text: quoteText || null, color: color || null })
    }),
  deleteAnnotation: (token: string, documentId: number, annotationId: number) =>
    request<void>(`/documents/${documentId}/annotations/${annotationId}`, token, { method: "DELETE" }),
  documentFile: async (token: string, id: number) => {
    const response = await fetch(`${API_URL}/documents/${id}/file`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "Could not load PDF" }));
      throw new ApiError(response.status, payload.detail ?? "Could not load PDF");
    }
    return response.blob();
  },
  documentExport: async (token: string, id: number, format: "json" | "markdown") => {
    const response = await fetch(`${API_URL}/documents/${id}/export?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "Could not export document" }));
      throw new ApiError(response.status, payload.detail ?? "Could not export document");
    }
    return response.blob();
  },
  upload: (token: string, file: File, workspaceId?: number | null) => {
    const data = new FormData();
    data.append("file", file);
    const path = workspaceId ? `/documents?workspace_id=${workspaceId}` : "/documents";
    return request<DocumentItem>(path, token, { method: "POST", body: data });
  },
  reprocess: (token: string, id: number) => request<DocumentItem>(`/documents/${id}/reprocess`, token, { method: "POST" }),
  deleteDocument: (token: string, id: number) => request<void>(`/documents/${id}`, token, { method: "DELETE" }),
  bulkUpdateDocuments: (token: string, documentIds: number[], payload: { tags_add?: string[]; favorite?: boolean; review_status?: DocumentReviewStatus; collection_id?: number }) =>
    request<{ updated: number; documents: DocumentItem[] }>("/documents/bulk", token, {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds, ...payload })
    }),
  ask: (token: string, id: number, question: string) =>
    request<AskResponse>(`/documents/${id}/ask`, token, {
      method: "POST",
      body: JSON.stringify({ question })
    }),
  compareDocuments: (token: string, id: number, otherDocumentId: number) =>
    request<DocumentComparison>(`/documents/${id}/compare`, token, {
      method: "POST",
      body: JSON.stringify({ other_document_id: otherDocumentId })
    }),
  search: (token: string, query: string, filters: DocumentFilters = {}) =>
    request<{ results: SearchResult[] }>("/search", token, {
      method: "POST",
      body: JSON.stringify({
        query,
        limit: 8,
        workspace_id: filters.workspaceId,
        status: filters.status || undefined,
        document_type: filters.documentType || undefined,
        risk_severity: filters.riskSeverity || undefined,
        tag: filters.tag || undefined,
        favorite: filters.favorite,
        review_status: filters.reviewStatus || undefined,
        collection_id: filters.collectionId || undefined
      })
    })
};
