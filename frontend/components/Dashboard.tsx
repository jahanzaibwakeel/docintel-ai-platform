"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { Bot, Clock, Download, FileSearch, LogOut, Plus, RefreshCw, Search, Star, Tags, Trash2, Upload, UserPlus, ZoomIn, ZoomOut } from "lucide-react";
import { api } from "@/lib/api";
import type { AdminDocument, AdminStats, AiProviderStatus, AskResponse, AuditLog, ChatMessage, Citation, DocumentAnnotation, DocumentCollection, DocumentComparison, DocumentDetail, DocumentItem, DocumentReviewStatus, NotificationItem, SavedSearch, SearchResult, User, Workspace, WorkspaceInvitation, WorkspaceMember } from "@/lib/types";

export function Dashboard({ token, onLogout }: { token: string; onLogout: () => void }) {
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [savedSearchName, setSavedSearchName] = useState("");
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [collectionFilter, setCollectionFilter] = useState<number | null>(null);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [annotations, setAnnotations] = useState<DocumentAnnotation[]>([]);
  const [annotationPage, setAnnotationPage] = useState("1");
  const [annotationQuote, setAnnotationQuote] = useState("");
  const [annotationNote, setAnnotationNote] = useState("");
  const [bulkSelectedIds, setBulkSelectedIds] = useState<number[]>([]);
  const [bulkTag, setBulkTag] = useState("");
  const [bulkReviewStatus, setBulkReviewStatus] = useState<DocumentReviewStatus | "">("");
  const [bulkCollectionId, setBulkCollectionId] = useState<number | null>(null);
  const [workspaceAnswer, setWorkspaceAnswer] = useState<AskResponse | null>(null);
  const [pdfUrl, setPdfUrl] = useState("");
  const [pdfPage, setPdfPage] = useState(1);
  const [pdfZoom, setPdfZoom] = useState(100);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [profileName, setProfileName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [compareId, setCompareId] = useState<number | null>(null);
  const [comparison, setComparison] = useState<DocumentComparison | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [favoriteOnly, setFavoriteOnly] = useState(false);
  const [reviewFilter, setReviewFilter] = useState<DocumentReviewStatus | "">("");
  const [tagInput, setTagInput] = useState("");
  const [documentFavorite, setDocumentFavorite] = useState(false);
  const [reviewTitle, setReviewTitle] = useState("");
  const [reviewStatus, setReviewStatus] = useState<DocumentReviewStatus>("unreviewed");
  const [reviewNotes, setReviewNotes] = useState("");
  const [adminStats, setAdminStats] = useState<AdminStats | null>(null);
  const [failedJobs, setFailedJobs] = useState<AdminDocument[]>([]);
  const [aiStatus, setAiStatus] = useState<AiProviderStatus | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [acceptedInviteToken, setAcceptedInviteToken] = useState("");
  const [pendingInvitations, setPendingInvitations] = useState<WorkspaceInvitation[]>([]);
  const [workspaceMembers, setWorkspaceMembers] = useState<WorkspaceMember[]>([]);

  const readyCount = useMemo(() => documents.filter((document) => document.status === "ready").length, [documents]);
  const currentWorkspace = useMemo(() => workspaces.find((workspace) => workspace.id === workspaceId) ?? null, [workspaces, workspaceId]);
  const currentMember = useMemo(
    () => workspaceMembers.find((member) => member.user_email?.toLowerCase() === user?.email.toLowerCase()) ?? null,
    [workspaceMembers, user]
  );
  const canManageWorkspace = currentMember?.role === "owner" || currentMember?.role === "admin";
  const currentPdfUrl = useMemo(() => (pdfUrl ? `${pdfUrl}#page=${pdfPage}&zoom=${pdfZoom}` : ""), [pdfUrl, pdfPage, pdfZoom]);

  async function refresh() {
    const [profile, workspaceList] = await Promise.all([api.me(token), api.workspaces(token)]);
    const activeWorkspaceId = workspaceId ?? workspaceList[0]?.id ?? null;
    const filters = { workspaceId: activeWorkspaceId, status: statusFilter, documentType: typeFilter, riskSeverity: riskFilter, tag: tagFilter, favorite: favoriteOnly ? true : undefined, reviewStatus: reviewFilter, collectionId: collectionFilter };
    const [docs, audits, invitationList, members, saved, collectionList] = await Promise.all([
      api.documents(token, filters),
      activeWorkspaceId ? api.audit(token, activeWorkspaceId) : Promise.resolve([]),
      activeWorkspaceId ? api.invitations(token, activeWorkspaceId).catch(() => ({ invitations: [], pending_count: 0 })) : Promise.resolve({ invitations: [], pending_count: 0 }),
      activeWorkspaceId ? api.members(token, activeWorkspaceId).catch(() => []) : Promise.resolve([]),
      api.savedSearches(token, activeWorkspaceId).catch(() => []),
      activeWorkspaceId ? api.collections(token, activeWorkspaceId).catch(() => []) : Promise.resolve([])
    ]);
    setUser(profile);
    setProfileName((current) => current || profile.full_name);
    setWorkspaces(workspaceList);
    setWorkspaceId(activeWorkspaceId);
    setDocuments(docs);
    setAuditLogs(audits);
    setPendingInvitations(invitationList.invitations);
    setWorkspaceMembers(members);
    setSavedSearches(saved);
    setCollections(collectionList);
    api.notifications(token)
      .then((payload) => {
        setNotifications(payload.notifications);
        setUnreadCount(payload.unread_count);
      })
      .catch(() => {
        setNotifications([]);
        setUnreadCount(0);
      });
    api.adminStats(token)
      .then(async (stats) => {
        setAdminStats(stats);
        setFailedJobs(await api.adminFailedDocuments(token));
      })
      .catch(() => {
        setAdminStats(null);
        setFailedJobs([]);
      });
    api.aiStatus(token)
      .then(setAiStatus)
      .catch(() => setAiStatus(null));
    if (!selectedId && docs.length > 0) setSelectedId(docs[0].id);
  }

  useEffect(() => {
    refresh()
      .catch((error) => setMessage(error instanceof Error ? error.message : "Could not load dashboard"))
      .finally(() => setLoading(false));
  }, [workspaceId, statusFilter, typeFilter, riskFilter, tagFilter, favoriteOnly, reviewFilter, collectionFilter]);

  useEffect(() => {
    const inviteToken = new URLSearchParams(window.location.search).get("invite_token");
    if (!inviteToken || inviteToken === acceptedInviteToken) return;
    setAcceptedInviteToken(inviteToken);
    api.acceptWorkspaceInvitation(token, inviteToken)
      .then(async (membership) => {
        setWorkspaceId(membership.workspace_id);
        setMessage("Workspace invitation accepted.");
        await refresh();
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Could not accept invitation"));
  }, [token, acceptedInviteToken]);

  useEffect(() => {
    setWorkspaceName(currentWorkspace?.name ?? "");
  }, [currentWorkspace]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    api.document(token, selectedId)
      .then((document) => {
        setSelected(document);
        setTagInput((document.tags ?? []).join(", "));
        setDocumentFavorite(document.favorite);
        setSelectedCollectionId(document.collection_id);
        setPdfPage(1);
        setPdfZoom(100);
        setReviewTitle(document.title ?? "");
        setReviewStatus(document.review_status);
        setReviewNotes(document.review_notes ?? "");
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Could not load document"));
    api.messages(token, selectedId)
      .then(setMessages)
      .catch(() => setMessages([]));
    api.annotations(token, selectedId)
      .then(setAnnotations)
      .catch(() => setAnnotations([]));
  }, [selectedId, token]);

  useEffect(() => {
    if (!selectedId) {
      setPdfUrl("");
      return;
    }
    let objectUrl = "";
    let active = true;
    api.documentFile(token, selectedId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) {
          setPdfUrl(objectUrl);
        } else {
          URL.revokeObjectURL(objectUrl);
        }
      })
      .catch(() => setPdfUrl(""));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedId, token]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (documents.some((document) => document.status === "processing" || document.status === "uploaded")) {
        refresh().catch(() => undefined);
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [documents]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setMessage("Uploading document...");
    try {
      const document = await api.upload(token, file, workspaceId);
      setSelectedId(document.id);
      await refresh();
      setMessage("Upload complete. Processing has started.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      event.target.value = "";
    }
  }

  async function ask() {
    if (!selected || !question.trim()) return;
    setAnswer("Thinking...");
    try {
      const response = await api.ask(token, selected.id, question);
      setAnswer(response.answer);
      setCitations(response.citations);
      setQuestion("");
      const history = await api.messages(token, selected.id);
      setMessages(history);
    } catch (error) {
      setAnswer(error instanceof Error ? error.message : "Question failed");
      setCitations([]);
    }
  }

  async function runSearch() {
    if (!query.trim()) return;
    setResults([]);
    setMessage("Searching...");
    try {
      const response = await api.search(token, query, {
        workspaceId,
        status: statusFilter,
        documentType: typeFilter,
        riskSeverity: riskFilter,
        tag: tagFilter,
        favorite: favoriteOnly ? true : undefined,
        reviewStatus: reviewFilter
      });
      setResults(response.results);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed");
    }
  }

  function currentSearchFilters() {
    return {
      workspaceId,
      status: statusFilter,
      documentType: typeFilter,
      riskSeverity: riskFilter,
      tag: tagFilter,
      favorite: favoriteOnly ? true : undefined,
      reviewStatus: reviewFilter,
      collectionId: collectionFilter
    };
  }

  async function saveCurrentSearch() {
    if (!savedSearchName.trim() || !query.trim()) return;
    try {
      await api.createSavedSearch(token, savedSearchName.trim(), query.trim(), workspaceId, currentSearchFilters());
      setSavedSearchName("");
      setMessage("Search saved.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save search");
    }
  }

  function applySavedSearch(savedSearch: SavedSearch) {
    const filters = savedSearch.filters;
    setQuery(savedSearch.query);
    setStatusFilter(String(filters.status ?? ""));
    setTypeFilter(String(filters.documentType ?? ""));
    setRiskFilter(String(filters.riskSeverity ?? ""));
    setTagFilter(String(filters.tag ?? ""));
    setFavoriteOnly(filters.favorite === true);
    setReviewFilter((filters.reviewStatus as DocumentReviewStatus | "") ?? "");
    setCollectionFilter(typeof filters.collectionId === "number" ? filters.collectionId : null);
    if (typeof filters.workspaceId === "number") setWorkspaceId(filters.workspaceId);
    setMessage(`Loaded saved search: ${savedSearch.name}`);
  }

  async function deleteSavedSearch(savedSearch: SavedSearch) {
    try {
      await api.deleteSavedSearch(token, savedSearch.id);
      setSavedSearches((items) => items.filter((item) => item.id !== savedSearch.id));
      setMessage("Saved search deleted.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete saved search");
    }
  }

  async function askWorkspace() {
    if (!workspaceId || !query.trim()) return;
    setWorkspaceAnswer(null);
    setMessage("Answering across workspace...");
    try {
      const response = await api.askWorkspace(token, workspaceId, query);
      setWorkspaceAnswer(response);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Workspace question failed");
    }
  }

  async function reprocess() {
    if (!selected) return;
    await api.reprocess(token, selected.id);
    await refresh();
  }

  async function removeDocument() {
    if (!selected) return;
    await api.deleteDocument(token, selected.id);
    setSelected(null);
    setSelectedId(null);
    await refresh();
  }

  async function saveDocumentOrganization() {
    if (!selected) return;
    const tags = tagInput.split(",").map((tag) => tag.trim()).filter(Boolean);
    try {
      const updated = await api.updateDocumentOrganization(token, selected.id, tags, documentFavorite, selectedCollectionId);
      setSelected((current) => current ? { ...current, tags: updated.tags, favorite: updated.favorite, collection_id: updated.collection_id } : current);
      setDocuments((items) => items.map((document) => document.id === updated.id ? updated : document));
      setMessage("Document organization saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save document organization");
    }
  }

  async function createCollection() {
    if (!workspaceId || !newCollectionName.trim()) return;
    try {
      const collection = await api.createCollection(token, workspaceId, newCollectionName.trim());
      setCollections((items) => [...items, collection].sort((left, right) => left.name.localeCompare(right.name)));
      setNewCollectionName("");
      setMessage("Collection created.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create collection");
    }
  }

  async function deleteCollection(collection: DocumentCollection) {
    try {
      await api.deleteCollection(token, collection.id);
      setCollections((items) => items.filter((item) => item.id !== collection.id));
      if (collectionFilter === collection.id) setCollectionFilter(null);
      if (selectedCollectionId === collection.id) setSelectedCollectionId(null);
      setMessage("Collection deleted.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete collection");
    }
  }

  async function createAnnotation() {
    if (!selected || !annotationNote.trim()) return;
    try {
      const annotation = await api.createAnnotation(token, selected.id, Number(annotationPage) || 1, annotationNote.trim(), annotationQuote.trim() || undefined, "yellow");
      setAnnotations((items) => [...items, annotation]);
      setAnnotationQuote("");
      setAnnotationNote("");
      setMessage("Annotation added.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not add annotation");
    }
  }

  async function deleteAnnotation(annotation: DocumentAnnotation) {
    if (!selected) return;
    try {
      await api.deleteAnnotation(token, selected.id, annotation.id);
      setAnnotations((items) => items.filter((item) => item.id !== annotation.id));
      setMessage("Annotation deleted.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete annotation");
    }
  }

  function goToPdfPage(page: number) {
    const maxPage = selected?.page_count ?? page;
    setPdfPage(Math.max(1, Math.min(maxPage || 1, page)));
  }

  function useSelectedTextForAnnotation() {
    const text = window.getSelection()?.toString().trim();
    if (!text) {
      setMessage("Select text in the browser, then capture it as the annotation quote.");
      return;
    }
    setAnnotationQuote(text.slice(0, 500));
  }

  async function applyBulkAction() {
    if (bulkSelectedIds.length === 0) return;
    try {
      const response = await api.bulkUpdateDocuments(token, bulkSelectedIds, {
        tags_add: bulkTag.trim() ? bulkTag.split(",").map((tag) => tag.trim()).filter(Boolean) : undefined,
        review_status: bulkReviewStatus || undefined,
        collection_id: bulkCollectionId || undefined,
        favorite: true
      });
      setDocuments((items) => items.map((document) => response.documents.find((updated) => updated.id === document.id) ?? document));
      setBulkSelectedIds([]);
      setBulkTag("");
      setBulkReviewStatus("");
      setBulkCollectionId(null);
      setMessage(`Updated ${response.updated} documents.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Bulk update failed");
    }
  }

  async function saveDocumentReview() {
    if (!selected) return;
    try {
      const updated = await api.updateDocumentReview(token, selected.id, reviewTitle, reviewStatus, reviewNotes);
      setSelected((current) => current ? { ...current, title: updated.title, review_status: updated.review_status, review_notes: updated.review_notes } : current);
      setDocuments((items) => items.map((document) => document.id === updated.id ? updated : document));
      setMessage("Document review saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save document review");
    }
  }

  async function clearChat() {
    if (!selected) return;
    await api.clearMessages(token, selected.id);
    setMessages([]);
    setAnswer("");
    setCitations([]);
  }

  async function exportDocument(format: "json" | "markdown") {
    if (!selected) return;
    try {
      const blob = await api.documentExport(token, selected.id, format);
      const extension = format === "markdown" ? "md" : "json";
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = url;
      link.download = `${selected.filename.replace(/\.[^.]+$/, "")}.${extension}`;
      link.click();
      URL.revokeObjectURL(url);
      setMessage(`Exported ${extension.toUpperCase()} report.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Export failed");
    }
  }

  async function compareSelected() {
    if (!selected || !compareId) return;
    setComparison(null);
    setMessage("Comparing documents...");
    try {
      const response = await api.compareDocuments(token, selected.id, compareId);
      setComparison(response);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Comparison failed");
    }
  }

  async function createWorkspace() {
    if (!newWorkspaceName.trim()) return;
    const workspace = await api.createWorkspace(token, newWorkspaceName.trim());
    setNewWorkspaceName("");
    setWorkspaceId(workspace.id);
    setSelectedId(null);
    await refresh();
  }

  async function renameWorkspace() {
    if (!workspaceId || !workspaceName.trim()) return;
    try {
      const updated = await api.updateWorkspace(token, workspaceId, workspaceName.trim());
      setWorkspaces((items) => items.map((workspace) => workspace.id === updated.id ? updated : workspace));
      setWorkspaceName(updated.name);
      setMessage("Workspace renamed.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not rename workspace");
    }
  }

  async function leaveWorkspace() {
    if (!workspaceId) return;
    try {
      await api.leaveWorkspace(token, workspaceId);
      setWorkspaceId(null);
      setSelectedId(null);
      setSelected(null);
      setMessage("You left the workspace.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not leave workspace");
    }
  }

  async function saveProfile() {
    if (!profileName.trim()) return;
    try {
      const updated = await api.updateProfile(token, profileName.trim());
      setUser(updated);
      setProfileName(updated.full_name);
      setMessage("Profile updated.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update profile");
    }
  }

  async function savePassword() {
    if (!currentPassword || !newPassword) return;
    try {
      await api.changePassword(token, currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setMessage("Password changed. Sign in again on other devices.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not change password");
    }
  }

  async function inviteMember() {
    if (!workspaceId || !inviteEmail.trim()) return;
    try {
      const response = await api.addMember(token, workspaceId, inviteEmail.trim(), "member");
      setMessage(response.status === "invited" ? "Invitation email queued." : "Member added and invite email queued.");
      setInviteEmail("");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not invite member");
    }
  }

  async function resendInvitation(invitation: WorkspaceInvitation) {
    if (!workspaceId) return;
    try {
      await api.resendInvitation(token, workspaceId, invitation.id);
      setMessage("Invitation email resent.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not resend invitation");
    }
  }

  async function revokeInvitation(invitation: WorkspaceInvitation) {
    if (!workspaceId) return;
    try {
      await api.revokeInvitation(token, workspaceId, invitation.id);
      setMessage("Invitation revoked.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not revoke invitation");
    }
  }

  async function updateMemberRole(member: WorkspaceMember, role: WorkspaceMember["role"]) {
    if (!workspaceId) return;
    try {
      await api.updateMemberRole(token, workspaceId, member.id, role);
      setMessage("Member role updated.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update member");
    }
  }

  async function removeMember(member: WorkspaceMember) {
    if (!workspaceId) return;
    try {
      await api.removeMember(token, workspaceId, member.id);
      setMessage("Member removed.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not remove member");
    }
  }

  async function markNotificationRead(notification: NotificationItem) {
    await api.markNotificationRead(token, notification.id);
    if (notification.document_id) setSelectedId(notification.document_id);
    await refresh();
  }

  function formatBytes(bytes: number | null) {
    if (!bytes) return "-";
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function formatDate(value: string | null) {
    return value ? new Date(value).toLocaleString() : "-";
  }

  const diagnostics = selected?.extraction_diagnostics;
  const riskFlags = selected?.risk_flags ?? [];
  const structuredFields = selected?.structured_fields ?? {};

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <FileSearch size={26} />
          <span>DocIntel</span>
          <span className="muted">{documents.length} documents, {readyCount} ready</span>
        </div>
        <div className="row">
          <span className="muted">{user?.email}</span>
          <button className="secondary" onClick={onLogout} title="Sign out"><LogOut size={17} /></button>
        </div>
      </header>

      <main className="main grid">
        <aside className="panel stack">
          <div className="stack">
            <strong>Account</strong>
            <div className="row">
              <input value={profileName} onChange={(event) => setProfileName(event.target.value)} placeholder="Full name" />
              <button onClick={saveProfile} title="Save profile"><RefreshCw size={16} /></button>
            </div>
            <input value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} placeholder="Current password" type="password" />
            <div className="row">
              <input value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="New password" type="password" minLength={8} />
              <button onClick={savePassword} title="Change password"><RefreshCw size={16} /></button>
            </div>
          </div>
          <div className="stack">
            <strong>Workspace</strong>
            <select value={workspaceId ?? ""} onChange={(event) => {
              setWorkspaceId(Number(event.target.value));
              setSelectedId(null);
            }}>
              {workspaces.map((workspace) => (
                <option value={workspace.id} key={workspace.id}>{workspace.name}</option>
              ))}
            </select>
            <div className="row">
              <input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} placeholder="Workspace name" disabled={!canManageWorkspace} />
              <button onClick={renameWorkspace} disabled={!canManageWorkspace || workspaceName.trim() === currentWorkspace?.name} title="Rename workspace"><RefreshCw size={16} /></button>
              <button className="danger" onClick={leaveWorkspace} disabled={!workspaceId} title="Leave workspace"><LogOut size={16} /></button>
            </div>
            <div className="row">
              <input value={newWorkspaceName} onChange={(event) => setNewWorkspaceName(event.target.value)} placeholder="New workspace" />
              <button onClick={createWorkspace} title="Create workspace"><Plus size={16} /></button>
            </div>
            <div className="row">
              <input value={newCollectionName} onChange={(event) => setNewCollectionName(event.target.value)} placeholder="New collection" />
              <button onClick={createCollection} disabled={!workspaceId || !newCollectionName.trim()} title="Create collection"><Plus size={16} /></button>
            </div>
            {collections.length > 0 && (
              <div className="stack">
                <strong>Collections</strong>
                {collections.slice(0, 6).map((collection) => (
                  <div className="row" key={collection.id}>
                    <button className="secondary" onClick={() => setCollectionFilter(collection.id)}>{collection.name}</button>
                    <button className="danger" onClick={() => deleteCollection(collection)} title="Delete collection"><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>
            )}
            <div className="row">
              <input value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="Invite email" />
              <button onClick={inviteMember} title="Invite member"><UserPlus size={16} /></button>
            </div>
            {pendingInvitations.length > 0 && (
              <div className="stack">
                <strong>Pending Invites</strong>
                {pendingInvitations.map((invitation) => (
                  <div className="row" key={invitation.id}>
                    <span className="muted">{invitation.email} - {invitation.role}</span>
                    <div className="row">
                      <button className="secondary" onClick={() => resendInvitation(invitation)} title="Resend invite"><RefreshCw size={14} /></button>
                      <button className="danger" onClick={() => revokeInvitation(invitation)} title="Revoke invite"><Trash2 size={14} /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {workspaceMembers.length > 0 && (
            <div className="stack">
              <strong>Members</strong>
              {workspaceMembers.map((member) => (
                <div className="row" key={member.id}>
                  <span className="muted">{member.user_email ?? `User ${member.user_id}`}</span>
                  <div className="row">
                    <select value={member.role} onChange={(event) => updateMemberRole(member, event.target.value as WorkspaceMember["role"])}>
                      <option value="owner">Owner</option>
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>
                    <button className="danger" onClick={() => removeMember(member)} title="Remove member"><Trash2 size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="stack">
            <div className="row">
              <strong>AI operations</strong>
              <button className="secondary" onClick={() => api.aiStatus(token, true).then(setAiStatus).catch((error) => setMessage(error instanceof Error ? error.message : "AI health check failed"))} title="Check AI provider">
                <Bot size={16} />
              </button>
            </div>
            {aiStatus ? (
              <div className="opsCard">
                <div className="row">
                  <strong>{aiStatus.provider}</strong>
                  <span className={`status ${aiStatus.configured ? "ready" : "failed"}`}>{aiStatus.configured ? "configured" : "setup"}</span>
                </div>
                <span className="muted">{aiStatus.model} | {aiStatus.embedding_model}</span>
                <span className="muted">{aiStatus.embedding_dimensions} dims | {aiStatus.max_context_chars.toLocaleString()} chars | {aiStatus.request_timeout_seconds}s</span>
                <span className="muted">PII {aiStatus.pii_redaction_enabled ? "redacted" : "not redacted"} | external PII {aiStatus.external_ai_with_pii_allowed ? "allowed" : "blocked"}</span>
                <span className="muted">{aiStatus.healthy === null ? aiStatus.detail : `${aiStatus.healthy ? "Healthy" : "Unhealthy"} - ${aiStatus.detail}`}</span>
              </div>
            ) : (
              <span className="muted">AI status unavailable.</span>
            )}
          </div>
          <div className="row">
            <strong>Documents</strong>
            <label>
              <input type="file" accept="application/pdf" onChange={upload} hidden />
              <span className="iconButton" title="Upload PDF"><Upload size={17} /></span>
            </label>
          </div>
          <div className="stack">
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">Any status</option>
              <option value="uploaded">Uploaded</option>
              <option value="processing">Processing</option>
              <option value="ready">Ready</option>
              <option value="failed">Failed</option>
            </select>
            <input value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} placeholder="Document type" />
            <input value={tagFilter} onChange={(event) => setTagFilter(event.target.value)} placeholder="Tag filter" />
            <select value={collectionFilter ?? ""} onChange={(event) => setCollectionFilter(Number(event.target.value) || null)}>
              <option value="">Any collection</option>
              {collections.map((collection) => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
            </select>
            <select value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}>
              <option value="">Any risk</option>
              <option value="low">Low risk</option>
              <option value="medium">Medium risk</option>
              <option value="high">High risk</option>
            </select>
            <select value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value as DocumentReviewStatus | "")}>
              <option value="">Any review</option>
              <option value="unreviewed">Unreviewed</option>
              <option value="in_review">In review</option>
              <option value="approved">Approved</option>
              <option value="needs_changes">Needs changes</option>
            </select>
            <label className="row">
              <span className="muted">Favorites only</span>
              <input type="checkbox" checked={favoriteOnly} onChange={(event) => setFavoriteOnly(event.target.checked)} />
            </label>
          </div>
          {documents.length > 0 && (
            <div className="stack">
              <strong>Bulk actions</strong>
              <input value={bulkTag} onChange={(event) => setBulkTag(event.target.value)} placeholder="Add tags to selected" />
              <select value={bulkReviewStatus} onChange={(event) => setBulkReviewStatus(event.target.value as DocumentReviewStatus | "")}>
                <option value="">Keep review status</option>
                <option value="unreviewed">Unreviewed</option>
                <option value="in_review">In review</option>
                <option value="approved">Approved</option>
                <option value="needs_changes">Needs changes</option>
              </select>
              <select value={bulkCollectionId ?? ""} onChange={(event) => setBulkCollectionId(Number(event.target.value) || null)}>
                <option value="">Keep collection</option>
                {collections.map((collection) => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
              </select>
              <button disabled={bulkSelectedIds.length === 0} onClick={applyBulkAction}>Apply to {bulkSelectedIds.length}</button>
            </div>
          )}
          {loading && <div className="message">Loading dashboard...</div>}
          {message && <div className={`message ${message.toLowerCase().includes("fail") ? "error" : ""}`}>{message}</div>}
          <div className="stack">
            {documents.map((document) => (
              <div
                key={document.id}
                className="card secondary"
                role="button"
                tabIndex={0}
                onClick={() => setSelectedId(document.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") setSelectedId(document.id);
                }}
                style={{ textAlign: "left", borderColor: selectedId === document.id ? "var(--accent)" : "var(--line)" }}
              >
                <div className="row">
                  <input
                    type="checkbox"
                    checked={bulkSelectedIds.includes(document.id)}
                    onClick={(event) => event.stopPropagation()}
                    onChange={(event) => {
                      setBulkSelectedIds((ids) => event.target.checked ? [...ids, document.id] : ids.filter((id) => id !== document.id));
                    }}
                  />
                  <strong>{document.title ?? document.filename}</strong>
                  <span className={`status ${document.status}`}>{document.status}</span>
                </div>
                <div className="muted">{document.filename} | {document.page_count ?? "-"} pages | {document.review_status.replace("_", " ")}{document.collection_id ? ` | ${collections.find((collection) => collection.id === document.collection_id)?.name ?? "collection"}` : ""}</div>
                {(document.favorite || document.tags.length > 0) && (
                  <div className="fieldChips">
                    {document.favorite && <span><Star size={12} /> Favorite</span>}
                    {document.tags.slice(0, 3).map((tag) => <span key={tag}><Tags size={12} /> {tag}</span>)}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="stack">
            <strong>Audit log</strong>
            <div className="auditList">
              {auditLogs.slice(0, 10).map((entry) => (
                <div className="auditItem" key={entry.id}>
                  <strong>{entry.action}</strong>
                  <span className="muted">{formatDate(entry.created_at)}</span>
                </div>
              ))}
              {auditLogs.length === 0 && <span className="muted">No activity yet.</span>}
            </div>
          </div>
          <div className="stack">
            <strong>Notifications {unreadCount > 0 ? `(${unreadCount})` : ""}</strong>
            <div className="auditList">
              {notifications.slice(0, 8).map((notification) => (
                <button className="auditItem secondary" key={notification.id} onClick={() => markNotificationRead(notification)}>
                  <strong>{notification.title}</strong>
                  <span className="muted">{notification.message}</span>
                </button>
              ))}
              {notifications.length === 0 && <span className="muted">No notifications.</span>}
            </div>
          </div>
          {adminStats && (
            <div className="stack">
              <strong>Admin ops</strong>
              <div className="metaGrid">
                <div><span className="muted">Users</span><strong>{adminStats.users}</strong></div>
                <div><span className="muted">Workspaces</span><strong>{adminStats.workspaces}</strong></div>
                <div><span className="muted">Documents</span><strong>{adminStats.documents}</strong></div>
                <div><span className="muted">Failed</span><strong>{adminStats.failed_documents}</strong></div>
              </div>
              <div className="auditList">
                {failedJobs.slice(0, 6).map((job) => (
                  <button className="auditItem secondary" key={job.id} onClick={() => setSelectedId(job.id)}>
                    <strong>{job.filename}</strong>
                    <span className="muted">{job.error_message ?? "Failed processing"}</span>
                  </button>
                ))}
                {failedJobs.length === 0 && <span className="muted">No failed jobs.</span>}
              </div>
            </div>
          )}
        </aside>

        <section className="stack">
          <div className="panel stack">
            <div className="row">
              <div>
                <h2>{selected?.title ?? selected?.filename ?? "Select a document"}</h2>
                <div className="muted">{selected ? `Status: ${selected.status}` : "Upload a PDF to begin"}</div>
              </div>
              {selected && (
                <div className="row">
                  <button className="secondary" onClick={() => exportDocument("json")} title="Export JSON"><Download size={17} /></button>
                  <button className="secondary" onClick={() => exportDocument("markdown")} title="Export Markdown"><Download size={17} /></button>
                  <button className="secondary" onClick={reprocess} title="Reprocess"><RefreshCw size={17} /></button>
                  <button className="secondary" onClick={removeDocument} title="Delete document"><Trash2 size={17} /></button>
                </div>
              )}
            </div>
            {selected?.error_message && <div className="message error">{selected.error_message}</div>}
            {selected && (
              <div className="metaGrid">
                <div><span className="muted">Pages</span><strong>{selected.page_count ?? "-"}</strong></div>
                <div><span className="muted">Size</span><strong>{formatBytes(selected.file_size_bytes)}</strong></div>
                <div><span className="muted">Uploaded</span><strong>{formatDate(selected.created_at)}</strong></div>
                <div><span className="muted">Processed</span><strong>{formatDate(selected.processing_completed_at)}</strong></div>
                <div><span className="muted">Retention</span><strong>{formatDate(selected.retention_expires_at)}</strong></div>
              </div>
            )}
            {selected && (
              <div className="stack">
                <h3>Organization</h3>
                <div className="row">
                  <input value={tagInput} onChange={(event) => setTagInput(event.target.value)} placeholder="Tags separated by commas" />
                  <label className="row">
                    <span className="muted">Favorite</span>
                    <input type="checkbox" checked={documentFavorite} onChange={(event) => setDocumentFavorite(event.target.checked)} />
                  </label>
                  <select value={selectedCollectionId ?? ""} onChange={(event) => setSelectedCollectionId(Number(event.target.value) || null)}>
                    <option value="">No collection</option>
                    {collections.map((collection) => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
                  </select>
                  <button onClick={saveDocumentOrganization} title="Save document organization"><RefreshCw size={16} /></button>
                </div>
              </div>
            )}
            {selected && (
              <div className="stack">
                <h3>Review</h3>
                <div className="row">
                  <input value={reviewTitle} onChange={(event) => setReviewTitle(event.target.value)} placeholder="Document title" />
                  <select value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value as DocumentReviewStatus)}>
                    <option value="unreviewed">Unreviewed</option>
                    <option value="in_review">In review</option>
                    <option value="approved">Approved</option>
                    <option value="needs_changes">Needs changes</option>
                  </select>
                  <button onClick={saveDocumentReview} title="Save document review"><RefreshCw size={16} /></button>
                </div>
                <textarea value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} placeholder="Reviewer notes" />
              </div>
            )}
            {selected && (
              <div className="stack">
                <h3>Annotations</h3>
                <div className="row">
                  <input value={annotationPage} onChange={(event) => setAnnotationPage(event.target.value)} placeholder="Page" />
                  <input value={annotationQuote} onChange={(event) => setAnnotationQuote(event.target.value)} placeholder="Quoted text" />
                </div>
                <div className="row">
                  <input value={annotationNote} onChange={(event) => setAnnotationNote(event.target.value)} placeholder="Annotation note" />
                  <button className="secondary" onClick={useSelectedTextForAnnotation} title="Capture selected text">Quote</button>
                  <button onClick={createAnnotation} disabled={!annotationNote.trim()} title="Add annotation"><Plus size={16} /></button>
                </div>
                <div className="auditList">
                  {annotations.map((annotation) => (
                    <div className="auditItem" key={annotation.id}>
                      <button className="secondary" onClick={() => {
                        goToPdfPage(annotation.page_number);
                        setAnnotationPage(String(annotation.page_number));
                      }}>Page {annotation.page_number}</button>
                      <span className="muted">{annotation.quote_text ? `${annotation.quote_text} - ` : ""}{annotation.note}</span>
                      <button className="danger" onClick={() => deleteAnnotation(annotation)} title="Delete annotation"><Trash2 size={14} /></button>
                    </div>
                  ))}
                  {annotations.length === 0 && <span className="muted">No annotations yet.</span>}
                </div>
              </div>
            )}
            {pdfUrl && (
              <div className="viewerShell">
                <div className="viewerToolbar">
                  <div className="row">
                    <button className="secondary" disabled={pdfPage <= 1} onClick={() => goToPdfPage(pdfPage - 1)} title="Previous page">Prev</button>
                    <input
                      aria-label="PDF page"
                      min={1}
                      max={selected?.page_count ?? undefined}
                      type="number"
                      value={pdfPage}
                      onChange={(event) => goToPdfPage(Number(event.target.value) || 1)}
                    />
                    <span className="muted">of {selected?.page_count ?? "-"}</span>
                    <button className="secondary" disabled={selected?.page_count ? pdfPage >= selected.page_count : false} onClick={() => goToPdfPage(pdfPage + 1)} title="Next page">Next</button>
                  </div>
                  <div className="row">
                    <button className="secondary" onClick={() => setPdfZoom((value) => Math.max(50, value - 25))} title="Zoom out"><ZoomOut size={16} /></button>
                    <span className="muted">{pdfZoom}%</span>
                    <button className="secondary" onClick={() => setPdfZoom((value) => Math.min(200, value + 25))} title="Zoom in"><ZoomIn size={16} /></button>
                  </div>
                </div>
                <div className="annotationStrip">
                  {annotations.map((annotation) => (
                    <button
                      className={annotation.page_number === pdfPage ? "activeAnnotation" : "secondary"}
                      key={`viewer-${annotation.id}`}
                      onClick={() => goToPdfPage(annotation.page_number)}
                    >
                      Page {annotation.page_number}
                    </button>
                  ))}
                </div>
                <div className="pdfFrame">
                  <iframe src={currentPdfUrl} title={selected?.filename ?? "PDF preview"} />
                </div>
              </div>
            )}
            {diagnostics && (
              <div>
                <h3>Extraction diagnostics</h3>
                <div className="metaGrid">
                  <div><span className="muted">OCR</span><strong>{diagnostics.ocr_enabled ? "Enabled" : "Disabled"}</strong></div>
                  <div><span className="muted">Native pages</span><strong>{diagnostics.native_page_count ?? 0}</strong></div>
                  <div><span className="muted">OCR pages</span><strong>{diagnostics.ocr_page_count ?? 0}</strong></div>
                  <div><span className="muted">OCR failures</span><strong>{diagnostics.failed_ocr_page_count ?? 0}</strong></div>
                </div>
                <div className="diagnosticRows">
                  {diagnostics.pages?.map((page) => (
                    <div className="row" key={page.page_number}>
                      <span>Page {page.page_number}</span>
                      <span className="muted">{page.method} | {page.character_count} chars{page.error ? ` | ${page.error}` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div>
              <h3>Summary</h3>
              <p>{selected?.summary ?? "Summary will appear when processing is complete."}</p>
            </div>
            {selected && (
              <div>
                <h3>Intelligence</h3>
                <div className="metaGrid">
                  <div>
                    <span className="muted">Document type</span>
                    <strong>{selected.document_type ?? "Pending"}</strong>
                  </div>
                  <div>
                    <span className="muted">Type confidence</span>
                    <strong>{selected.document_type_confidence ? `${selected.document_type_confidence}%` : "-"}</strong>
                  </div>
                  <div>
                    <span className="muted">Risk flags</span>
                    <strong>{riskFlags.length}</strong>
                  </div>
                  <div>
                    <span className="muted">Structured groups</span>
                    <strong>{Object.keys(structuredFields).length}</strong>
                  </div>
                </div>
                {riskFlags.length > 0 && (
                  <div className="results">
                    {riskFlags.map((risk, index) => (
                      <div className={`riskItem ${risk.severity}`} key={`${risk.label}-${index}`}>
                        <div className="row">
                          <strong>{risk.label}</strong>
                          <span className="muted">{risk.severity} | {risk.confidence}%</span>
                        </div>
                        <p>{risk.evidence}</p>
                      </div>
                    ))}
                  </div>
                )}
                {Object.keys(structuredFields).length > 0 && (
                  <div className="results">
                    {Object.entries(structuredFields).map(([key, values]) => (
                      <div className="card" key={key}>
                        <strong>{key.replaceAll("_", " ")}</strong>
                        <div className="fieldChips">
                          {values.slice(0, 8).map((field, index) => (
                            <span key={`${field.value}-${index}`}>{field.value} ({field.confidence}%)</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div>
              <h3>Key fields</h3>
              <div className="results">
                {selected?.key_fields
                  ? Object.entries(selected.key_fields).map(([key, values]) => (
                      <div className="card" key={key}>
                        <strong>{key.replaceAll("_", " ")}</strong>
                        <div className="muted">{Array.isArray(values) ? values.join(", ") || "None found" : String(values)}</div>
                      </div>
                    ))
                  : <div className="muted">Fields will appear after extraction.</div>}
              </div>
            </div>
            {selected && documents.filter((document) => document.id !== selected.id).length > 0 && (
              <div>
                <h3>Compare documents</h3>
                <div className="row">
                  <select value={compareId ?? ""} onChange={(event) => setCompareId(Number(event.target.value) || null)}>
                    <option value="">Choose a document</option>
                    {documents.filter((document) => document.id !== selected.id).map((document) => (
                      <option key={document.id} value={document.id}>{document.filename}</option>
                    ))}
                  </select>
                  <button disabled={!compareId} onClick={compareSelected}>Compare</button>
                </div>
                {comparison && (
                  <div className="results">
                    <div className="card">
                      <div className="row">
                        <strong>{comparison.left.filename} vs {comparison.right.filename}</strong>
                        <span className="muted">{Math.round(comparison.similarity * 100)}% similar</span>
                      </div>
                      <p>{comparison.summary.changed ? "Summaries differ." : "Summaries match."}</p>
                    </div>
                    {Object.entries(comparison.field_changes).map(([key, change]) => (
                      <div className="card" key={key}>
                        <strong>{key.replaceAll("_", " ")}</strong>
                        <p>Only in {comparison.left.filename}: {change.only_in_left.join(", ") || "None"}</p>
                        <p>Only in {comparison.right.filename}: {change.only_in_right.join(", ") || "None"}</p>
                      </div>
                    ))}
                    <div className="card">
                      <strong>Risk changes</strong>
                      <p>Only in {comparison.left.filename}: {comparison.risk_changes.only_in_left.join(", ") || "None"}</p>
                      <p>Only in {comparison.right.filename}: {comparison.risk_changes.only_in_right.join(", ") || "None"}</p>
                      <p>Shared: {comparison.risk_changes.shared.join(", ") || "None"}</p>
                    </div>
                    <div className="card">
                      <strong>Term changes</strong>
                      <p>Only in {comparison.left.filename}: {comparison.term_changes.only_in_left.slice(0, 12).join(", ") || "None"}</p>
                      <p>Only in {comparison.right.filename}: {comparison.term_changes.only_in_right.slice(0, 12).join(", ") || "None"}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="panel stack">
            <div className="row">
              <h3>Ask this document</h3>
              <button className="secondary" disabled={!selected || messages.length === 0} onClick={clearChat} title="Clear chat">
                <Trash2 size={16} />
              </button>
            </div>
            {messages.length > 0 && (
              <div className="chatHistory">
                {messages.map((chatMessage) => (
                  <div className={`chatBubble ${chatMessage.role}`} key={chatMessage.id}>
                    <strong>{chatMessage.role === "user" ? "You" : "Assistant"}</strong>
                    <p>{chatMessage.content}</p>
                    {chatMessage.citations && chatMessage.citations.length > 0 && (
                      <div className="muted">
                        {chatMessage.citations.map((citation) => `Page ${citation.page_number ?? "-"} (${Math.round((citation.score ?? 0) * 100)}%)`).join(" | ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about dates, obligations, risks, parties, or clauses" />
            <button disabled={!selected || selected.status !== "ready"} onClick={ask}>Ask</button>
            {answer && <div className="message">{answer}</div>}
            {citations.length > 0 && (
              <div className="results">
                {citations.map((citation) => (
                  <div className="card" key={citation.chunk_index}>
                    <div className="row">
                      <strong>Source</strong>
                      <span className="muted">Page {citation.page_number ?? "-"} | Chunk {citation.chunk_index}</span>
                    </div>
                    <p>{citation.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel stack">
            <h3>Semantic search</h3>
            <div className="row">
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search across uploaded documents" />
              <button onClick={runSearch} title="Search"><Search size={17} /></button>
            </div>
            <div className="row">
              <input value={savedSearchName} onChange={(event) => setSavedSearchName(event.target.value)} placeholder="Saved search name" />
              <button onClick={saveCurrentSearch} disabled={!savedSearchName.trim() || !query.trim()} title="Save search"><Plus size={16} /></button>
            </div>
            {savedSearches.length > 0 && (
              <div className="auditList">
                {savedSearches.slice(0, 6).map((savedSearch) => (
                  <div className="auditItem" key={savedSearch.id}>
                    <button className="secondary" onClick={() => applySavedSearch(savedSearch)}>
                      <strong>{savedSearch.name}</strong>
                    </button>
                    <button className="danger" onClick={() => deleteSavedSearch(savedSearch)} title="Delete saved search"><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>
            )}
            <button disabled={!workspaceId || !query.trim()} onClick={askWorkspace}>Ask workspace</button>
            {workspaceAnswer && (
              <div className="message">
                <strong>Workspace answer</strong>
                <p>{workspaceAnswer.answer}</p>
                <div className="muted">
                  Confidence {Math.round(workspaceAnswer.confidence * 100)}% | {workspaceAnswer.grounded ? "grounded" : "needs review"} | {workspaceAnswer.prompt_version}
                </div>
                <div className="results">
                  {workspaceAnswer.citations.map((citation) => (
                    <div className="card" key={`${citation.document_id}-${citation.chunk_index}`}>
                      <div className="row">
                        <strong>{citation.filename ?? "Source"}</strong>
                        <span className="muted">Page {citation.page_number ?? "-"} | {citation.validated ? "validated" : "unverified"}</span>
                      </div>
                      <p>{citation.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="results">
              {results.map((result) => (
                <div className="card" key={`${result.document_id}-${result.chunk_index}`}>
                  <div className="row">
                    <strong>{result.filename}</strong>
                    <span className="muted">Page {result.page_number ?? "-"} | {Math.round(result.score * 100)}% match</span>
                  </div>
                  <div className="scoreBar">
                    <span style={{ width: `${Math.round(result.vector_score * 100)}%` }} />
                  </div>
                  <div className="muted">Vector {Math.round(result.vector_score * 100)}% | Keyword {Math.round(result.keyword_score * 100)}%</div>
                  <p>{result.text}</p>
                </div>
              ))}
            </div>
          </div>

          {selected?.extracted_text && (
            <div className="panel stack">
              <div className="row">
                <h3>Extracted text</h3>
                <span className="muted"><Clock size={14} /> {formatDate(selected.updated_at)}</span>
              </div>
              <pre className="textPreview">{selected.extracted_text}</pre>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
