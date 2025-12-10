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
