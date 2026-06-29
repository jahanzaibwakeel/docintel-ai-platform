# AI Document Intelligence Platform

A full-stack document intelligence app for uploading PDFs, extracting text, summarizing content, asking document questions, extracting entities/key fields, and searching across documents with semantic search.

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, pgvector
- Frontend: Next.js, React, TypeScript
- Mobile app: Expo, React Native, TypeScript
- Background jobs: Redis + Celery
- AI: OpenAI, Ollama, or local fallback mode
- Deployment: Docker Compose

## Quick Start

1. Copy environment values:

```powershell
Copy-Item .env.example .env
```

2. Edit `.env` and choose an AI provider:

```env
AI_PROVIDER=fallback
# or
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
# or
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

3. Start the stack:

```powershell
.\scripts\dev.cmd
```

4. Open the app:

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

The helper scripts set `DOCKER_CONFIG` to the repo-local [.docker](/C:/Users/Dossani%20Computer/Documents/Documentaion%20Platform/.docker) folder. This avoids Docker CLI warnings caused by unreadable user-level Docker config files on Windows.

You can also run one-off Compose commands through:

```powershell
.\scripts\compose.cmd config
.\scripts\compose.cmd up --build
```

If your PowerShell execution policy allows local scripts, the `.ps1` helpers are available too.

## Development

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Worker:

```powershell
cd backend
celery -A app.worker.celery_app worker --loglevel=INFO
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Mobile app:

```powershell
cd mobile
npm install
npm run start
```

