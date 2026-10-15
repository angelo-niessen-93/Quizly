# Quizly Backend

Django-/DRF-Backend für persönliche YouTube-Quizze. Vorhandene Routen
`/api/register/`, `login/`, `logout/`, `token/refresh/` und `quizzes/`
bleiben erhalten; ebenso das Registrierungsfeld `confirmed_password`.
Das ursprüngliche Repository enthielt Platzhalter, keine Frontend-Dateien
und keine weitergehenden Request-/Response-Verträge. Die aktuelle API folgt
dem unten dokumentierten, vom Auftraggeber bereitgestellten Vertrag.

## Einrichtung

Getestet mit Python 3.14, Django 6.1 und SQLite. Python 3.12 oder neuer verwenden.

### Windows / PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Den erzeugten Wert lokal als `DJANGO_SECRET_KEY` in `.env` eintragen.
Eine bereits vorhandene `.env` nicht überschreiben.
Der frühere öffentliche Schlüssel ist aus dem Anwendungscode entfernt.
Er muss auch in bestehenden Deployments ersetzt werden; dadurch werden bisherige
Sessions und JWTs ungültig. Er bleibt in der bisherigen Git-Historie auffindbar.

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Backend: `http://127.0.0.1:8000/api/`, Admin: `http://127.0.0.1:8000/admin/`.
Die Vorlage schaltet ausschließlich für lokale HTTP-Entwicklung Secure-Cookies
und HTTPS-Weiterleitung aus. Sichere Standardeinstellungen gelten ohne diese
expliziten Umgebungswerte.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
# DJANGO_SECRET_KEY in .env eintragen
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Für reine Laufzeitinstallationen genügt `requirements.txt`.
Die initiale Migration verwendet ein eigenes Benutzermodell mit eindeutiger
E-Mail. Eine bereits mit dem alten Standardmodell migrierte Datenbank benötigt
eine gesonderte Datenmigration; vorhandene Datenbanken nicht löschen.

## FFmpeg und YouTube

FFmpeg und FFprobe müssen als ausführbare Programme installiert sein.
Ein Python-Paket namens ffmpeg ersetzt diese Programme nicht.

