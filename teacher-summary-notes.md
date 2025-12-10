# Teacher View Summary Notes

## Current Flow
- `ClassDetails` (`curiosity-coach-frontend/src/components/ClassDetails.tsx`) and `ClassSummary` (`curiosity-coach-frontend/src/components/ClassSummary.tsx`) both call `getStudentsForClass`, which in turn hits `GET /api/students` and loads each student’s latest conversation *plus all messages*. Navigating between the pages triggers the same heavy fetch twice.
- `ClassSummary` follows up with a `POST /api/students/class-analysis` call as soon as the roster resolves. The backend (`backend/src/students/router.py`) repeats the class query, refetches the latest conversation messages, flattens them, and asks Brain for a fresh summary on every visit.
- `StudentAnalysis` (`curiosity-coach-frontend/src/components/StudentAnalysis.tsx`) makes `POST /api/students/{id}/analysis` each time a teacher opens “Analyze Kid”, forcing the backend to materialize all of that student’s conversations/messages and re-run Brain with no caching.

## Pain Points
- Duplicate DB work: class roster + message hydration happens on every page hop and again inside each analysis endpoint.
- LLM summaries are recomputed synchronously, even if nothing changed, adding latency and cost.
- Frontend has no shared cache/context, so results fetched in one view are discarded before visiting the next.

## Optimization Ideas
1. **Frontend data reuse**
   - Introduce a shared store (React Context/React Query) so `ClassDetails` and `ClassSummary` recycle the same fetched roster and conversations instead of reloading per navigation.
   - Pass the already-fetched student list via router state when moving from `ClassDetails` → `ClassSummary`, and only refetch when the parameters change.

2. **Backend shape improvements**
   - Split `GET /students` into a lightweight variant (metadata only) and defer message hydration to explicit calls. Most UI surfaces only need last-chat metadata, not full message lists.
   - Extend `/students/class-analysis` to reuse the conversations already retrieved during the roster query. For example, accept a list of conversation IDs (or timestamps) from the client and skip re-querying when unchanged.

3. **Caching & background refresh**
   - Store class/student analysis in a table keyed by (school, grade, section) or student ID with a `computed_at` timestamp. Return cached summaries instantly and trigger async recompute when the data is stale.
   - Use task queue/cron to refresh analyses periodically so teachers see recent insights without waiting for synchronous LLM calls.

4. **Change detection**
   - Track a hash/updated timestamp for the latest conversation set. Only rerun Brain when the set changes. Otherwise, serve cached copy.
   - Emit events when new messages land and let that invalidate the cached analysis for affected class/student.

5. **UI experience tweaks**
   - Show cached analysis immediately with a “last updated” indicator and optional “Refresh analysis” button that re-triggers the compute flow on demand.

These tactics should trim redundant work, keep the UI responsive, and reduce Brain/DB load while preserving the teacher experience.

## Longer-Term Architecture (Async + Caching)
- Persist class/student analyses in dedicated tables (e.g., `class_analyses`, `student_analyses`) with fields for identifiers, `analysis_text`, `status`, `computed_at`, `last_message_hash`. Let the teacher UI read from there.
- Turn the existing `/students/class-analysis` and `/students/{id}/analysis` endpoints into async launchers: return `202 Accepted` with a `job_id` if a fresh computation is needed, otherwise emit cached data immediately.
- Reuse the SQS-backed `QueueService` and `tasks` infrastructure to enqueue `CLASS_ANALYSIS` / `STUDENT_ANALYSIS` jobs. A worker can hydrate conversations, call Brain, upsert the DB row, and mark the job `completed`.
- Add job-tracking tables (`analysis_jobs`) keyed by `job_id` so the frontend can poll `GET /analysis-jobs/{job_id}` (or use SSE/WebSocket later). When status flips to `completed`, fetch the cached analysis.
- Frontend flow: show cached analysis + timestamp instantly. If a new run is triggered, display “Refreshing…” with exponential backoff polling. Allow manual retry to handle failure states.
- Cache invalidation: listen for new conversation messages (e.g., in the message write path) and flag the relevant class/student analyses as `stale`, prompting the next UI load to queue a refresh.

