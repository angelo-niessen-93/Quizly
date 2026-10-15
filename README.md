# Quizly

Turn YouTube videos into playable quizzes with Django REST Framework, local
Whisper transcription, and Google Gemini. This repository contains only the
backend. The [official Developer Akademie frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly)
is a separate project.

## Quick Start

Run these commands in PowerShell with Python 3.12+ and Git installed.

1. Clone the backend:
   ```powershell
   git clone https://github.com/angelo-niessen-93/Quizly.git
   cd Quizly
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install the standard runtime dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Create the local configuration and generate a private signing key:
   ```powershell
   Copy-Item .env.example .env
   python -c "import secrets; from dotenv import set_key; set_key('.env', 'DJANGO_SECRET_KEY', secrets.token_urlsafe(64))"
   ```
   Edit `.env` and set `GEMINI_API_KEY` for quiz generation. Registration and
   login work without a Gemini key. For the original frontend, keep
   `LOCAL_FRONTEND_CSRF_COMPATIBILITY=true` from the template. This enables
   tokenless requests only from explicitly trusted local frontend origins.
   Keep `DJANGO_DEBUG=true`, `COOKIE_SECURE=false`, and
   `SECURE_SSL_REDIRECT=false` for local HTTP; use `127.0.0.1` for both servers.
   Production must use CSRF tokens and disable this compatibility setting.
5. Apply migrations:
   ```powershell
   python manage.py migrate
   ```
6. Start Django:
   ```powershell
   python manage.py runserver 127.0.0.1:8000
   ```

Keep this terminal open. [The CSRF endpoint](http://127.0.0.1:8000/api/csrf/)
returns JSON; `/api/` itself is not a homepage. These steps assume a fresh clone;
do not overwrite an existing `.env` or regenerate an existing signing key.

On Linux/macOS use `python3 -m venv .venv`, `source .venv/bin/activate`, and
`cp .env.example .env`; the remaining Python commands are the same.
If PowerShell blocks activation, invoke `.\.venv\Scripts\python.exe` directly.

## System prerequisites

- Python 3.12 or newer and Git (`python --version`, `git --version`).
- **FFmpeg and FFprobe** for video processing. On Windows:
  ```powershell
  winget install --id Gyan.FFmpeg -e
  ```
  Open a new terminal after installing and reactivate the virtual environment.
  Verify with `ffmpeg -version` and `ffprobe -version`.
  On Ubuntu/Debian use `sudo apt install ffmpeg`; on macOS use `brew install ffmpeg`.
  If the executables are outside `PATH`, set `FFMPEG_LOCATION` to their directory.
- Internet access and a [Gemini API key](https://aistudio.google.com/api-keys)
  for generation. The first Whisper transcription downloads model weights.

## Run the official frontend

In a second terminal, start from the directory **containing** the backend folder:

```powershell
git clone https://github.com/Developer-Akademie-Backendkurs/project.Quizly.git Quizly-Frontend
python -m http.server 5500 --bind 127.0.0.1 --directory Quizly-Frontend
```

Open **http://127.0.0.1:5500/** and register, then log in. No frontend source
changes or Node.js installation are required. Keep frontend and backend in
separate sibling folders. Do not open pages using `file://`.

The original frontend targets `http://127.0.0.1:8000/api/`. Use `127.0.0.1`
for both servers: `localhost` and `127.0.0.1` are different cookie sites.
Both port-5500 origins are listed in the environment template, but opening the
original frontend on `localhost` while its API uses `127.0.0.1` can prevent
SameSite cookies from accompanying login follow-up requests.

## Configuration

[.env.example](.env.example) is the complete configuration template. Django
loads `.env` beside `manage.py`; exported variables take precedence. Set a private
`DJANGO_SECRET_KEY` and, for generation, `GEMINI_API_KEY`. Never commit `.env`.
No paid OpenAI API or OpenAI key is required; Whisper runs locally.

The template is for local HTTP development. Exact frontend origins include the
scheme and port; allowed hosts contain hostnames only. Restart Django after
configuration changes. See the template for audio, Gemini, cookie, and origin
settings instead of maintaining a second variable reference here.