- Windows: `winget install --id Gyan.FFmpeg -e`, anschließend Terminal neu öffnen.
- Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`.
- macOS mit Homebrew: `brew install ffmpeg`.
- Alternativ ein Paket von [FFmpeg](https://ffmpeg.org/download.html) installieren.

Mit `ffmpeg -version` und `ffprobe -version` prüfen.
Falls die Programme nicht im PATH liegen, `FFMPEG_LOCATION` auf deren gemeinsames
Verzeichnis setzen, beispielsweise `C:/Tools/ffmpeg/bin`.

Die Anwendung akzeptiert HTTPS-Links von youtube.com, www.youtube.com,
m.youtube.com und youtu.be. Watch-, Shorts- und Embed-Links werden auf eine
einzelne Video-ID normalisiert. Zugangsdaten in URLs, Ports, fremde Hosts,
Playlists und ungültige IDs werden zurückgewiesen. Ob ein Video tatsächlich
verfügbar ist, prüft der Download. Private, entfernte, altersbeschränkte und
regional gesperrte Videos können fehlschlagen.

Nur aufgezeichnete Videos mit bekannter Dauer bis 20 Minuten werden verarbeitet.
yt-dlp lädt Audio, FFmpeg erzeugt MP3, Whisper transkribiert und Gemini Flash
erstellt JSON. Pro Download sind eine Dateigrößengrenze von 100 MiB, begrenzte
Wiederholungen und Socket-Timeouts eingestellt; das konvertierte Audio muss
kleiner als 24 MiB sein. Temporäre Dateien werden durch `TemporaryDirectory`
auch bei Ausnahmen entfernt. Audio und Transkript werden nicht dauerhaft gespeichert.

YouTube kann zusätzliche JavaScript-Challenges verlangen. Bei entsprechenden
yt-dlp-Meldungen dessen [aktuelle Voraussetzungen](https://github.com/yt-dlp/yt-dlp#dependencies)
einschließlich JavaScript-Laufzeit beachten und yt-dlp gezielt aktualisieren.
Die Anwendung übernimmt keine Browser-Cookies und umgeht keine Zugriffssperren.

## Lokales Whisper und RTX 5070 Ti

Transkription verwendet ausschließlich
[openai/whisper](https://github.com/openai/whisper) über das Paket
`openai-whisper==20250625`. Ein OpenAI-API-Key und das OpenAI-API-SDK sind
nicht erforderlich; Audio bleibt für die Transkription lokal.

Für die hier geprüfte RTX 5070 Ti wurde in der Backend-.venv installiert:

```powershell
python -m pip install torch==2.14.1+cu130 --index-url https://download.pytorch.org/whl/cu130
python -m pip install -r requirements-dev.txt
```

Die CUDA-Version von PyTorch zuerst installieren; die anschließende Installation
der Projektanforderungen behält diese kompatible Variante bei.
Ohne NVIDIA-GPU genügt die normale Requirements-Installation mit CPU-PyTorch.
Die globale Python-Installation anderer Projekte wird nicht verändert.

Geprüft: NVIDIA-Treiber 610.74, PyTorch 2.14.1+cu130, CUDA-Runtime 13.0,
RTX 5070 Ti mit Compute Capability 12.0 und erfolgreiche GPU-Matrixberechnung.

Whisper verwendet standardmäßig `small` und `WHISPER_DEVICE=auto`.
Auto wählt CUDA bei Verfügbarkeit, andernfalls CPU. Optional lassen sich
`WHISPER_DEVICE=cpu` oder `cuda` ausdrücklich setzen.
Das Modell wird erst beim ersten Transkriptionsauftrag geladen und danach
einmal pro Django-Prozess im Speicher wiederverwendet. Ein Lock verhindert
gleichzeitige doppelte Ladevorgänge und parallele GPU-Transkriptionen.
Bei mehreren Serverprozessen besitzt jeder seinen eigenen Modell-Cache.

Modellgewichte liegen standardmäßig in `.cache/whisper`; der erste Aufruf lädt
`small` herunter. Dieser kostenlose Modelldownload benötigt Internetzugang,
spätere Aufrufe verwenden die vorhandenen Gewichte.
`.cache/` ist von Git ausgeschlossen.
`WHISPER_CACHE_DIR` erlaubt einen anderen Cache-Ordner.

Lokale Datei ohne Gemini-Aufruf transkribieren:

```powershell
python manage.py shell -c "from pathlib import Path; from apps.quizzes.ai import transcribe_audio; print(transcribe_audio(Path('sample.wav')))"
```

Eine kurze, lokal mit Windows-Sprachausgabe erzeugte WAV-Datei wurde auf
`cuda:0` zweimal korrekt erkannt. Der Modell-Cache zeigte danach einen
Ladevorgang und einen Cache-Treffer. Auch der echte YouTube-Download mit
FFmpeg-Konvertierung, FFprobe-Prüfung und lokaler GPU-Transkription wurde getestet.

## Gemini-Konfiguration prüfen

Das einzige benötigte KI-Secret heißt exakt `GEMINI_API_KEY`.
Die Datei `.env` muss im Backend-Ordner neben `manage.py` liegen.
Prozessvariablen haben Vorrang vor Dateiwerten.

Der vorhandene Key wurde nicht verändert. Ein frischer Django-Prozess erkennt
ihn als gesetzt. Der vorherige Leermeldungs-Befund stammt aus der Prüfung vor
dem Eintragen des Keys; der damals laufende Server mit `--noreload` hatte
die neue Konfiguration noch nicht geladen. Nach Änderungen an `.env`
den Django-Prozess neu starten.

Prüfung ohne Schlüssel-Ausgabe oder API-Aufruf:

```powershell
python manage.py shell -c "from django.conf import settings; print('Gemini configured:', bool(settings.GEMINI_API_KEY.strip()))"
```

Die lokale Konfiguration ist bereit. Gültigkeit, Konto-/Modellberechtigung und
der vollständige Gemini-Aufruf wurden ohne Kostenfreigabe nicht online geprüft.

## Umgebungsvariablen

`.env` wird lokal geladen; bereits gesetzte Prozessvariablen haben Vorrang.
Die Datei ist von Git ausgeschlossen. `.env.example` enthält keine Zugangsdaten.

| Variable | Bedeutung / Standard ohne .env |
| --- | --- |
| `DJANGO_SECRET_KEY` | Pflicht: eigener zufälliger Schlüssel; kein öffentlicher Django-Entwicklungsschlüssel |
| `DJANGO_DEBUG` | `false`; nur lokal `true` |
| `DJANGO_ALLOWED_HOSTS` | Kommagetrennt; `localhost,127.0.0.1` |
| `COOKIE_SECURE` | `true`; nur für lokale HTTP-Entwicklung `false` |
| `COOKIE_SAMESITE` | `Lax`; bei tatsächlich siteübergreifenden Clients `None` mit HTTPS |
| `SECURE_SSL_REDIRECT` | `true`; lokal mit HTTP `false` |
| `CSRF_TRUSTED_ORIGINS` | Explizite Frontend-Ursprünge mit Schema und Port; standardmäßig leer |
| `CORS_ALLOWED_ORIGINS` | Explizite Frontend-Ursprünge; standardmäßig leer |
| `GEMINI_API_KEY` | Eigener Gemini-API-Key; standardmäßig leer |
| `GEMINI_MODEL` | `gemini-2.5-flash`; verfügbares Flash-Modell im eigenen Konto prüfen |
| `WHISPER_MODEL` | `small`, lokales Whisper-Modell |
| `WHISPER_DEVICE` | `auto`, alternativ `cuda` oder `cpu` |
| `WHISPER_CACHE_DIR` | Optionaler Cache-Ordner; Standard `.cache/whisper` |
| `FFMPEG_LOCATION` | Optionaler Pfad zum Verzeichnis mit FFmpeg und FFprobe |

Der Gemini-Key muss vom Betreiber eingerichtet werden. Whisper benötigt keinen API-Key. Es wurden keine erfundenen
Zugangsdaten und keine kostenpflichtigen Live-Anfragen verwendet.
Ohne Keys oder Audio-Werkzeuge liefert automatische Generierung HTTP 503;
Registrierung, Login, Verwaltung und manuell erstellte Quizze funktionieren unabhängig.

## Browser-Anbindung und CSRF

JWTs stehen ausschließlich in den HTTP-only-Cookies `access_token` und
`refresh_token`, Pfad `/api/`. JSON enthält keine Tokens.
Authorization-Header und Tokens im Request-Body werden nicht als Anmeldung
verwendet. Access gilt 15 Minuten, Refresh sieben Tage.

Vor dem ersten schreibenden Request `GET /api/csrf/` aufrufen.
Der zurückgegebene `csrfToken` wird als `X-CSRFToken` gesendet.
Alle Requests benötigen `credentials: 'include'`. Nach Login erneut
`GET /api/csrf/` aufrufen, weil Login das CSRF-Geheimnis rotiert.
Das CSRF-Cookie ist absichtlich nicht HTTP-only; es ist kein JWT.

```javascript
const api = 'http://127.0.0.1:8000/api';
const csrfResponse = await fetch(api + '/csrf/', { credentials: 'include' });
const { csrfToken } = await csrfResponse.json();
const response = await fetch(api + '/login/', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
  body: JSON.stringify({ username: 'alice', password: 'eigenes-passwort' })
});
// Nach erfolgreichem Login CSRF-Token erneut über GET /csrf/ beziehen.
```

Frontend und Backend lokal konsistent über localhost oder über 127.0.0.1
ansprechen. Für getrennte Ports beide Origin-Listen passend setzen.
Keine Wildcard-CORS-Freigabe verwenden.

Refresh rotiert beide JWTs und sperrt die alte Sitzung. Auch deren Access-Token
wird ungültig. Der Client sollte gleichzeitige Refresh-Aufrufe zusammenfassen.
Logout sperrt die Sitzung und entfernt Cookies; er funktioniert auch nach Ablauf
des Access-Tokens. Der Server prüft die Blacklist bei geschützten Requests.
Ein Logout betrifft die aktuelle Sitzung, nicht andere Geräte.

## API

Die folgenden Verträge entsprechen dem vom Auftraggeber bereitgestellten
Auszug der offiziellen Developer-Akademie-Dokumentation. Alle URLs haben
einen abschließenden Slash. Schreibende Requests verwenden JSON.
JWTs werden ausschließlich als Cookies übertragen.

| Methode | Pfad unter /api/ | Erfolg / Response |
| --- | --- | --- |
| POST | `register/` | 201, ausschließlich `detail` |
| POST | `login/` | 200, `detail` und `user`; beide JWT-Cookies |
| POST | `logout/` | 200, ausschließlich `detail`; Cookies löschen und Sitzung sperren |
| POST | `token/refresh/` | 200, ausschließlich `detail`; Access-Cookie erneuern |
| POST | `quizzes/` | 201, generiertes Quiz |
| GET | `quizzes/` | 200, JSON-Array aller eigenen Quizze |
| GET | `quizzes/{id}/` | 200, einzelnes eigenes Quiz |
| PATCH | `quizzes/{id}/` | 200, aktualisiertes Quiz |
| DELETE | `quizzes/{id}/` | 204, vollständig leerer Response-Body |

Die vorhandenen Erweiterungen bleiben zusätzlich verfügbar:

| Methode | Pfad unter /api/ | Zweck |
| --- | --- | --- |
| GET | `csrf/` | CSRF-Cookie und `{"csrfToken": "..."}` |
| GET | `quizzes/?period=today` | Heute erstellte eigene Quizze |
| GET | `quizzes/?period=week` | Heute und vorherige sechs Kalendertage |
| GET | `quizzes/{id}/progress/` | Gespeicherter Versuch mit spielbaren Frage-/Antwort-IDs |
| PATCH | `quizzes/{id}/progress/` | Einzelne Antwort speichern oder ersetzen |
| POST | `quizzes/{id}/replay/` | Antworten zurücksetzen und Versuchszähler erhöhen |

Nur CSRF und die Authentifizierungsrouten sind ohne bestehende Anmeldung
erreichbar. CSRF-Schutz gilt auch dort für Schreibzugriffe.
Datumsfilter verwenden Europe/Berlin einschließlich beider Datumsgrenzen.
Listen sind nach Erstellungszeit und ID absteigend sortiert.
Eigentümer werden ausschließlich aus der Anmeldung gesetzt.
Fremde bestehende Quiz-IDs liefern 403, nicht vorhandene IDs 404.

### Registrierung, Login, Refresh und Logout

Registrierungsrequest:

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "eigenes-starkes-passwort",
  "confirmed_password": "eigenes-starkes-passwort"
}
```

