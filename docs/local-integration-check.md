# Local integration report

Reviewed: 15 October 2026. This English report consolidates earlier local
integration records and the final backend submission review. Historical real
service/browser results are distinguished from the current offline review.

## Scope and submission

Only the Django backend is submitted. The
[Developer Akademie frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly)
is provided separately and is not a deliverable. Backend and frontend were kept
in separate folders and Git repositories and communicated only through REST.
The browser tests used a **locally adapted** frontend based on upstream commit
ae8e8637e39d328e3b8a55670db77f121deffb49, with credentialed CSRF handling and
progress synchronization. A fresh upstream clone is not the tested adapted copy.
No author-owned frontend repository or publication is required for submission.
The final documentation review does not modify or publish the frontend.

## Successful authorized Gemini run - historical measured evidence

The user authorized one optimized attempt using the project's confirmed Free
Tier. At that time, public pricing listed free standard text input/output and a
read-only model lookup with the existing key confirmed generateContent support.
No billing settings or credentials were changed. Model metadata alone does not
prove the project billing tier. No paid tools or features were requested.

| Check | Actual result |
| --- | --- |
| Input | Existing transcript, 3834 characters, unchanged |
| Transcript SHA-256 | 950ea93ce0671759c9a83c3b8d2c35f2b29d04c89a9dd087f8f65d35c28f3089 |
| Model | gemini-3.8-flash; matching modelVersion in response |
| Configuration | LOW thinking, no thought output, 8192-token cap, requested server deadline 180 seconds, HTTPX phase limits 190 seconds |
| Attempts | Exactly one observed generation request; SDK attempts=1, no continuation, function calling, redirects or fallback |
| Gemini response | HTTP 200 in 13.460 seconds; finishReason STOP |
| Backend POST | HTTP 201 in 14.391 seconds |
| Quiz title | The Science of Vaccines |
| Content | Ten distinct questions, four distinct string options each, one correct answer each |
| Source fidelity | All ten questions and solutions checked against the saved transcript |
| SQLite | Ten questions, forty answers, one is_correct per question, initial progress record |
| Contract | Exact quiz/question fields, integer IDs, ISO timestamps and correct answer text |
| GET | HTTP 200, content matched the POST response |
| Real browser | All ten questions played; UI and backend both reported 100% |
| Autosave/reload | After three selections, reload restored progress and opened question four |
| Persisted result | Ten selections confirmed directly in SQLite |
| Change after completion | First answer changed; persisted score became 90% |
| Replay/reload | attempt=2, completed=false, zero selections; reset persisted after reload |
| Cleanup | Temporary account, tokens and quiz removed after verification |

The temporary test server substituted only the cached transcript for the repeated
audio/Whisper step, as requested. The real SDK request, response validation,
create_quiz/save_quiz logic, SQLite storage, response serializers and browser/API
requests were exercised. The normal server was restored afterward; no production
transcript-cache feature or API contract change was introduced.

Provider usage was 805 prompt tokens, 1128 candidate tokens and 1933 total tokens.
serviceTier=standard indicates the inference class, not the project's billing
tier. No separate thinking-token counter was returned. The successful run does
not isolate how much each optimization or service load affected latency.

Local evidence was archived under ignored .cache/final-gemini-stages.jsonl,
.cache/final-gemini-result.json, .cache/final-gemini-provider-response.json and
.cache/final-gemini-quiz.json. These files are not submission dependencies.
Temporary quiz ID 4 was deleted and is not a persistent demo fixture.