## Implementation Plan (Step-by-Step)
1. **Database Layer**
   1. Add Alembic migration to create `class_analyses` and `student_analyses` tables with identifiers, `analysis_text`, `status` (enum: queued, running, ready, failed), `computed_at`, `last_message_hash`, and audit fields (`created_at`, `updated_at`).
   2. Create `analysis_jobs` table storing `job_id` (UUID), `analysis_type` (class/student), target identifiers, `status`, `error`, and timestamps.
   3. Update SQLAlchemy models + Pydantic schemas to expose these tables.

2. **Backend API Changes**
   1. Refactor `/students/class-analysis` and `/students/{id}/analysis` to:
      - Look up cached analysis via SQLAlchemy model.
      - Compare incoming conversation hash to `last_message_hash`.
      - If valid cache: return `200` with `analysis`, `computed_at`, `status='ready'` and omit queuing unless `force_refresh=true`.
      - If stale/missing: enqueue job, upsert row `status='queued'`, return `202` with `job_id`, latest cached text (if any), and `status`.
   2. Add `GET /analysis-jobs/{job_id}` endpoint returning job status plus latest cached analysis snapshot.
   3. Ensure message write paths (conversation create/update) mark related analyses `status='stale'` (or adjust hash) to force refresh on next request.

3. **Queue & Worker**
   1. Introduce new task payload types (`CLASS_ANALYSIS`, `STUDENT_ANALYSIS`) in `QueueService` and the consumer.
   2. Worker flow: hydrate conversations/messages, compute hash, call Brain `/class-analysis` or `/student-analysis`, store results to corresponding table, update job + analysis rows to `ready` with `computed_at` (and error handling to mark `failed`).
   3. Reuse existing task runner (SQS consumer/Lambda or background worker). Ensure idempotency by checking if newer job already completed.

4. **Brain Service**
   1. No contract change required; continue accepting the same payload. Optionally add ability to return rich HTML and metadata (author, sections) if needed.
   2. Consider returning structured data instead of raw HTML long term; for now the backend can still store the HTML string.

5. **Frontend Updates**
   1. Update `ClassSummary` and `StudentAnalysis` components to call the new API shape (expect `status`, `job_id`, `analysis`, `computed_at`).
   2. If response is `202`, show cached analysis immediately (if present), display “Refreshing / last updated …” banner, and start polling `GET /analysis-jobs/{job_id}` until completion or failure.
   3. Add manual “Refresh analysis” button to re-trigger POST with `force_refresh=true`.
   4. Surface error states from job polling (e.g., show toast + retry CTA).

6. **Testing & Rollout**
   1. Write unit tests for new models and API flows (cached hit, queueing, job polling, failure cases).
   2. Add integration tests or scripts to simulate job completion (mock queue worker) so frontend behaviour is exercised.
   3. Verify migrations/upgrades in staging; backfill tables with initial “ready” analyses or leave empty for first-run generation.
   4. Monitor queue/job metrics post-deploy; set alerts for repeated `failed` statuses.

7. **Follow-ups**
   - Consider adding WebSocket/SSE later to push completion events instead of polling.
   - Evaluate storing analysis as structured JSON for richer UI rendering down the line.

## Implementation Snapshot (WIP)
- Added `class_analyses`, `student_analyses`, and `analysis_jobs` tables (with Alembic migration `3c0b0a0dcb5d_add_analysis_cache_tables.py`) and SQLAlchemy models for cached summaries and job metadata.
- Refactored `/api/students/class-analysis` and `/api/students/{id}/analysis` to return cached results instantly, queue background jobs via FastAPI `BackgroundTasks`, and expose job state fetching at `/api/students/analysis-jobs/{job_id}`.
- Background processors reuse existing Brain calls to update caches, stamp `computed_at`, and surface failures without blocking API Gateway timeouts.
- Frontend teacher views now show cached text immediately, poll job status, surface “last updated” timestamps, and allow manual refresh with graceful failure messaging.