Erfolg: HTTP 201 mit exakt:

```json
{"detail": "User created successfully!"}
```

Username, E-Mail-Format, Passwortbestätigung und Django-Passwortregeln werden
geprüft. E-Mails sind auch auf Datenbankebene ohne Beachtung der Großschreibung
eindeutig. Passwörter werden gehasht.

Loginrequest: `{"username": "alice", "password": "..."}`.
Erfolg: HTTP 200 mit exakt dieser Struktur:

```json
{
  "detail": "Login successfully!",
  "user": {"id": 1, "username": "alice", "email": "alice@example.com"}
}
```

Login setzt `access_token` und `refresh_token` als HTTP-only-Cookies.
Die ID gehört zum tatsächlich angemeldeten Benutzer.
Fehlendes Konto, falsches Passwort sowie fehlende oder leere Zugangsdaten
erzeugen dieselbe generische Fehlermeldung und HTTP 401.

Refresh und Logout benötigen keinen JSON-Body; der Refresh-Token wird
ausschließlich aus dem Cookie gelesen. Die Erfolgsantworten lauten exakt:

```json
{"detail": "Token refreshed"}
```

```json
{"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."}
```

Refresh erneuert den Access-Cookie und rotiert zusätzlich den Refresh-Cookie.
Logout entfernt beide Cookies und sperrt die bestehende Sitzung serverseitig,
einschließlich kopierter Access- und Refresh-Tokens.