Historical sources: [pricing](https://ai.google.dev/gemini-api/docs/pricing),
[billing](https://ai.google.dev/gemini-api/docs/billing). Future live generation
requires a fresh project/quota check and any required authorization. No new live
AI request was made during this final documentation review.

## Real API results from the successful run

| Endpoint | Result | Scope |
| --- | --- | --- |
| GET /api/csrf/ | 200 | Real requests and browser |
| POST /api/register/ | 201 | Temporary account |
| POST /api/login/ | 200 | HTTP-only access/refresh cookies |
| POST /api/quizzes/ | 201 | Request contained url; cached transcript substituted only for audio processing |
| GET /api/quizzes/{id}/ | 200 | Exact response contract checked |
| GET /api/quizzes/{id}/progress/ | 200 | Restored selections and score |
| PATCH /api/quizzes/{id}/progress/ | 200 | Browser autosave and answer changes |
| POST /api/quizzes/{id}/replay/ | 200 | Server-side reset persisted |

Refresh, logout, CRUD, error codes and permissions are additionally covered by
the backend automated suite described in the DoD mapping.

## Earlier failures and optimization

| Attempt | Actual outcome |
| --- | --- |
| Earlier gemini-2.5-flash | Provider HTTP 404 after 0.84 seconds; backend returned safe 502 after 24.50 seconds including audio processing; no partial quiz |
| Earlier unoptimized gemini-3.8-flash | HTTP 504 DEADLINE_EXCEEDED after 90.14 seconds: "Deadline expired before operation could complete." Backend returned 502 after 112.30 seconds; no partial quiz or retry |
| Final optimized gemini-3.8-flash | HTTP 200 in 13.460 seconds, valid content and successful persistence/browser play |

The 504 was a provider response, not a demonstrated local ReadTimeout. Offline
SDK inspection reproduced the old timeout=90000 setting as both HTTPX 90-second
phase limits and X-Server-Timeout: 90. This was a concrete deadline constraint;
a unique cause of slow provider computation was not established.

| Concern | Optimization / conclusion |
| --- | --- |
| Server deadline | Explicit requested 180 seconds |
| Client timeout | 190 seconds for connect/read/write/pool; not a total wall-clock guarantee |
| Thinking | Explicit low and no thought output, replacing an unspecified level |
| Prompt | Compact instructions, reduced from 310 to 266 characters plus the unchanged transcript |
| Output | 8192 tokens including thinking; concise question content, no explanations |
| JSON | Structured schema from QuizContentSerializer; exactly ten questions and four answers, then semantic validation |
| Hidden follow-up calls | attempts=1 plus continuation, automatic function calling and redirects disabled |
| Provider instability | Neither proved nor excluded by a single 504 |

Nine offline tests use the real Google SDK with HTTPX MockTransport. They cover
serialized LOW/schema/token limits, deadline units, configurable limits, one
attempt on provider/network errors, no redirect or continuation follow-up, and
safe rejection of truncated MAX_TOKENS output. No Google connection is needed.
The offline preparation script uses a dummy key and the ignored saved transcript;
it is optional and has no live mode.

## Audio and local environment - earlier real checks

| Check | Confirmed result |
| --- | --- |
| FFmpeg and FFprobe | 9.0.2, both version commands successful |
| Windows installation | WinGet Gyan.FFmpeg, installer hash verified; PATH and FFMPEG_LOCATION working |
| openai-whisper | 20250625, local small model; no OpenAI API key or paid transcription API |
| PyTorch | 2.14.1+cu130 |
| GPU | RTX 5070 Ti, driver 610.74, compute capability 12.0 |
| CUDA | Runtime 13.0, real matrix multiplication and model placement on cuda:0 verified |
| Model reuse | Two local audio calls: one model-load cache miss, one cache hit |
| Local WAV | Known English sentence recognized correctly twice; second call about 0.44 seconds |
| Spoken YouTube source | rb7TVW77ZCs, approximately 275 seconds |
| Audio processing | MP3 2201132 bytes; download/conversion 3.81 seconds |
| Whisper | 3834-character transcript in 18.33 seconds |
| Cleanup | Temporary audio directory removed after processing |

An earlier music-video smoke test also produced MP3 (213.04 seconds, 1704812
bytes) and a nonempty 1773-character transcript; the clear-speech source above
was used for the final quiz content. The Whisper model is lazy-loaded once per
process; a lock serializes loading and inference. Tests cover CPU fallback,
FP16 selection, caching and recovery after a load failure.

## Configuration and browser progress - earlier real checks

GEMINI_API_KEY was present and loaded by a fresh Django process without exposing
or changing it. The earlier empty-key observation predated key entry; an old
server needed restarting. The actual variable name and dotenv loading were
correct. Exported process variables take precedence over .env.

The current default model is gemini-3.8-flash. Whisper defaults to small/auto;
its cache and all local credentials remain ignored. Local HTTP uses an explicit
Secure=false exception; application defaults remain secure. CORS/CSRF permit the
configured local frontend origin, with credentialed requests and HTTP-only JWTs.

Earlier browser checks used Edge 155.0.4283.45 and Selenium 4.43.0 against real
Django and SQLite. They verified registration/login, immediate autosave without
clicking Next, restored selection after reload, replacement without duplicate
selection rows, percentage results, edits after completion, replay and reset
persistence. Injected save failure 503 caused UI rollback; a later save succeeded.
The adapted frontend serializes writes to avoid reordering. Its nine automated
tests passed in the earlier run. That frontend is not included in this submission
and was not modified during the final backend documentation review.

## Backend submission review and limits

The README now provides a backend-only installation path, API-client verification,
and optional frontend context. The DoD mapping is in English and identifies all
required backend functionality as complete. Ignore rules exclude environment
files, SQLite/database sidecars, caches, virtual environments and temporary files.
Current secret values were not found in tracked files or any inspected Git
history blobs. No database, environment-secret file or generated audio/model
artifact was found among tracked files or historical paths.

One old hardcoded django-insecure development key remains in Git history. It is
not used by current code, its prefix is rejected at startup, and it differs from
the current private key. Any historical deployment using it must rotate that key.
No Git history rewrite or credential change was performed.

The final review completed these checks without live AI calls:

| Current review check | Result |
| --- | --- |
| Complete backend suite | 102 passed in 9.369 seconds |
| Ruff lint and formatting | Passed; 50 Python files already formatted |
| Function size, naming and docstrings | Passed |
| Migration completeness | No changes detected |
| Installed dependencies | pip check passed |
| Secure Django configuration | check --deploy passed with secure process overrides |
| Fresh backend-only database | All migrations and Django checks passed |
| Independent API smoke check | CSRF 200, registration 201, login 200, own quiz list 200; HTTP-only cookies verified |
| Ignore rules | Thirteen path cases checked, including SQLite sidecars and public template exception |
| Tracked/history artifact paths | None found |
| Documentation | English, local links and README section anchors checked |

The independent smoke check used Django's CSRF-enforcing test client in an
isolated backend-only source copy with a new signing key and database, no frontend,
and no Gemini key. It used already installed dependencies; it was not a fresh
operating-system/package installation. The temporary source/database directory
was removed. The frontend's earlier nine tests were not rerun or modified during
this backend-only review.

No backend implementation blocker remains for the backend-only submission.
Production hosting/HTTPS and independently inspected numeric project RPM/TPM/RPD
limits remain operational checks, not missing backend code. No frontend fork is
required. There were no frontend changes, commits or pushes in this review.
