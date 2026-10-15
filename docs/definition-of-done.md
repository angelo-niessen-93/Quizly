# Definition of Done - Backend submission review

Reviewed: 15 October 2026. **Done** means implemented and verified locally.
All required backend items below are done. External deployment checks are listed
separately and are not requirements for this backend submission.

## Submission scope

Only this Django backend is submitted to Developer Akademie. The
[official frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly)
is supplied by Developer Akademie and is not part of the submission. The two
applications communicate exclusively through the REST API. Browser integration
was verified with a locally adapted frontend, kept outside this repository.
No frontend fork, author-owned frontend repository, or frontend publication is
required. Backend setup and automated tests work independently of the frontend.

## 1. Authentication

| Requirement | Status | Evidence |
| --- | --- | --- |
| Username, email, password and confirmation registration | Done | Registration serializer and API tests |
| Validation, including duplicate email addresses | Done | Django password validators and case-insensitive database uniqueness |
| Login with access and refresh JWTs | Done | Cookie login and exact response contract tests |
| Both tokens exclusively in secure HTTP-only cookies | Done | HttpOnly, Secure and SameSite tests; Secure defaults to true, local HTTP exception documented |
| Refresh, logout and blacklist | Done | Rotation, reuse prevention, access-session revocation and cookie deletion tests |
| Protected endpoints and safe errors | Done | Default authenticated access, ownership checks and generic authentication/provider errors |

## 2. Quiz system

| Requirement | Status | Evidence |
| --- | --- | --- |
| Quiz, question, answer and progress models | Done | Models, migrations and persistence tests |
| Create, retrieve, update and delete REST API | Done | CRUD and exact contract tests |
| Assign quizzes to the authenticated user | Done | Server-assigned owner, own-only lists, foreign-object 403 and missing-object 404 |
| Today and last-seven-days overview | Done | period=today/week and local calendar-boundary tests |
| Edit title and description | Done | PATCH and admin validation |
| Store the YouTube URL | Done | Validated video_url storage and migration preservation |
| Ten questions with four options each | Done | Schema, content validation, admin safeguards and real generation evidence |
| Automatically save progress | Done | Atomic selection endpoint; earlier browser autosave and SQLite checks |
| Change previous answers | Done | Selection replacement, reload and post-completion score updates |
| Percentage result and correct solutions | Done | Score tests and browser results; correct answer text included in quiz responses as required |
| Replay quizzes | Done | Reset selections, increment attempt and preserve reset state after reload |

## 3. AI integration

| Requirement | Status | Evidence |
| --- | --- | --- |
| Accept only valid YouTube URLs | Done | HTTPS, allowed host, video ID and URL-component validation before download |
| yt-dlp and FFmpeg audio processing | Done | Earlier real download, MP3 conversion and FFprobe verification |
| OpenAI Whisper transcription | Done | Local openai-whisper small on CUDA, local audio and real YouTube transcription |
| Gemini Flash generation | Done | One authorized optimized gemini-3.8-flash request returned HTTP 200 in 13.460 seconds |
| Validate and store questions and correct answers | Done | Ten distinct questions, forty options, one solution each; real SQLite and API checks |
| Reliable temporary-file cleanup | Done | Success and failure-path tests; real temporary-directory removal |
| Environment-based API credentials | Done | Empty public template, no OpenAI API key, safe failure when Gemini is unconfigured |

## 4. Code quality

| Requirement | Status | Evidence |
| --- | --- | --- |
| Functions have at most 14 physical lines | Done | AST check, including tests |
| Each function has one responsibility | Done | Separate validation, storage, token, transcription and provider helpers reviewed |
| Python functions use snake_case | Done | AST naming check |
| Helper logic separated into services/functions/utils | Done | Auth and quiz services plus dedicated validation, generation and transcription modules |
| PEP-8 | Done | Ruff E/F/W/I, 79-character lines and formatting check |
| Meaningful docstrings | Done | Source review and AST docstring check |
| Remove unused and commented-out code | Done | Source review and unused-code lint checks |
| Admin for quizzes and individual questions | Done | Search/filter, metadata and question/answer editing with regression tests |

## 5. Security and documentation