### Quiz erstellen und bearbeiten

Der dokumentierte Erstellungsrequest lautet:

```json
{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
```

Das Request-Feld heißt ausschließlich `url`. In Datenbank und Response heißt
das Feld `video_url`. Anfragen mit ausschließlich `video_url` oder dem früheren
`youtube_url` ersetzen das Pflichtfeld `url` nicht und liefern HTTP 400.

Die Erstellung validiert und normalisiert die YouTube-URL, transkribiert das
Audio und generiert genau zehn Fragen mit jeweils vier Optionen.
Der Aufruf arbeitet synchron und kann wegen Download und KI länger dauern.
Bei einem Fehler wird kein unvollständiges Quiz gespeichert.

Quiz-Responses von POST, GET-Liste, GET-Detail und PATCH verwenden exakt:

```json
{
  "id": 1,
  "title": "Quiz Title",
  "description": "Quiz Description",
  "created_at": "2026-10-15T12:34:56.789Z",
  "updated_at": "2026-10-15T12:34:56.789Z",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "questions": [
    {
      "id": 1,
      "question_title": "Question 1",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A",
      "created_at": "2026-10-15T12:34:56.789Z",
      "updated_at": "2026-10-15T12:34:56.789Z"
    }
  ]
}
```

Das Beispiel kürzt die Fragenliste auf ein Element. Ein vollständiges Quiz
enthält genau zehn Fragen. `id` ist jeweils ein Integer, `question_options`
ist ein Array mit vier Strings und `answer` der korrekte Antworttext.
Datumswerte sind ISO-8601-Strings mit Zeitzone; auch ein UTC-Offset wie
`+02:00` ist gültig. `answer` ist gemäß Vertrag bereits vor Spielabschluss
vorhanden. Fortschrittsfelder sind nicht Teil dieser Quiz-Responses.

