import * as DocumentPicker from "expo-document-picker";
import { StatusBar } from "expo-status-bar";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View
} from "react-native";

import { api } from "./src/api";
import { tokenStorage } from "./src/storage";
import type { AskResponse, ChatMessage, DocumentAnnotation, DocumentCollection, DocumentComparison, DocumentDetail, DocumentItem, DocumentReviewStatus, NotificationItem, SavedSearch, SearchResult, User, Workspace } from "./src/types";

type Tab = "documents" | "search" | "detail" | "account";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [collections, setCollections] = useState<DocumentCollection[]>([]);
  const [workspaceId, setWorkspaceId] = useState<number | null>(null);
  const [collectionFilter, setCollectionFilter] = useState<number | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [annotations, setAnnotations] = useState<DocumentAnnotation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tab, setTab] = useState<Tab>("documents");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [savedSearchName, setSavedSearchName] = useState("");
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [workspaceAnswer, setWorkspaceAnswer] = useState<AskResponse | null>(null);
  const [comparison, setComparison] = useState<DocumentComparison | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [question, setQuestion] = useState("");
  const [profileName, setProfileName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [favoriteOnly, setFavoriteOnly] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const [documentFavorite, setDocumentFavorite] = useState(false);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [annotationNote, setAnnotationNote] = useState("");
  const [reviewTitle, setReviewTitle] = useState("");
  const [reviewStatus, setReviewStatus] = useState<DocumentReviewStatus>("unreviewed");
  const [reviewNotes, setReviewNotes] = useState("");

  const readyCount = useMemo(() => documents.filter((document) => document.status === "ready").length, [documents]);
  const currentWorkspace = useMemo(() => workspaces.find((workspace) => workspace.id === workspaceId) ?? null, [workspaces, workspaceId]);
  const statusStyles = {
    ready: styles.status_ready,
    failed: styles.status_failed,
    processing: styles.status_processing,
    uploaded: styles.status_uploaded
  };

  useEffect(() => {
    tokenStorage.get()
      .then((storedToken) => {
        if (storedToken) {
          setToken(storedToken);
          return;
        }
        tokenStorage.getRefresh()
          .then(async (refreshToken) => {
            if (!refreshToken) return;
            const tokens = await api.refresh(refreshToken);
            await tokenStorage.setPair(tokens.access_token, tokens.refresh_token);
            setToken(tokens.access_token);
          })
          .catch(() => tokenStorage.clear());
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!token) return;
    refresh(token).catch((error) => setMessage(error instanceof Error ? error.message : "Could not load app"));
  }, [token, workspaceId, tagFilter, favoriteOnly, collectionFilter]);

  useEffect(() => {
    setWorkspaceName(currentWorkspace?.name ?? "");
  }, [currentWorkspace]);

  async function refresh(activeToken = token) {
    if (!activeToken) return;
    setLoading(true);
    try {
      const [profile, workspaceList] = await Promise.all([api.me(activeToken), api.workspaces(activeToken)]);
      const activeWorkspaceId = workspaceId ?? workspaceList[0]?.id ?? null;
      const [docs, notificationList, saved, collectionList] = await Promise.all([
        api.documents(activeToken, { workspaceId: activeWorkspaceId, tag: tagFilter, favorite: favoriteOnly ? true : undefined, collectionId: collectionFilter }),
        api.notifications(activeToken),
        api.savedSearches(activeToken, activeWorkspaceId).catch(() => []),
        activeWorkspaceId ? api.collections(activeToken, activeWorkspaceId).catch(() => []) : Promise.resolve([])
      ]);
      setUser(profile);
      setProfileName((current) => current || profile.full_name);
      setWorkspaces(workspaceList);
      setWorkspaceId(activeWorkspaceId);
      setDocuments(docs);
      setCollections(collectionList);
      setNotifications(notificationList.notifications);
      setUnreadCount(notificationList.unread_count);
      setSavedSearches(saved);
    } finally {
      setLoading(false);
    }
  }

  async function openDocument(document: DocumentItem) {
    if (!token) return;
    setLoading(true);
    try {
      const [detail, history, annotationList] = await Promise.all([api.document(token, document.id), api.messages(token, document.id), api.annotations(token, document.id).catch(() => [])]);
      setSelected(detail);
      setTagInput((detail.tags ?? []).join(", "));
      setDocumentFavorite(detail.favorite);
      setSelectedCollectionId(detail.collection_id);
      setReviewTitle(detail.title ?? "");
      setReviewStatus(detail.review_status);
      setReviewNotes(detail.review_notes ?? "");
      setMessages(history);
      setAnnotations(annotationList);
      setTab("detail");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not open document");
    } finally {
      setLoading(false);
    }
  }

  async function runSearch() {
    if (!token || !searchQuery.trim()) return;
    setLoading(true);
    try {
      const response = await api.search(token, searchQuery.trim(), { workspaceId, tag: tagFilter, favorite: favoriteOnly ? true : undefined, collectionId: collectionFilter });
      setSearchResults(response.results);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  function currentSearchFilters() {
    return { workspaceId, tag: tagFilter, favorite: favoriteOnly ? true : undefined, collectionId: collectionFilter };
  }

  async function saveCurrentSearch() {
    if (!token || !savedSearchName.trim() || !searchQuery.trim()) return;
    setLoading(true);
    try {
      await api.createSavedSearch(token, savedSearchName.trim(), searchQuery.trim(), workspaceId, currentSearchFilters());
      setSavedSearchName("");
      setMessage("Search saved.");
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save search");
    } finally {
      setLoading(false);
    }
  }

  function applySavedSearch(savedSearch: SavedSearch) {
    const filters = savedSearch.filters;
    setSearchQuery(savedSearch.query);
    setTagFilter(String(filters.tag ?? ""));
    setFavoriteOnly(filters.favorite === true);
    setCollectionFilter(typeof filters.collectionId === "number" ? filters.collectionId : null);
    if (typeof filters.workspaceId === "number") setWorkspaceId(filters.workspaceId);
    setMessage(`Loaded saved search: ${savedSearch.name}`);
  }

  async function deleteSavedSearch(savedSearch: SavedSearch) {
    if (!token) return;
    setLoading(true);
    try {
      await api.deleteSavedSearch(token, savedSearch.id);
      setSavedSearches((items) => items.filter((item) => item.id !== savedSearch.id));
      setMessage("Saved search deleted.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete saved search");
    } finally {
      setLoading(false);
    }
  }

  async function askWorkspace() {
    if (!token || !workspaceId || !searchQuery.trim()) return;
    setLoading(true);
    setWorkspaceAnswer(null);
    try {
      const response = await api.askWorkspace(token, workspaceId, searchQuery.trim());
      setWorkspaceAnswer(response);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Workspace question failed");
    } finally {
      setLoading(false);
    }
  }

  async function askQuestion() {
    if (!token || !selected || !question.trim()) return;
    setLoading(true);
    try {
      await api.ask(token, selected.id, question.trim());
      const history = await api.messages(token, selected.id);
      setMessages(history);
      setQuestion("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Question failed");
    } finally {
      setLoading(false);
    }
  }

  async function uploadPdf() {
    if (!token) return;
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "application/pdf",
        copyToCacheDirectory: true,
        multiple: false
      });
      if (result.canceled || !result.assets[0]) return;
      setLoading(true);
      const asset = result.assets[0];
      const document = await api.upload(
        token,
        { uri: asset.uri, name: asset.name ?? "upload.pdf", mimeType: asset.mimeType ?? "application/pdf" },
        workspaceId
      );
      setMessage("Upload complete. Processing has started.");
      await refresh(token);
      await openDocument(document);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function deleteSelectedDocument() {
    if (!token || !selected) return;
    setLoading(true);
    try {
      await api.deleteDocument(token, selected.id);
      setSelected(null);
      setMessages([]);
      setTab("documents");
      setMessage("Document deleted.");
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Delete failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveDocumentOrganization() {
    if (!token || !selected) return;
    setLoading(true);
    try {
      const tags = tagInput.split(",").map((tag) => tag.trim()).filter(Boolean);
      const updated = await api.updateDocumentOrganization(token, selected.id, tags, documentFavorite, selectedCollectionId);
      setSelected((current) => current ? { ...current, tags: updated.tags, favorite: updated.favorite, collection_id: updated.collection_id } : current);
      setDocuments((items) => items.map((document) => document.id === updated.id ? updated : document));
      setMessage("Document organization saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save document organization");
    } finally {
      setLoading(false);
    }
  }

  async function createCollection() {
    if (!token || !workspaceId || !newCollectionName.trim()) return;
    setLoading(true);
    try {
      const collection = await api.createCollection(token, workspaceId, newCollectionName.trim());
      setCollections((items) => [...items, collection].sort((left, right) => left.name.localeCompare(right.name)));
      setNewCollectionName("");
      setMessage("Collection created.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create collection");
    } finally {
      setLoading(false);
    }
  }

  async function createAnnotation() {
    if (!token || !selected || !annotationNote.trim()) return;
    setLoading(true);
    try {
      const annotation = await api.createAnnotation(token, selected.id, 1, annotationNote.trim());
      setAnnotations((items) => [...items, annotation]);
      setAnnotationNote("");
      setMessage("Annotation added.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not add annotation");
    } finally {
      setLoading(false);
    }
  }

  async function saveDocumentReview() {
    if (!token || !selected) return;
    setLoading(true);
    try {
      const updated = await api.updateDocumentReview(token, selected.id, reviewTitle, reviewStatus, reviewNotes);
      setSelected((current) => current ? { ...current, title: updated.title, review_status: updated.review_status, review_notes: updated.review_notes } : current);
      setDocuments((items) => items.map((document) => document.id === updated.id ? updated : document));
      setMessage("Document review saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save document review");
    } finally {
      setLoading(false);
    }
  }

  async function openNotification(notification: NotificationItem) {
    if (!token) return;
    await api.markNotificationRead(token, notification.id);
    if (notification.document_id) {
      const document = documents.find((item) => item.id === notification.document_id);
      if (document) await openDocument(document);
    }
    await refresh(token);
  }

  async function exportSelectedDocument(format: "json" | "markdown") {
    if (!token || !selected) return;
    setLoading(true);
    try {
      const content = format === "json"
        ? JSON.stringify(await api.documentExportJson(token, selected.id), null, 2)
        : await api.documentExportMarkdown(token, selected.id);
      await Share.share({ title: selected.filename, message: content });
      setMessage(`Exported ${format === "json" ? "JSON" : "Markdown"} report.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Export failed");
    } finally {
      setLoading(false);
    }
  }

  async function compareSelectedDocument() {
    if (!token || !selected) return;
    const other = documents.find((document) => document.id !== selected.id);
    if (!other) {
      setMessage("Upload another document to compare.");
      return;
    }
    setLoading(true);
    try {
      const response = await api.compareDocuments(token, selected.id, other.id);
      setComparison(response);
      setMessage(`Compared with ${other.filename}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveProfile() {
    if (!token || !profileName.trim()) return;
    setLoading(true);
    try {
      const updated = await api.updateProfile(token, profileName.trim());
      setUser(updated);
      setProfileName(updated.full_name);
      setMessage("Profile updated.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update profile");
    } finally {
      setLoading(false);
    }
  }

  async function savePassword() {
    if (!token || !currentPassword || !newPassword) return;
    setLoading(true);
    try {
      await api.changePassword(token, currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setMessage("Password changed. Sign in again on other devices.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not change password");
    } finally {
      setLoading(false);
    }
  }

  async function renameWorkspace() {
    if (!token || !workspaceId || !workspaceName.trim()) return;
    setLoading(true);
    try {
      const updated = await api.updateWorkspace(token, workspaceId, workspaceName.trim());
      setWorkspaces((items) => items.map((workspace) => workspace.id === updated.id ? updated : workspace));
      setWorkspaceName(updated.name);
      setMessage("Workspace renamed.");
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not rename workspace");
    } finally {
      setLoading(false);
    }
  }

  async function leaveWorkspace() {
    if (!token || !workspaceId) return;
    setLoading(true);
    try {
      await api.leaveWorkspace(token, workspaceId);
      setWorkspaceId(null);
      setSelected(null);
      setMessages([]);
      setMessage("You left the workspace.");
      await refresh(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not leave workspace");
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    const refreshToken = await tokenStorage.getRefresh();
    if (token) await api.logout(token, refreshToken).catch(() => undefined);
    await tokenStorage.clear();
    setToken(null);
    setUser(null);
    setDocuments([]);
    setSelected(null);
    setMessages([]);
  }

  if (loading && !token) {
    return (
      <SafeAreaView style={styles.center}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  if (!token) {
    return <AuthScreen onToken={setToken} />;
  }

  return (
    <SafeAreaView style={styles.shell}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>DocIntel</Text>
          <Text style={styles.muted}>{user?.email ?? "Signed in"}</Text>
        </View>
        <View style={styles.headerActions}>
          <Pressable style={styles.secondaryButton} onPress={() => refresh()}>
            <Text style={styles.secondaryButtonText}>Refresh</Text>
          </Pressable>
          <Pressable style={styles.secondaryButton} onPress={signOut}>
            <Text style={styles.secondaryButtonText}>Sign out</Text>
          </Pressable>
        </View>
      </View>

      {message ? (
        <Pressable style={styles.notice} onPress={() => setMessage("")}>
          <Text>{message}</Text>
        </Pressable>
      ) : null}

      <View style={styles.tabs}>
        <TabButton active={tab === "documents"} label="Documents" onPress={() => setTab("documents")} />
        <TabButton active={tab === "search"} label="Search" onPress={() => setTab("search")} />
        <TabButton active={tab === "detail"} label="Detail" onPress={() => setTab("detail")} disabled={!selected} />
        <TabButton active={tab === "account"} label="Account" onPress={() => setTab("account")} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {tab === "documents" && (
          <View style={styles.stack}>
            <Text style={styles.title}>{documents.length} documents</Text>
            <Text style={styles.muted}>{readyCount} ready | {unreadCount} unread alerts</Text>
            <Pressable style={styles.button} onPress={uploadPdf}>
              <Text style={styles.buttonText}>Upload PDF</Text>
            </Pressable>
            {notifications.slice(0, 3).map((notification) => (
              <Pressable style={styles.card} key={notification.id} onPress={() => openNotification(notification)}>
                <Text style={styles.cardTitle}>{notification.title}</Text>
                <Text style={styles.bodyText}>{notification.message}</Text>
              </Pressable>
            ))}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.workspaceRow}>
              {workspaces.map((workspace) => (
                <Pressable
                  key={workspace.id}
                  style={[styles.chip, workspaceId === workspace.id && styles.activeChip]}
                  onPress={() => {
                    setWorkspaceId(workspace.id);
                    setSelected(null);
                  }}
                >
                  <Text style={workspaceId === workspace.id ? styles.activeChipText : styles.chipText}>{workspace.name}</Text>
                </Pressable>
              ))}
            </ScrollView>
            <View style={styles.row}>
              <TextInput style={[styles.input, styles.flexInput]} value={tagFilter} onChangeText={setTagFilter} placeholder="Filter tag" />
              <Pressable style={[styles.secondaryButton, favoriteOnly && styles.activeSoftButton]} onPress={() => setFavoriteOnly((value) => !value)}>
                <Text style={styles.secondaryButtonText}>{favoriteOnly ? "Favorites" : "All"}</Text>
              </Pressable>
            </View>
            <View style={styles.row}>
              <TextInput style={[styles.input, styles.flexInput]} value={newCollectionName} onChangeText={setNewCollectionName} placeholder="New collection" />
              <Pressable style={styles.secondaryButton} onPress={createCollection}>
                <Text style={styles.secondaryButtonText}>Create</Text>
              </Pressable>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.workspaceRow}>
              <Pressable style={[styles.chip, collectionFilter === null && styles.activeChip]} onPress={() => setCollectionFilter(null)}>
                <Text style={collectionFilter === null ? styles.activeChipText : styles.chipText}>All collections</Text>
              </Pressable>
              {collections.map((collection) => (
                <Pressable key={collection.id} style={[styles.chip, collectionFilter === collection.id && styles.activeChip]} onPress={() => setCollectionFilter(collection.id)}>
                  <Text style={collectionFilter === collection.id ? styles.activeChipText : styles.chipText}>{collection.name}</Text>
                </Pressable>
              ))}
            </ScrollView>
            {documents.map((document) => (
              <Pressable style={styles.card} key={document.id} onPress={() => openDocument(document)}>
                <View style={styles.row}>
                  <Text style={styles.cardTitle}>{document.favorite ? `[fav] ${document.title ?? document.filename}` : document.title ?? document.filename}</Text>
                  <Text style={[styles.badge, statusStyles[document.status]]}>{document.status}</Text>
                </View>
                <Text style={styles.muted}>{document.filename} | {document.page_count ?? "-"} pages | {document.review_status.replace("_", " ")}{document.collection_id ? ` | ${collections.find((collection) => collection.id === document.collection_id)?.name ?? "collection"}` : ""}</Text>
                {document.tags.length > 0 ? <Text style={styles.muted}>{document.tags.slice(0, 4).join(", ")}</Text> : null}
                <Text numberOfLines={3} style={styles.bodyText}>{document.summary ?? "Processing summary..."}</Text>
              </Pressable>
            ))}
          </View>
        )}

        {tab === "search" && (
          <View style={styles.stack}>
            <Text style={styles.title}>Semantic search</Text>
            <TextInput style={styles.input} value={searchQuery} onChangeText={setSearchQuery} placeholder="Search across documents" />
            <Pressable style={styles.button} onPress={runSearch}>
              <Text style={styles.buttonText}>Search</Text>
            </Pressable>
            <Pressable style={styles.secondaryButton} onPress={askWorkspace}>
              <Text style={styles.secondaryButtonText}>Ask workspace</Text>
            </Pressable>
            <View style={styles.row}>
              <TextInput style={[styles.input, styles.flexInput]} value={savedSearchName} onChangeText={setSavedSearchName} placeholder="Saved search name" />
              <Pressable style={styles.secondaryButton} onPress={saveCurrentSearch}>
                <Text style={styles.secondaryButtonText}>Save</Text>
              </Pressable>
            </View>
            {savedSearches.map((savedSearch) => (
              <View style={styles.card} key={savedSearch.id}>
                <Text style={styles.cardTitle}>{savedSearch.name}</Text>
                <Text style={styles.muted}>{savedSearch.query}</Text>
                <View style={styles.row}>
                  <Pressable style={styles.secondaryButton} onPress={() => applySavedSearch(savedSearch)}>
                    <Text style={styles.secondaryButtonText}>Apply</Text>
                  </Pressable>
                  <Pressable style={styles.dangerButton} onPress={() => deleteSavedSearch(savedSearch)}>
                    <Text style={styles.dangerButtonText}>Delete</Text>
                  </Pressable>
                </View>
              </View>
            ))}
            {workspaceAnswer ? (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Workspace answer</Text>
                <Text style={styles.bodyText}>{workspaceAnswer.answer}</Text>
                <Text style={styles.muted}>Confidence {Math.round(workspaceAnswer.confidence * 100)}% | {workspaceAnswer.grounded ? "grounded" : "needs review"}</Text>
              </View>
            ) : null}
            {searchResults.map((result) => (
              <Pressable
                style={styles.card}
                key={`${result.document_id}-${result.page_number}-${result.text.slice(0, 12)}`}
                onPress={() => {
                  const document = documents.find((item) => item.id === result.document_id);
                  if (document) openDocument(document);
                }}
              >
                <View style={styles.row}>
                  <Text style={styles.cardTitle}>{result.filename}</Text>
                  <Text style={styles.muted}>{Math.round(result.score * 100)}%</Text>
                </View>
                <Text style={styles.muted}>Page {result.page_number ?? "-"}</Text>
                <Text style={styles.bodyText}>{result.text}</Text>
              </Pressable>
            ))}
          </View>
        )}

        {tab === "detail" && selected && (
          <View style={styles.stack}>
            <View style={styles.row}>
              <Text style={styles.title}>{selected.title ?? selected.filename}</Text>
              <Pressable style={styles.dangerButton} onPress={deleteSelectedDocument}>
                <Text style={styles.dangerButtonText}>Delete</Text>
              </Pressable>
            </View>
            <View style={styles.row}>
              <Pressable style={styles.secondaryButton} onPress={() => exportSelectedDocument("json")}>
                <Text style={styles.secondaryButtonText}>Export JSON</Text>
              </Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => exportSelectedDocument("markdown")}>
                <Text style={styles.secondaryButtonText}>Export Markdown</Text>
              </Pressable>
            </View>
            <Pressable style={styles.secondaryButton} onPress={compareSelectedDocument}>
              <Text style={styles.secondaryButtonText}>Compare with another document</Text>
            </Pressable>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Organization</Text>
              <TextInput style={styles.input} value={tagInput} onChangeText={setTagInput} placeholder="Tags separated by commas" />
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.workspaceRow}>
                <Pressable style={[styles.chip, selectedCollectionId === null && styles.activeChip]} onPress={() => setSelectedCollectionId(null)}>
                  <Text style={selectedCollectionId === null ? styles.activeChipText : styles.chipText}>No collection</Text>
                </Pressable>
                {collections.map((collection) => (
                  <Pressable key={collection.id} style={[styles.chip, selectedCollectionId === collection.id && styles.activeChip]} onPress={() => setSelectedCollectionId(collection.id)}>
                    <Text style={selectedCollectionId === collection.id ? styles.activeChipText : styles.chipText}>{collection.name}</Text>
                  </Pressable>
                ))}
              </ScrollView>
              <Pressable style={[styles.secondaryButton, documentFavorite && styles.activeSoftButton]} onPress={() => setDocumentFavorite((value) => !value)}>
                <Text style={styles.secondaryButtonText}>{documentFavorite ? "Favorite" : "Mark favorite"}</Text>
              </Pressable>
              <Pressable style={styles.button} onPress={saveDocumentOrganization}>
                <Text style={styles.buttonText}>Save organization</Text>
              </Pressable>
            </View>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Review</Text>
              <TextInput style={styles.input} value={reviewTitle} onChangeText={setReviewTitle} placeholder="Document title" />
              <View style={styles.wrapRow}>
                {(["unreviewed", "in_review", "approved", "needs_changes"] as DocumentReviewStatus[]).map((status) => (
                  <Pressable
                    key={status}
                    style={[styles.secondaryButton, reviewStatus === status && styles.activeSoftButton]}
                    onPress={() => setReviewStatus(status)}
                  >
                    <Text style={styles.secondaryButtonText}>{status.replace("_", " ")}</Text>
                  </Pressable>
                ))}
              </View>
              <TextInput style={[styles.input, styles.textArea]} value={reviewNotes} onChangeText={setReviewNotes} placeholder="Reviewer notes" multiline />
              <Pressable style={styles.button} onPress={saveDocumentReview}>
                <Text style={styles.buttonText}>Save review</Text>
              </Pressable>
            </View>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Annotations</Text>
              {annotations.map((annotation) => (
                <View style={styles.chatBubble} key={annotation.id}>
                  <Text style={styles.cardTitle}>Page {annotation.page_number}</Text>
                  <Text style={styles.bodyText}>{annotation.note}</Text>
                </View>
              ))}
              <TextInput style={styles.input} value={annotationNote} onChangeText={setAnnotationNote} placeholder="Add note for page 1" />
              <Pressable style={styles.button} onPress={createAnnotation}>
                <Text style={styles.buttonText}>Add annotation</Text>
              </Pressable>
            </View>
            {comparison ? (
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Comparison</Text>
                <Text style={styles.bodyText}>{comparison.left.filename} vs {comparison.right.filename}</Text>
                <Text style={styles.bodyText}>Similarity: {Math.round(comparison.similarity * 100)}%</Text>
                <Text style={styles.bodyText}>Only in first: {comparison.risk_changes.only_in_left.join(", ") || "No unique risks"}</Text>
                <Text style={styles.bodyText}>Only in second: {comparison.risk_changes.only_in_right.join(", ") || "No unique risks"}</Text>
              </View>
            ) : null}
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Summary</Text>
              <Text style={styles.bodyText}>{selected.summary ?? "No summary yet."}</Text>
            </View>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Intelligence</Text>
              <Text style={styles.bodyText}>Type: {selected.document_type ?? "Pending"}</Text>
              <Text style={styles.bodyText}>Confidence: {selected.document_type_confidence ?? "-"}%</Text>
              {(selected.risk_flags ?? []).map((risk, index) => (
                <View style={styles.risk} key={`${risk.label}-${index}`}>
                  <Text style={styles.cardTitle}>{risk.label}</Text>
                  <Text style={styles.muted}>{risk.severity} | {risk.confidence}%</Text>
                  <Text style={styles.bodyText}>{risk.evidence}</Text>
                </View>
              ))}
            </View>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Chat</Text>
              {messages.map((chatMessage) => (
                <View style={[styles.chatBubble, chatMessage.role === "user" && styles.userBubble]} key={chatMessage.id}>
                  <Text style={styles.cardTitle}>{chatMessage.role === "user" ? "You" : "Assistant"}</Text>
                  <Text style={styles.bodyText}>{chatMessage.content}</Text>
                </View>
              ))}
              <TextInput style={[styles.input, styles.textArea]} value={question} onChangeText={setQuestion} placeholder="Ask this document" multiline />
              <Pressable style={styles.button} onPress={askQuestion}>
                <Text style={styles.buttonText}>Ask</Text>
              </Pressable>
            </View>
          </View>
        )}

        {tab === "account" && (
          <View style={styles.stack}>
            <Text style={styles.title}>Account</Text>
            <Text style={styles.muted}>{user?.email}</Text>
            <TextInput style={styles.input} value={profileName} onChangeText={setProfileName} placeholder="Full name" />
            <Pressable style={styles.button} onPress={saveProfile}>
              <Text style={styles.buttonText}>Save profile</Text>
            </Pressable>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Password</Text>
              <TextInput style={styles.input} value={currentPassword} onChangeText={setCurrentPassword} placeholder="Current password" secureTextEntry />
              <TextInput style={styles.input} value={newPassword} onChangeText={setNewPassword} placeholder="New password" secureTextEntry />
              <Pressable style={styles.button} onPress={savePassword}>
                <Text style={styles.buttonText}>Change password</Text>
              </Pressable>
            </View>
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>Workspace</Text>
              <Text style={styles.muted}>{currentWorkspace?.name ?? "No active workspace"}</Text>
              <TextInput style={styles.input} value={workspaceName} onChangeText={setWorkspaceName} placeholder="Workspace name" />
              <Pressable style={styles.button} onPress={renameWorkspace} disabled={!workspaceId || workspaceName.trim() === currentWorkspace?.name}>
                <Text style={styles.buttonText}>Rename workspace</Text>
              </Pressable>
              <Pressable style={styles.dangerButton} onPress={leaveWorkspace} disabled={!workspaceId}>
                <Text style={styles.dangerButtonText}>Leave workspace</Text>
              </Pressable>
            </View>
          </View>
        )}
      </ScrollView>

      {loading ? <ActivityIndicator style={styles.loader} /> : null}
    </SafeAreaView>
  );
}

function AuthScreen({ onToken }: { onToken: (token: string) => void }) {
  const [mode, setMode] = useState<"login" | "register" | "reset">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setMessage("");
    try {
      if (mode === "reset") {
        if (resetToken.trim()) {
          await api.confirmPasswordReset(resetToken.trim(), password);
          setPassword("");
          setResetToken("");
          setMode("login");
          setMessage("Password updated. Sign in with the new password.");
          return;
        }

        const response = await api.requestPasswordReset(email);
        if (response.reset_token) {
          setResetToken(response.reset_token);
          setMessage("Reset token generated for local development. Enter a new password and submit again.");
        } else {
          setMessage(response.message);
        }
        return;
      }

      const response = mode === "login" ? await api.login(email, password) : await api.register(fullName, email, password);
      await tokenStorage.setPair(response.access_token, response.refresh_token);
      onToken(response.access_token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.authShell}>
      <StatusBar style="dark" />
      <Text style={styles.brandLarge}>DocIntel</Text>
      <Text style={styles.subtitle}>Document intelligence on the move</Text>
      <View style={styles.tabs}>
        <TabButton active={mode === "login"} label="Sign in" onPress={() => setMode("login")} />
        <TabButton active={mode === "register"} label="Create" onPress={() => setMode("register")} />
        <TabButton active={mode === "reset"} label="Reset" onPress={() => setMode("reset")} />
      </View>
      {mode === "register" ? <TextInput style={styles.input} value={fullName} onChangeText={setFullName} placeholder="Full name" /> : null}
      <TextInput style={styles.input} value={email} onChangeText={setEmail} placeholder="Email" autoCapitalize="none" keyboardType="email-address" />
      {mode === "reset" ? <TextInput style={styles.input} value={resetToken} onChangeText={setResetToken} placeholder="Reset token" autoCapitalize="none" /> : null}
      <TextInput style={styles.input} value={password} onChangeText={setPassword} placeholder={mode === "reset" ? "New password" : "Password"} secureTextEntry />
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Pressable style={styles.button} onPress={submit} disabled={loading}>
        <Text style={styles.buttonText}>
          {loading ? "Working..." : mode === "login" ? "Sign in" : mode === "register" ? "Create account" : resetToken.trim() ? "Set new password" : "Request reset"}
        </Text>
      </Pressable>
    </SafeAreaView>
  );
}

function TabButton({ active, disabled, label, onPress }: { active: boolean; disabled?: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable style={[styles.tab, active && styles.activeTab, disabled && styles.disabled]} onPress={onPress} disabled={disabled}>
      <Text style={active ? styles.activeTabText : styles.tabText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1, backgroundColor: "#f6f7f9" },
  authShell: { flex: 1, justifyContent: "center", padding: 22, gap: 12, backgroundColor: "#f6f7f9" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: { padding: 18, flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#dfe4ea" },
  headerActions: { flexDirection: "row", gap: 8 },
  brand: { fontSize: 22, fontWeight: "800", color: "#17202a" },
  brandLarge: { fontSize: 38, fontWeight: "900", color: "#17202a" },
  subtitle: { color: "#637083", fontSize: 16, marginBottom: 12 },
  content: { padding: 16, paddingBottom: 40 },
  stack: { gap: 12 },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  wrapRow: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 8 },
  title: { fontSize: 24, fontWeight: "800", color: "#17202a" },
  sectionTitle: { fontSize: 18, fontWeight: "800", color: "#17202a", marginBottom: 8 },
  card: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#dfe4ea", borderRadius: 8, padding: 14, gap: 8 },
  cardTitle: { fontWeight: "800", color: "#17202a", flex: 1 },
  bodyText: { color: "#334155", lineHeight: 20 },
  muted: { color: "#637083", fontSize: 13 },
  input: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#dfe4ea", borderRadius: 8, paddingHorizontal: 12, paddingVertical: 11, color: "#17202a" },
  flexInput: { flex: 1 },
  textArea: { minHeight: 90, textAlignVertical: "top" },
  button: { minHeight: 44, borderRadius: 8, backgroundColor: "#0f766e", alignItems: "center", justifyContent: "center", paddingHorizontal: 14 },
  buttonText: { color: "#fff", fontWeight: "800" },
  secondaryButton: { borderRadius: 8, backgroundColor: "#e8eef2", paddingHorizontal: 12, paddingVertical: 9 },
  activeSoftButton: { backgroundColor: "#b7d9d5" },
  secondaryButtonText: { color: "#17202a", fontWeight: "700" },
  dangerButton: { borderRadius: 8, backgroundColor: "#fee4e2", paddingHorizontal: 12, paddingVertical: 9 },
  dangerButtonText: { color: "#b42318", fontWeight: "800" },
  tabs: { flexDirection: "row", gap: 8, paddingHorizontal: 16, paddingTop: 12 },
  tab: { flex: 1, borderRadius: 8, backgroundColor: "#e8eef2", alignItems: "center", paddingVertical: 10 },
  activeTab: { backgroundColor: "#0f766e" },
  disabled: { opacity: 0.45 },
  tabText: { color: "#17202a", fontWeight: "800" },
  activeTabText: { color: "#fff", fontWeight: "800" },
  workspaceRow: { gap: 8, paddingVertical: 4 },
  chip: { borderWidth: 1, borderColor: "#dfe4ea", borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: "#fff" },
  activeChip: { backgroundColor: "#0f766e", borderColor: "#0f766e" },
  chipText: { color: "#17202a", fontWeight: "700" },
  activeChipText: { color: "#fff", fontWeight: "700" },
  badge: { overflow: "hidden", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 4, fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  status_ready: { backgroundColor: "#dcfae6", color: "#067647" },
  status_failed: { backgroundColor: "#fee4e2", color: "#b42318" },
  status_processing: { backgroundColor: "#fff1d6", color: "#b54708" },
  status_uploaded: { backgroundColor: "#fff1d6", color: "#b54708" },
  notice: { margin: 12, padding: 10, backgroundColor: "#e8eef2", borderRadius: 8 },
  error: { color: "#b42318" },
  risk: { borderLeftWidth: 4, borderLeftColor: "#b54708", paddingLeft: 10, gap: 4 },
  chatBubble: { backgroundColor: "#fbfcfd", borderWidth: 1, borderColor: "#dfe4ea", borderRadius: 8, padding: 10, gap: 4 },
  userBubble: { backgroundColor: "#effaf8", borderColor: "#b7d9d5" },
  loader: { position: "absolute", right: 18, bottom: 18 }
});