Set the mobile API URL in `mobile/.env` or your shell:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1
```

For a physical phone, replace `localhost` with your computer's LAN IP address.

## Operations

Health endpoints:

- `GET /health` is a lightweight liveness check.
- `GET /ready` checks PostgreSQL and Redis and returns `503` when a dependency is unavailable.

Logs:

- Backend requests include an `x-request-id` response header.
- JSON logs are enabled by default with `JSON_LOGS=true`.
- Set `LOG_LEVEL=DEBUG` for more verbose backend logs.

Admin access:

- Set `ADMIN_EMAILS=admin@example.com,ops@example.com` to enable admin operations for specific accounts.
- Refresh-token sessions are enabled by default. Set `REFRESH_TOKEN_EXPIRE_DAYS=30` to tune session lifetime.
- Password reset tokens are one-time use and expire after `PASSWORD_RESET_EXPIRE_MINUTES=30`.
- Local development returns reset tokens in API responses with `PASSWORD_RESET_RETURN_TOKEN=true`. Disable this when an email delivery provider is wired in.

Metrics:

- `GET /metrics` exposes Prometheus-style text metrics.
- HTTP metrics include request count and duration by method, route, and status code.
- Worker metrics include document processing job counts and processing duration summaries.

Backups:

```powershell
.\scripts\backup-db.cmd
.\scripts\restore-db.cmd backups\docintel-YYYYMMDD-HHMMSS.sql
```

CI:

- GitHub Actions is configured in `.github/workflows/ci.yml`.
- It compiles backend code, installs/builds the frontend, and validates Docker Compose.

Tests:

```powershell
.\scripts\test-backend.cmd
```

Backend tests run inside the Docker image and use `tests/run_tests.py`, which fails if any test is skipped.

## Core Workflow

1. Register or sign in.
2. Upload a PDF.
3. The API stores metadata and dispatches a background job.
4. The worker extracts PDF text, chunks it, generates embeddings, extracts fields, and creates a summary.
5. The dashboard shows processing status and document actions.
6. Ask questions against a selected document or run semantic search across all uploaded documents.

## Upgrade Roadmap

### Phase 1: Production Foundation

- Alembic database migrations.
- Safer upload validation and file metadata.
- Page-aware chunks, citations, and search results.
- Richer document detail UI with processing metadata and extracted text.

### Phase 2: OCR and Document Quality

- OCR fallback for scanned PDF pages.
- Per-page extraction diagnostics.
- Authenticated PDF preview in the document detail view.
- Better failure recovery and retry controls.

### Phase 3: Advanced RAG

- Hybrid keyword plus vector search.
- Lightweight reranking for stronger answer grounding.
- Saved chat history with citations per document.
- Search score breakdowns for vector and keyword matching.

### Phase 4: Structured Intelligence

- Document type classification with confidence.
- Structured field groups with per-value confidence.
- Risk flag detection with severity and evidence.
- Intelligence dashboard section for classification, fields, and risks.

### Phase 5: Team and Compliance

- Workspaces with owner/admin/member/viewer roles.
- Personal workspace creation on registration.
- Shared workspace document access.
- Audit logs for registration, workspace creation, uploads, views, downloads, reprocessing, questions, and chat clearing.
- Workspace member invite/update by email.

### Phase 6: Operations

- CI checks for backend and frontend.
- Structured JSON request logging with request IDs.
- Liveness/readiness endpoints.
- Docker healthchecks and restart policies.
- Production frontend container start command.
- Database backup and restore scripts.

### Phase 7: Reliability and Data Lifecycle

- Backend service tests with standard-library `unittest`.
- Frontend typecheck script and mobile metadata smoke check in CI.
- Document deletion with audit logs.
- Retention expiry metadata and cleanup task.
- Deleted documents are removed from normal document lists and search.

Retention cleanup can be run through Celery:

```powershell
cd backend
celery -A app.worker.celery_app call cleanup_expired_documents --args="[100]"
```

### Phase 8: Storage and Security

- Local/S3-compatible storage abstraction for PDFs.
- Optional S3/MinIO signed file access.
- Server-side encryption flag for S3-compatible uploads.
- PII detection and redaction before external AI calls.
- External AI with PII is blocked unless redaction is enabled or explicitly allowed.

Storage defaults to local Docker volume storage. To use MinIO or S3-compatible storage:

```env
STORAGE_PROVIDER=s3
STORAGE_BUCKET=docintel
STORAGE_ENDPOINT_URL=http://minio:9000
STORAGE_ACCESS_KEY_ID=minioadmin
STORAGE_SECRET_ACCESS_KEY=minioadmin
```

External AI privacy controls:

```env
REDACT_PII_FOR_EXTERNAL_AI=true
ALLOW_EXTERNAL_AI_WITH_PII=false
```

### Phase 9: Mobile App

- Expo mobile companion app.
- JWT sign-in/register.
- Workspace document dashboard.
- Native PDF upload with Expo DocumentPicker.
- Semantic search.
- Document detail, summary, intelligence, and chat.
- Mobile document delete and refresh controls.
- Later: PDF preview, push notifications, and offline cache.

### Phase 10: Enterprise AI

- Cross-document workspace Q&A.
- Streaming-compatible workspace Q&A endpoint using Server-Sent Events.
- Prompt version metadata on answers.
- Answer confidence scoring from citations.
- Citation validation flags and grounded answer status.
- Later: provider-native token streaming, dedicated reranker model, document comparison, and clause library.

### Phase 11: QA and Migration Validation

- Docker-backed backend test suite with pinned dependencies.
- No skipped backend tests allowed.
- PostgreSQL, Redis, and pgvector are available during backend tests.
- Migration smoke test validates expected tables and pgvector extension.

### Phase 12: API Workflow and Dependency Gates

- FastAPI integration tests for registration, personal workspace creation, login failures, auth boundaries, PDF upload validation, and document listing.
- Fixed SQLAlchemy document ownership relationships after adding deletion ownership metadata.
- Pinned a compatible bcrypt runtime for reliable password hashing.
- CI now audits frontend and mobile dependencies, builds the frontend, and typechecks both web and mobile apps.
- Frontend and mobile npm dependency trees resolve with zero reported vulnerabilities.

### Phase 13: Observability

- Prometheus-style `/metrics` endpoint.
- Request metrics for counts and durations labeled by method, route, and status code.
- Document processing worker metrics for started, ignored, ready, and failed jobs.
- Document processing duration summaries.
- Backend tests for metrics rendering and endpoint exposure.

### Phase 14: Document Export

- Document intelligence export endpoint: `GET /api/v1/documents/{id}/export?format=json|markdown`.
- JSON exports include metadata, summary, key fields, structured fields, risk flags, diagnostics, and extracted text.
- Markdown exports produce a readable report for sharing or archiving.
- Web dashboard export actions for JSON and Markdown.
- Mobile app export/share actions for JSON and Markdown.
- API workflow tests validate export authorization, attachment headers, and exported content.

### Phase 15: Document Comparison

- Document comparison endpoint: `POST /api/v1/documents/{id}/compare`.
- Deterministic comparison of summaries, key fields, risk flags, and extracted text terms.
- Similarity score based on extracted text or summaries.
- Web dashboard comparison panel for selected documents.
- Mobile comparison action in document detail.
- API workflow test coverage for field, risk, and text comparison behavior.

### Phase 16: Security and Search Filters

- API rate limiting middleware with Redis support and in-memory fallback.
- Configurable rate limit settings: `RATE_LIMIT_ENABLED` and `RATE_LIMIT_PER_MINUTE`.
- Rate-limited responses return `429` with `Retry-After`.
- Document listing filters for status, document type, created date range, workspace, and risk severity.
- Semantic search filters for workspace, status, document type, created date range, and risk severity.
- Web dashboard filter controls for status, document type, and risk severity.
- Mobile semantic search remains scoped to the active workspace.
- Backend tests for rate limiting and filtered document/search behavior.

### Phase 17: Admin Operations

- Environment-configured admins through `ADMIN_EMAILS`.
- Admin API endpoints for platform stats, users, workspaces, and documents.
- Failed-job document view for operational triage.
- Web dashboard admin operations panel for configured admins.
- Backend tests for admin authorization, stats, users, workspaces, and failed documents.

### Phase 18: In-App Notifications

- Persistent notifications table with Alembic migration.
- Notification API for listing recent alerts, unread counts, and marking notifications read.
- Worker emits document-ready and document-failed notifications for document owners.
- Web dashboard notification panel with unread count and mark-read behavior.
- Mobile document list shows recent alerts and unread count.
- Backend tests for notification ownership, unread counts, mark-read behavior, and migration coverage.

### Phase 19: Stronger Auth Sessions

- Database-backed refresh tokens.
- Refresh-token hashing at rest.
- Token rotation through `POST /api/v1/auth/refresh`.
- Logout/revoke endpoint: `POST /api/v1/auth/logout`.
- Web and mobile clients store refresh tokens and revoke them on sign out.
- Backend tests for refresh rotation, old-token reuse rejection, logout revocation, and migration coverage.

### Phase 20: Password Reset

- Password reset request endpoint: `POST /api/v1/auth/password-reset/request`.
- Password reset confirmation endpoint: `POST /api/v1/auth/password-reset/confirm`.
- Hashed, one-time reset tokens with configurable expiry.
- Existing refresh sessions are revoked after a password change.
- Web and mobile reset flows for requesting a token and setting a new password.
- Backend tests cover unknown-email privacy, token reuse rejection, login with the new password, refresh-session revocation, and migration coverage.

### Phase 21: Email Delivery

- Email service abstraction with `outbox`, `smtp`, and `disabled` providers.
- Local development outbox writes JSONL emails to `EMAIL_OUTBOX_DIR`.
- SMTP settings for production password reset delivery.
- Password reset requests send reset links based on `FRONTEND_ORIGIN`.
- Web reset links auto-open the password reset flow from `?reset_token=...`.
- Backend tests cover outbox delivery, reset link generation, and password reset email emission.

### Phase 22: Workspace Invite Emails

- Workspace member additions and role updates send email notifications.
- Invite emails include workspace name, assigned role, inviter email, and app link.
- Local outbox mode captures invite emails for development and tests.
- Dashboard shows a clear success/error state when inviting members.
- Backend tests cover invite email generation and API-triggered delivery.

### Phase 23: Pending Workspace Invitations

- Inviting an email without an existing account creates a pending workspace invitation instead of failing.
- Invitation tokens are hashed at rest and expire after `WORKSPACE_INVITE_EXPIRE_DAYS`.
- Invite links use `?invite_token=...` and can be accepted after sign-in.
- `POST /api/v1/workspaces/invitations/accept` converts valid invitations into workspace memberships.
- Dashboard auto-accepts invite links for the signed-in matching email.
- Backend tests cover pending invite creation, email link delivery, acceptance, token reuse rejection, and migration coverage.

### Phase 24: Invitation Management

- Workspace admins can list pending invitations.
- Invitation resends rotate the invite token and send a fresh email.
- Invitation revocation closes mistaken or stale invites.
- Dashboard shows pending invites with resend and revoke actions.
- Web and mobile API clients expose invitation management helpers.
- Backend tests cover list, resend, rotated-token rejection, revoke, and revoked-token rejection.

### Phase 25: Workspace Member Management

- Workspace member responses include user email addresses for usable team administration.
- Workspace admins can update member roles through `PATCH /api/v1/workspaces/{workspace_id}/members/{member_id}`.
- Workspace admins can remove members through `DELETE /api/v1/workspaces/{workspace_id}/members/{member_id}`.
- Last-owner protection prevents demoting or removing the final workspace owner.
- Dashboard shows members with role selectors and remove actions.
- Web and mobile API clients expose member management helpers.
- Backend tests cover member listing, role updates, removal, and last-owner safeguards.

### Phase 26: Account Settings

- Authenticated users can update their own full name through `PATCH /api/v1/auth/me`.
- Authenticated users can change a known password through `POST /api/v1/auth/change-password`.
- Password changes verify the current password and revoke existing refresh sessions.
- Web dashboard includes profile and password controls.
- Mobile app includes an Account tab for profile and password updates.
- Backend tests cover profile update, incorrect current password rejection, old-password rejection, new-password login, and refresh-token revocation.

### Phase 27: Workspace Settings

- Workspace admins can rename workspaces through `PATCH /api/v1/workspaces/{workspace_id}`.
- Workspace members can leave workspaces through `POST /api/v1/workspaces/{workspace_id}/leave`.
- Last-owner protection prevents the final owner from leaving a workspace.
- Web dashboard includes active workspace rename and leave controls.
- Mobile app Account tab includes active workspace rename and leave controls.
- Backend tests cover admin rename, member rename rejection, member leave, and last-owner safeguards.

### Phase 28: Document Organization

- Documents support normalized tags and a favorite flag.
- Document organization can be updated through `PATCH /api/v1/documents/{document_id}/organization`.
- Document lists can filter by `tag` and `favorite`.
- Semantic search accepts the same tag and favorite filters.
- Web dashboard includes tag/favorite filters, document badges, and selected-document organization controls.
- Mobile app includes tag/favorite filters and selected-document organization controls.
- Backend tests cover migration columns, metadata normalization, list filters, and search filters.

### Phase 29: Review Workflow

- Documents support a custom title, review status, and reviewer notes.
- Review metadata can be updated through `PATCH /api/v1/documents/{document_id}/review`.
- Document lists and semantic search can filter by review status.
- JSON and Markdown exports include title, tags, favorite state, review status, and review notes.
- Web dashboard includes review filters and selected-document review controls.
- Mobile app includes selected-document review controls.
- Backend tests cover migration columns, review updates, review filters, review-aware search, and export metadata.

### Phase 30: Saved Searches

- Users can save reusable semantic search queries with their current filters.
- Saved searches are user-owned and can be scoped to a workspace.
- Saved search API supports create, list, update, and delete through `/api/v1/saved-searches`.
- Web dashboard can save, apply, and delete saved searches.
- Mobile app Search tab can save, apply, and delete saved searches.
- Backend tests cover workspace scoping, ownership isolation, update, delete, and migration coverage.

### Phase 31: Collections, Annotations, and Bulk Actions

- Workspace document collections/folders are available through `/api/v1/collections`.
- Documents can be assigned to collections and filtered/searched by collection.
- Document annotations support page number, quoted text, note text, and color through `/api/v1/documents/{id}/annotations`.
- Bulk document actions can add tags, mark favorites, update review status, and assign collections through `POST /api/v1/documents/bulk`.
- Web dashboard includes collection management, collection filters, selected-document annotations, and bulk metadata controls.
- Mobile app includes collection filters, collection assignment, and simple document annotation notes.
- Backend tests cover collection CRUD, bulk updates, collection-filtered list/search, annotation create/list/delete, and migration coverage.

### Phase 32: Deployment Hardening, AI Ops, and PDF Review

- Production deployment files are included in `.env.production.example`, `docker-compose.prod.yml`, and `deploy/nginx.conf`.
- The production override hides direct backend, frontend, PostgreSQL, and Redis host ports behind an HTTPS Nginx proxy.
- Copy `.env.production.example` to `.env.production`, set real secrets/domains/TLS certificate paths, then run `scripts/prod-up.cmd`.
- AI provider status is available at `GET /api/v1/ai/status` with provider, model, embedding model, timeout, context window, PII policy, and optional health check details.
- Web dashboard surfaces AI runtime configuration so operators can confirm whether fallback, OpenAI, or Ollama is active.
- The PDF review area adds page navigation, zoom controls, annotation page jumping, and quick annotation quote capture from selected text.

## Notes

- `fallback` AI mode uses deterministic embeddings and extractive summaries, useful for local demos and tests without an LLM.
- `openai` mode uses OpenAI chat and embedding APIs.
- `ollama` mode expects a running Ollama daemon with the configured generation and embedding models.
- Uploaded files are persisted in the Docker `uploads` volume.