PATCH akzeptiert `title` und/oder `description`, beispielsweise:

```json
{"title": "Neuer Titel", "description": "Neue Beschreibung"}
```

Dabei bleibt `created_at` erhalten und `updated_at` wird aktualisiert.
Fragen und ihre Zeitstempel werden durch eine reine Metadatenänderung nicht
verändert. DELETE entfernt Quiz, Fragen, Antworten und Fortschritt.

### Vorhandene manuelle Erstellung

Als bestehende Erweiterung akzeptiert POST optional `title`, `description`
und `questions`. Ohne `questions` wird regulär über die KI generiert.
Mit `questions` kann ein vollständiger Inhalt ohne externe Dienste gespeichert
werden; das Pflichtfeld `url` bleibt erforderlich.

Ein Element der manuellen Fragenliste verwendet weiterhin das interne
Eingabeformat; die Liste muss genau zehn unterschiedliche Fragen enthalten:

```json
{
  "question": "Welche Farbe hat ein klarer Tageshimmel?",
  "answers": [
    {"text": "Blau", "is_correct": true},
    {"text": "Grün", "is_correct": false},
    {"text": "Rot", "is_correct": false},
    {"text": "Schwarz", "is_correct": false}
  ]
}
```

Jede Frage benötigt vier unterschiedliche Antworttexte und genau eine korrekte
Lösung. Dieselben Regeln gelten für KI-Antworten. Maximale Textlängen:
Titel 200, Beschreibung 5000, Frage 1000, Antwort 500 Zeichen.
Ohne Titel wird bei manueller Erstellung `Quiz` verwendet.
Auch diese Erweiterung liefert die oben beschriebene Quiz-Response.

### Spielen und auswerten

`GET /api/quizzes/{id}/progress/` liefert weiterhin `attempt`, `completed`,
`updated_at`, `selections` und `score`. Zusätzlich enthält `questions`
die spielbare Darstellung mit `id`, `question`, `position`, `answers`
und `correct_answer`. Die dortigen Antworten enthalten `id` und `text`.
Damit stehen weiterhin alle IDs zum Speichern und Ändern einer Auswahl bereit.

Eine Auswahl speichern:

```http
PATCH /api/quizzes/1/progress/
Content-Type: application/json

{"question": 12, "answer": 47}
```

Erneutes Senden für dieselbe Frage ersetzt die Auswahl.
Frage und Antwort müssen zum eigenen Quiz und zueinander gehören.
Fortschritt wird mit jeder Auswahl atomar gespeichert; nach zehn beantworteten
Fragen wird `completed` wahr. `selections` enthält Frage-/Antwort-IDs.