For an existing local HTTP installation, add
`LOCAL_FRONTEND_CSRF_COMPATIBILITY=true` to `.env` and restart Django to use the
unchanged official frontend. Fresh installations include this setting through
the template. Its security restrictions are described under
[CSRF and browser requests](#csrf-and-browser-requests).

## Usage

Register an account in the frontend, log in, and submit a supported public
YouTube video URL to generate a ten-question quiz. Open quizzes from your
library to play, review answers, or edit their title and description.

The API also supports saving answer selections and replaying quizzes. Clients
must integrate the progress and replay endpoints to persist play across reloads;
the unchanged official frontend does not use those endpoints.

## Architecture

The separate browser frontend communicates with Django REST Framework through
JSON requests and HTTP-only JWT cookies. Django stores users, quiz content, and
answer progress in SQLite and restricts quiz access to the owner.

Quiz generation follows this pipeline:

```text
YouTube URL -> yt-dlp -> FFmpeg -> local Whisper -> Gemini -> validation -> SQLite
```

Whisper transcribes audio locally; only the transcript is sent to Gemini to
generate structured questions. The backend validates ten distinct questions,
four distinct options per question, and one correct answer before saving.
Generation is synchronous, so the request waits for the complete pipeline.

| Directory | Responsibility |
| --- | --- |
| `apps/accounts/` | Users, authentication, cookie sessions, and API CSRF checks |
| `apps/quizzes/` | Quiz models, generation, progress, API views, and tests |
| `quizly/` | Django settings, root URLs, and server entry points |
| `scripts/` | Quality checks and offline provider diagnostics |

## Optional: NVIDIA GPU Acceleration

Whisper supports CPU execution. `WHISPER_DEVICE=auto` selects CUDA when available
and otherwise CPU; set `WHISPER_DEVICE=cpu` to explicitly use CPU. CPU inference
uses full precision and can be substantially slower. A GPU is optional.

NVIDIA acceleration can speed up local transcription. The previously tested
**RTX 5070 Ti** setup used `torch==2.14.1+cu130`; this is hardware-specific,
not part of the standard installation. Users without an NVIDIA GPU should
**not execute NVIDIA-specific installation commands**.

For a compatible NVIDIA GPU, install a suitable driver, use the
[official PyTorch selector](https://pytorch.org/get-started/locally/) to choose a
supported CUDA wheel for your OS/Python/GPU, and install it in the active backend
virtual environment. For the recorded RTX configuration only:

```powershell
python -m pip install --upgrade torch==2.14.1+cu130 --index-url https://download.pytorch.org/whl/cu130
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Set `WHISPER_DEVICE=cuda` only after the check returns `True`, or keep `auto`.
Installing a CUDA toolkit alone does not enable CUDA in CPU-only PyTorch.

## API documentation

Base URL: `http://127.0.0.1:8000/api/`. Keep trailing slashes. JSON bodies use
`Content-Type: application/json`. JWTs are accepted only through cookies, not
through request-body token fields or Bearer headers.

### Endpoint overview

"Access" means a valid access cookie. Every POST, PATCH, and DELETE also needs
valid CSRF protection. Refresh and logout work after access-token expiry.

| Method | Endpoint | Authentication | Purpose / success |
| --- | --- | --- | --- |
| GET | `/api/csrf/` | Public | CSRF cookie and masked token; 200 |
| POST | `/api/register/` | Public + CSRF | Register user; 201 |
| POST | `/api/login/` | Public + CSRF | Set access/refresh cookies; 200 |
| POST | `/api/token/refresh/` | Refresh cookie + CSRF | Rotate session; 200 |
| POST | `/api/logout/` | CSRF; refresh cookie revokes session | Clear JWT cookies; 200 |
| POST | `/api/quizzes/` | Access | Generate and store owned quiz; 201 |
| GET | `/api/quizzes/` | Access | List own quizzes; 200 |
| GET | `/api/quizzes/{id}/` | Access + ownership | Retrieve quiz; 200 |
| PATCH | `/api/quizzes/{id}/` | Access + ownership | Edit title/description; 200 |
| DELETE | `/api/quizzes/{id}/` | Access + ownership | Delete related content; 204, no body |
| GET | `/api/quizzes/{id}/progress/` | Access + ownership | Read attempt and playable answer IDs; 200 |
| PATCH | `/api/quizzes/{id}/progress/` | Access + ownership | Save or replace one selection; 200 |
| POST | `/api/quizzes/{id}/replay/` | Access + ownership | Reset selections, increment attempt; 200 |

### CSRF and browser requests

The unchanged academy frontend does not bootstrap CSRF or send `X-CSRFToken`.
The local template enables `LOCAL_FRONTEND_CSRF_COMPATIBILITY`: API writes without
a token are accepted only from an exact loopback origin listed in **both**
CORS and CSRF allowlists, with DEBUG enabled and an HTTP loopback API host.
Nonempty bodies must be JSON; nonempty forms, missing/null/foreign origins,
and invalid supplied CSRF tokens remain rejected. This applies to registration,
login, refresh, logout, and authenticated quiz writes. JWT authentication and
ownership checks still apply. Django admin keeps normal CSRF enforcement.

Empty request bodies are supported for refresh and logout. The compatibility
option defaults to false and cannot authorize requests when
DEBUG is false, HTTPS is used, or secure cookies are enabled. Production clients
must use the token flow below. Do not use the local template for deployment.

`GET /api/csrf/` has no body and returns HTTP 200:

```json
{"csrfToken": "<masked-csrf-token>"}
```

The bracketed value represents the actual response; it is not a usable token.
The response also establishes a CSRF cookie. Before an unsafe request, fetch this
endpoint with credentials included and send the returned value as `X-CSRFToken`.
For example, from the allowed frontend origin:

```javascript
const api = "http://127.0.0.1:8000/api/";
const bootstrap = await fetch(`${api}csrf/`, { credentials: "include" });
const { csrfToken } = await bootstrap.json();
const response = await fetch(`${api}login/`, {
  method: "POST",
  credentials: "include",
  headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
  body: JSON.stringify({ username: "learner", password: "ExampleOnly!Quiz72z" }),
});
```

All example identities and passwords are fictional; use your own registered
credentials. Login rotates the CSRF secret: obtain a fresh token after login,
or before every subsequent unsafe request.
Never read JWTs from JavaScript or store them in localStorage.

### Registration, login, refresh, and logout

**Register:** `POST /api/register/`

```json
{
  "username": "learner",
  "email": "learner@example.com",
  "password": "ExampleOnly!Quiz72z",
  "confirmed_password": "ExampleOnly!Quiz72z"
}
```

HTTP 201:

```json
{"detail": "User created successfully!"}
```

Registration does not log the user in. Invalid fields, duplicate usernames/emails,
weak passwords, and mismatched confirmation return 400. Django checks minimum
length (eight characters), common/numeric passwords, and similarity to user data.
Backend validation remains authoritative over frontend hints.

**Login:** `POST /api/login/`

```json
{"username": "learner", "password": "ExampleOnly!Quiz72z"}
```

HTTP 200, using the actual user's ID and identity:

```json
{
  "detail": "Login successfully!",
  "user": {"id": 1, "username": "learner", "email": "learner@example.com"}
}
```

Both tokens are set as HTTP-only cookies; neither appears in JSON. Missing
credentials, unknown users, and incorrect passwords return the same generic 401:
`{"detail": "Invalid username or password."}`.

**Refresh:** `POST /api/token/refresh/`, no JSON body required. The refresh cookie
is the input. HTTP 200:

```json
{"detail": "Token refreshed"}
```

Refresh sets a new access cookie and rotates the refresh cookie. The old session
is blacklisted. A missing, expired, or revoked refresh cookie returns 401.

**Logout:** `POST /api/logout/`, no JSON body required. HTTP 200:

```json
{"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."}
```

Logout clears both cookies and blacklists a valid supplied refresh token. It is
idempotent if that token is missing or already invalid. It affects the current
session, not every device. CSRF is still required.

### Generate a quiz

`POST /api/quizzes/`:

```json
{"url": "https://www.youtube.com/watch?v=rb7TVW77ZCs"}
```

The request field is **`url`**; the response/database field is **`video_url`**.
The owner is always the signed-in user. Success is HTTP 201 with the
[quiz response](#quiz-response). Invalid input returns 400, generation failures
return a safe 502, and missing Gemini/audio-tool configuration returns 503.

Supported forms are HTTPS single-video watch, shorts, embed, and youtu.be links
on `youtube.com`, `www.youtube.com`, `m.youtube.com`, and `youtu.be`, as appropriate
for the URL form. URLs are canonicalized. Other hosts, embedded credentials,
explicit ports, fragments, invalid IDs, and standalone playlist URLs are rejected.

Videos must be recorded, have a known duration, and be no longer than 20 minutes.
Downloads are bounded to 100 MiB; the MP3 must be nonempty and below 24 MiB.
A syntactically valid URL does not guarantee that the video is accessible.

### Quiz response

Create, detail GET, and PATCH return the same structure. This **abbreviated
example shows one question**; a real quiz response contains all ten.

```json
{
  "id": 1,
  "title": "The Science of Vaccines",
  "description": "A quiz about the source video's explanation of vaccines.",
  "created_at": "2026-10-15T12:00:00+02:00",
  "updated_at": "2026-10-15T12:00:00+02:00",
  "video_url": "https://www.youtube.com/watch?v=rb7TVW77ZCs",
  "questions": [
    {
      "id": 11,
      "question_title": "In what year did Edward Jenner administer the first vaccine?",
      "question_options": ["1796", "1896", "1756", "1812"],
      "answer": "1796",
      "created_at": "2026-10-15T12:00:00+02:00",
      "updated_at": "2026-10-15T12:00:00+02:00"
    }
  ]
}
```

IDs are integers; timestamps are ISO-8601 strings. `question_options` contains
four strings. `answer` is the correct answer **text**, not an index or ID, and is
included even before completion. Progress uses a separate representation below.

### List, retrieve, edit, and delete

- `GET /api/quizzes/`: HTTP 200 with an unpaginated array of your quiz objects;
  a new empty library returns `[]`. Results are newest first by creation time,
  then ID. Other users' quizzes are excluded.
- `GET /api/quizzes/?period=today`: same response for today's quizzes.
- `GET /api/quizzes/?period=week`: same response for today and the previous six
  calendar days. Date boundaries use `Europe/Berlin`, not a rolling 168-hour range.
  An unsupported `period` value returns 400.
- `GET /api/quizzes/1/`: HTTP 200 with the full quiz object described above.
- `PATCH /api/quizzes/1/`: update either or both editable metadata fields:

```json
{"title": "My revised title", "description": "My revised description"}
```

PATCH returns HTTP 200 with the full quiz object, changed metadata, and a new
`updated_at`. Questions, answers, and progress are preserved. Owner and video URL
are not editable through this endpoint.

`DELETE /api/quizzes/1/` requires no body and deletes the quiz, questions, answers,
progress, and selections. Success is **204 with no response body**; do not parse
JSON from it. For detail and play endpoints, a foreign existing quiz returns 403
and a nonexistent ID returns 404.

### Progress, scoring, and replay

`GET /api/quizzes/1/progress/` requires no body and returns HTTP 200. This is an
abbreviated example containing one of ten playable questions:

```json
{
  "attempt": 1,
  "completed": false,
  "updated_at": "2026-10-15T12:01:00+02:00",
  "selections": [{"question": 11, "answer": 21}],
  "score": null,
  "questions": [
    {
      "id": 11,
      "question": "In what year did Edward Jenner administer the first vaccine?",
      "position": 1,
      "answers": [
        {"id": 21, "text": "1796"},
        {"id": 22, "text": "1896"},
        {"id": 23, "text": "1756"},
        {"id": 24, "text": "1812"}
      ],
      "correct_answer": null
    }
  ]
}
```

`PATCH /api/quizzes/1/progress/` saves one selection using IDs from that response:

```json
{"question": 11, "answer": 21}
```

It returns HTTP 200 with the updated progress object. Another answer for the same
question replaces the selection. Both IDs must belong together and to this quiz;
invalid combinations return 400.

After all ten questions are answered, `completed` is `true`, `score` is the correct
answer percentage from 0 to 100, and each progress question's `correct_answer`
becomes its correct answer ID. Before completion, score and solution IDs are
`null`. Changing a completed answer recalculates the score.

`POST /api/quizzes/1/replay/` has no body and returns HTTP 200 with reset progress:
`attempt` increases, `completed` becomes `false`, `selections` becomes `[]`, and
score/solution IDs return to `null`. It reuses questions without calling Gemini.

### Optional manual creation

POST also accepts `title`, `description`, and `questions`. A complete question
list skips external generation. `url` remains required and validated. The list
must contain ten distinct items using this **input** shape:

```json
{
  "question": "Which number is even?",
  "answers": [
    {"text": "2", "is_correct": true},
    {"text": "3", "is_correct": false},
    {"text": "5", "is_correct": false},
    {"text": "7", "is_correct": false}
  ]
}
```

This one-item example is not a complete create request. Supply ten different
questions, each with four distinct options and exactly one true flag. Text limits
are 200 characters for title, 5000 for description, 1000 for question, and 500 for
answer. Manual creation defaults title to `Quiz` and description to empty.
Success remains HTTP 201 with the same public quiz response.

### Status codes and errors

| Code | Meaning |
| --- | --- |
| 200 / 201 / 204 | Successful read/write, creation, or bodyless deletion as documented above |
| 400 | Invalid registration, quiz content, URL, duration, date filter, or selection |
| 401 | Missing/invalid access authentication, invalid login, or unusable refresh token |
| 403 | Failed CSRF verification or another user's existing quiz |
| 404 | Requested quiz does not exist |
| 405 | Unsupported method, such as PUT on quiz detail |
| 429 | DRF throttling: 60 requests/minute anonymously, 120/minute authenticated |
| 500 | Unexpected internal failure; quiz persistence is transactional |
| 502 | Download, transcription, generation, or generated-content validation failed |
| 503 | Gemini key or FFmpeg/FFprobe configuration unavailable |

Field validation errors generally map field names to message lists. General
errors use `detail`, for example:

```json
{"detail": "Quiz generation failed. Please try again later."}
```

Credentials and raw provider errors are not returned to clients. The application
throttles are not guarantees of Gemini quota or availability.

## Development and Testing

`requirements.txt` contains runtime dependencies and is sufficient to run Quizly.
`requirements-dev.txt` includes that file plus Ruff. Install it only for development:

```powershell
python -m pip install -r requirements-dev.txt
python manage.py test --settings=quizly.test_settings
python manage.py makemigrations --check --dry-run --settings=quizly.test_settings
python -m ruff check apps quizly scripts manage.py
python -m ruff format --check apps quizly scripts manage.py
python scripts/check_quality.py
python -m pip check
python manage.py check
```

Tests use an isolated database and simulated AI providers, with no API key or
model download required. Test settings are for tests only. The custom quality
check requires documented snake_case functions of at most 14 lines.

Security tests enforce CSRF checks and cover trusted local origins, rejected
foreign origins and form bodies, invalid supplied tokens, production guards,
admin protection, cookie authentication, token rotation, and logout revocation.
Provider tests simulate external services; they do not validate a live Gemini
project, YouTube availability, or real model inference.

## Security and deployment

Tokens remain in HTTP-only cookies and are never returned as JSON or accepted
from Authorization headers. Refresh rotates and blacklists the previous session;
logout revokes it. Quizzes require authentication and enforce ownership.

For production set `DJANGO_DEBUG=false`, `COOKIE_SECURE=true`,
`SECURE_SSL_REDIRECT=true`, and `LOCAL_FRONTEND_CSRF_COMPATIBILITY=false`.
Configure real hosts and exact HTTPS CORS/CSRF origins. Use a private signing key,
a production WSGI/ASGI server, static-file hosting, and appropriate proxy settings.
Django's development server is for local use. Check configuration with
`python manage.py check --deploy` under the production environment.
Back up the database and periodically run `python manage.py flushexpiredtokens`.

Use a newly generated private signing key; never reuse a publicly exposed or
historical development key. Settings require an environment key and reject the
`django-insecure-` prefix.

## Limitations and troubleshooting

- Use `127.0.0.1:5500` with the original frontend's `127.0.0.1:8000` API target.
  Mixing `localhost` and `127.0.0.1` breaks the same-site cookie workflow.
- A 403 with `CSRF verification failed.` means the request failed the API's CSRF
  checks. Verify `.env`, exact origins, and restart Django. Production clients
  must bootstrap and send the token. A foreign quiz also returns 403.
- The original frontend treats both 401 and 403 as session-refresh triggers and
  has generic validation errors. Its quiz play does not use the backend's saved
  progress/replay endpoints; those require a separately integrated client.
- Generation is synchronous and can take time, especially on CPU. Gemini keys,
  model access, billing and quotas, and YouTube availability are external
  prerequisites. FFmpeg must be discoverable by the backend process.
- The first Whisper use downloads weights. Temporary audio is cleaned up;
  model weights remain cached. Each server process holds its own loaded model.
- Verify cookies, CORS, and CSRF through the actual HTTPS deployment before
  exposing it to users.

## Credits

Created for Developer Akademie. The separate
[official frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly)
retains its upstream license and attribution. Quizly uses Django, DRF, Simple JWT,
Whisper, PyTorch, FFmpeg, yt-dlp, and the Google GenAI SDK under their licenses.

See also the [Definition of Done](docs/definition-of-done.md).