| Requirement | Status | Evidence |
| --- | --- | --- |
| Replace exposed Django key and load from environment | Done | No built-in application key; startup rejects missing or django-insecure-prefixed keys |
| Configurable DEBUG | Done | DJANGO_DEBUG, false by default |
| Secure cookies and CSRF protection | Done | Cookie flags, CSRF on all unsafe API methods, explicit credentialed CORS origins |
| Complete README: setup, API, environment and FFmpeg | Done | English backend-only setup and API guide; optional frontend context clearly separated |
| Automated registration, login, logout, permissions and quiz tests | Done | 102 backend tests, including contracts, provider transport, admin and migrations |
| Exclude local secrets, databases and artifacts | Done | Tracked-file/history audit, ignore-rule checks and expanded SQLite sidecar coverage |

## API contract verification

The contract source is the user's supplied official Developer Akademie endpoint
specification and complete JSON example. Automated generation tests simulate
providers; the earlier authorized real generation also verified POST and GET.

| Endpoint | Verified result | Deviation |
| --- | --- | --- |
| POST /api/register/ | 201, exactly {"detail":"User created successfully!"} | None |
| POST /api/login/ | 200, exact detail/user response and HTTP-only token cookies | None; invalid credentials return 401 |
| POST /api/logout/ | 200, exact prescribed detail, both cookies removed, session revoked | None |
| POST /api/token/refresh/ | 200, exactly {"detail":"Token refreshed"}, new access cookie | None; refresh rotation retained |
| POST /api/quizzes/ | 201, request field url, ten questions and four string options each | None |
| GET /api/quizzes/ | 200, array containing only owned quizzes | None |
| GET /api/quizzes/{id}/ | 200, exact quiz field set | None |
| PATCH /api/quizzes/{id}/ | 200, title/description and updated_at updated | None |
| DELETE /api/quizzes/{id}/ | 204, empty body and cascading deletion | None |
| GET /api/csrf/ | 200, csrfToken and cookie | Existing supporting endpoint |
| GET /api/quizzes/{id}/progress/ | 200, saved selections, score and playable answer IDs | Existing extension preserved |
| PATCH /api/quizzes/{id}/progress/ | 200, save/replace selection and update score | Existing extension preserved |
| POST /api/quizzes/{id}/replay/ | 200, clear selections and increment attempt | Existing extension preserved |

Quiz fields: id, title, description, created_at, updated_at, video_url, questions.
Question fields: id, question_title, question_options, answer, created_at,
updated_at. question_options contains exactly four strings; answer is the correct
answer text. IDs are integers and timestamps are ISO-8601 strings.

Tests cover 400 invalid input, 401 unauthenticated/invalid credentials, 403 foreign
quizzes, 404 missing quizzes, and rollback on unexpected internal storage errors.
Operational 429, 502 and 503 responses are documented. Migration 0002 preserves
existing quizzes, questions, answers, progress and selections while updating the
contract fields.

## Final backend review results

- All 102 backend tests passed again in 9.369 seconds, without live AI calls.
- Ruff lint/format, function AST checks, pip check and migration checks passed.
- Secure Django check --deploy passed with secure process overrides.
- A backend-only source copy migrated a fresh database, passed Django checks,
  and verified CSRF, registration, login, HTTP-only cookies and own-quiz listing
  without a frontend or Gemini key. Temporary files were removed afterward.
- Ignore rules passed thirteen path checks; no tracked file matches ignore rules.
- English documentation, local links and README section anchors were checked.

## Evidence boundaries and remaining operational checks

- The 102 backend tests do not require a frontend, live AI calls, or API keys.
- Nine tests and real Edge browser checks passed in the earlier **locally adapted
  frontend**. This is supporting evidence, not a frontend submission requirement.
- The final real Gemini test reused the 3834-character transcript. Audio download
  and local CUDA transcription were verified separately in earlier real runs.
- The user confirmed the Gemini project's Free Tier. Public model pricing was
  checked during that run; model metadata is not independent billing evidence.
  Numeric project RPM/TPM/RPD limits were not independently inspected.
- Production hosting, real HTTPS and target-host configuration are not certified
  by local checks. They do not block the requested backend-only submission.
- One obsolete hardcoded Django development key remains in old Git history.
  The application no longer uses it, rejects that insecure prefix, and the current
  configured credentials were not found in tracked files or Git history. Any old
  deployment using the historical key must rotate it. History was not rewritten.

See [the integration report](local-integration-check.md) for measured results and
[the README](../README.md) for independent backend installation instructions.