Im Fortschritts-Endpunkt sind `score` und `correct_answer` vor Abschluss null.
Danach ist `score` die Prozentzahl 0–100 und `correct_answer` die korrekte
Antwort-ID je Frage. Änderungen aktualisieren die Bewertung.
Replay löscht die Auswahlen, erhöht den Versuchszähler und setzt die
Fortschrittsauswertung zurück. Der dokumentierte Quiz-Response enthält seinen
korrekten Antworttext weiterhin unabhängig vom Spielstand.
Gespeichert wird der aktuelle Versuch; eine Versuchshistorie ist nicht vorgesehen.

### Fehlercodes

- 400: Ungültige Registrierungs-/Quizdaten, YouTube-URL oder Videodauer.
- 401: Fehlende oder ungültige Anmeldung, falsche Login-Daten,
  abgelaufener Token oder gesperrte Sitzung.
- 403: Zugriff auf ein fremdes bestehendes Quiz oder fehlgeschlagene CSRF-Prüfung.
- 404: Quiz existiert nicht.
- 429: Ratenbegrenzung, anonym 60/Minute und angemeldet 120/Minute.
- 500: Tatsächlicher interner Serverfehler, beispielsweise ein unerwarteter
  Fehler bei der Datenbankspeicherung; teilweise Daten werden zurückgerollt.
- 502: Fehler beim Download, der Transkription oder KI-Generierung.
- 503: Gemini-Konfiguration oder FFmpeg/FFprobe fehlen.

Die bestehenden 429/502/503-Fälle bleiben als zusätzliche Betriebsfälle erhalten.
Externe Fehler werden nicht als interne 500-Fehler ausgegeben.
Validierungsfehler sind feldbezogene JSON-Objekte; allgemeine Fehler einschließlich
ungültiger Login-Daten verwenden `detail`.
Authentifizierte Schreibzugriffe benötigen zusätzlich gültigen CSRF-Schutz.

### Aktualisierung einer bestehenden Installation

```powershell
python manage.py migrate
```

Migration `0002_api_contract_fields` benennt `youtube_url` datenbewahrend in
`video_url` um und ergänzt `Quiz.updated_at` sowie beide Fragenzeitstempel.
Fragen, Antworten und Fortschrittsverknüpfungen bleiben erhalten.
Neue Zeitstempel bestehender Einträge werden beim Migrieren initialisiert;
historische Fragezeitstempel wurden zuvor nicht erfasst.
Ein automatisierter Migrationstest prüft zehn vorhandene Fragen, ihre Antworten
und gespeicherte Auswahlen.

## Admin

Mit `createsuperuser` einen Administrator einrichten.
Quizliste mit Nutzer-/Titelsuche, Datumsfilter und Links zu einzelnen Fragen.
Titel und Beschreibung können bearbeitet und vollständige Quizze gelöscht werden.
Einzelne Fragen lassen sich separat bearbeiten, einschließlich Antworttexten
und korrekter Lösung. Die Antwortvalidierung gilt auch im Admin.

Neue Quizze entstehen über die validierte API. Einzelne Fragen können im Admin
nicht hinzugefügt oder gelöscht werden, damit zehn Fragen und vier Antworten
erhalten bleiben. Administratoren haben bewusst Zugriff auf alle Quizze.
Benutzerkonten werden über das normale Django-UserAdmin verwaltet.

## Tests und Qualität

```powershell
python manage.py test --settings=quizly.test_settings
python manage.py makemigrations --check --dry-run --settings=quizly.test_settings
python scripts/check_quality.py
ruff check .
ruff format --check .
python -m pip check
```

Tests verwenden eine temporäre Datenbank, einen ausschließlich für Tests
vorgesehenen Schlüssel und einen schnellen Passwort-Hasher.
`quizly.test_settings` niemals für Entwicklung oder Produktion verwenden.
Externe Dienste sind in Tests simuliert; es werden keine echten Kosten erzeugt.

Die 91 automatisierten Backend-Tests decken Registrierung, doppelte E-Mails, Passwortvalidierung,
Cookie-Flags, Login, Token-Rotation, Logout/Blacklist, CSRF, Berechtigungen,
CRUD, Datumsauswahl, Fortschritt, Antwortänderung, Bewertung, Wiederholung,
Admin-Bearbeitung, URL-Validierung, KI-Schema, Rollback und Dateibereinigung ab.
Zusätzliche Vertragstests prüfen exakte Responses, Datentypen und Statuscodes;
ein Migrationstest prüft den Erhalt vorhandener Inhalte und Fortschritte.
Der AST-Check erzwingt für alle Projektfunktionen einschließlich Tests
maximal 14 physische Zeilen ab der def-Zeile, snake_case und Docstrings.
Djangos Test-Lifecycle wird über `setUp = setup_test` angebunden.

## Deployment

Eigene Secrets, Domainnamen und HTTPS konfigurieren:
`DJANGO_DEBUG=false`, `COOKIE_SECURE=true`, `SECURE_SSL_REDIRECT=true`.
Frontend-Ursprünge explizit in CORS und CSRF eintragen.
HSTS ist außerhalb des Debug-Modus aktiv.
Bei einem Reverse Proxy die HTTPS-Erkennung passend zur vertrauenswürdigen
Proxy-Konfiguration einrichten; beliebige Forwarded-Header nicht vertrauen.

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py flushexpiredtokens
```

`flushexpiredtokens` regelmäßig, beispielsweise täglich, ausführen.
Statische Dateien durch den Webserver bereitstellen und einen geeigneten
WSGI-/ASGI-Server einsetzen. SQLite ist für die lokale Abgabe eingerichtet;
bei parallelem Produktionsbetrieb eine Datenbank mit Zeilensperren und einen
gemeinsamen Cache für Ratenbegrenzungen konfigurieren. Der eingebaute
Entwicklungsserver ist kein Produktionsserver.

## Abnahmestatus und Quellen

Die vollständige Zuordnung aller DoD-Punkte mit offenen externen Prüfungen steht
in [docs/definition-of-done.md](docs/definition-of-done.md).
Der echte YouTube -> FFmpeg -> Whisper -> Gemini-Durchlauf bleibt offen.
Das offizielle Frontend liegt separat in D:\DEVAkademie\Projekte\Quizly-Frontend
und wurde gemeinsam mit diesem Backend lokal im Browser geprüft.
Das Frontend synchronisiert Antworten, Wiederaufnahme und Replay jetzt mit dem Backend.

Verwendete offizielle Schnittstellendokumentation:
[Lokales OpenAI Whisper](https://github.com/openai/whisper),
[Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output),
[yt-dlp](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp),
[Simple JWT Blacklist und Rotation](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/settings.html).


## Lokale Integration mit dem getrennten offiziellen Frontend

Backend: D:\DEVAkademie\Projekte\Quizly, Port 8000.
Frontend: D:\DEVAkademie\Projekte\Quizly-Frontend, Port 5500.
Beide Projekte besitzen eigene Git-Repositories und kommunizieren nur per REST.
Die Frontend-Base-URL ist http://127.0.0.1:8000/api/.
Die minimale CSRF-Anpassung befindet sich im separaten Frontend in shared/js/auth.js.

Frontend aus dessen eigenem Verzeichnis starten:

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

Anschließend http://127.0.0.1:5500/ öffnen. Backend und Frontend konsistent
über 127.0.0.1 ansprechen. Die vorhandene lokale .env erlaubt diesen Origin.
Den vollständigen Prüfbericht mit Paketversionen, tatsächlichen Browser-/HTTP-
Ergebnissen, Secret-Status ohne Werte und allen Blockern findest du in
[docs/local-integration-check.md](docs/local-integration-check.md).

Der echte YouTube-Audiodownload, FFmpeg, FFprobe und lokales GPU-Whisper sind
geprüft. Gemini ist lokal konfiguriert; ein echter Generierungsaufruf wartet
auf ausdrückliche Kostenfreigabe. Keine kostenpflichtigen APIs wurden aufgerufen.
Die manuelle Quiz-Erstellung und Speicherung sowie die Frontend-Synchronisierung
von Auswahlen, Reload, Antwortänderung und Replay wurden real geprüft.

Frontend-Regressionen im getrennten Frontend-Ordner ausführen:

```powershell
node --test tests/progress.test.cjs
```

Die neun Tests benötigen keine zusätzlichen Node-Pakete.
