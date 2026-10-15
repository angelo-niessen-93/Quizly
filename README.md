# Quizly Backend

Django-/DRF-Backend f?r pers?nliche YouTube-Quizze. Vorhandene Routen
`/api/register/`, `login/`, `logout/`, `token/refresh/` und `quizzes/`
bleiben erhalten; ebenso das Registrierungsfeld `confirmed_password`.
Das urspr?ngliche Repository enthielt Platzhalter, keine Frontend-Dateien
und keine weitergehenden Request-/Response-Vertr?ge.

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
Eine bereits vorhandene `.env` nicht ?berschreiben.
Der fr?here ?ffentliche Schl?ssel ist aus dem Anwendungscode entfernt.
Er muss auch in bestehenden Deployments ersetzt werden; dadurch werden bisherige
Sessions und JWTs ung?ltig. Er bleibt in der bisherigen Git-Historie auffindbar.

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Backend: `http://127.0.0.1:8000/api/`, Admin: `http://127.0.0.1:8000/admin/`.
Die Vorlage schaltet ausschlie?lich f?r lokale HTTP-Entwicklung Secure-Cookies
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

F?r reine Laufzeitinstallationen gen?gt `requirements.txt`.
Die initiale Migration verwendet ein eigenes Benutzermodell mit eindeutiger
E-Mail. Eine bereits mit dem alten Standardmodell migrierte Datenbank ben?tigt
eine gesonderte Datenmigration; vorhandene Datenbanken nicht l?schen.

## FFmpeg und YouTube

FFmpeg und FFprobe m?ssen als ausf?hrbare Programme installiert sein.
Ein Python-Paket namens ffmpeg ersetzt diese Programme nicht.

- Windows: `winget install --id Gyan.FFmpeg -e`, anschlie?end Terminal neu ?ffnen.
- Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`.
- macOS mit Homebrew: `brew install ffmpeg`.
- Alternativ ein Paket von [FFmpeg](https://ffmpeg.org/download.html) installieren.

Mit `ffmpeg -version` und `ffprobe -version` pr?fen.
Falls die Programme nicht im PATH liegen, `FFMPEG_LOCATION` auf deren gemeinsames
Verzeichnis setzen, beispielsweise `C:/Tools/ffmpeg/bin`.

Die Anwendung akzeptiert HTTPS-Links von youtube.com, www.youtube.com,
m.youtube.com und youtu.be. Watch-, Shorts- und Embed-Links werden auf eine
einzelne Video-ID normalisiert. Zugangsdaten in URLs, Ports, fremde Hosts,
Playlists und ung?ltige IDs werden zur?ckgewiesen. Ob ein Video tats?chlich
verf?gbar ist, pr?ft der Download. Private, entfernte, altersbeschr?nkte und
regional gesperrte Videos k?nnen fehlschlagen.

Nur aufgezeichnete Videos mit bekannter Dauer bis 20 Minuten werden verarbeitet.
yt-dlp l?dt Audio, FFmpeg erzeugt MP3, Whisper transkribiert und Gemini Flash
erstellt JSON. Pro Download sind eine Dateigr??engrenze von 100 MiB, begrenzte
Wiederholungen und Socket-Timeouts eingestellt; das konvertierte Audio muss
kleiner als 24 MiB sein. Tempor?re Dateien werden durch `TemporaryDirectory`
auch bei Ausnahmen entfernt. Audio und Transkript werden nicht dauerhaft gespeichert.

YouTube kann zus?tzliche JavaScript-Challenges verlangen. Bei entsprechenden
yt-dlp-Meldungen dessen [aktuelle Voraussetzungen](https://github.com/yt-dlp/yt-dlp#dependencies)
einschlie?lich JavaScript-Laufzeit beachten und yt-dlp gezielt aktualisieren.
Die Anwendung ?bernimmt keine Browser-Cookies und umgeht keine Zugriffssperren.

## Umgebungsvariablen

`.env` wird lokal geladen; bereits gesetzte Prozessvariablen haben Vorrang.
Die Datei ist von Git ausgeschlossen. `.env.example` enth?lt keine Zugangsdaten.

| Variable | Bedeutung / Standard ohne .env |
| --- | --- |
| `DJANGO_SECRET_KEY` | Pflicht: eigener zuf?lliger Schl?ssel; kein ?ffentlicher Django-Entwicklungsschl?ssel |
| `DJANGO_DEBUG` | `false`; nur lokal `true` |
| `DJANGO_ALLOWED_HOSTS` | Kommagetrennt; `localhost,127.0.0.1` |
| `COOKIE_SECURE` | `true`; nur f?r lokale HTTP-Entwicklung `false` |
| `COOKIE_SAMESITE` | `Lax`; bei tats?chlich site?bergreifenden Clients `None` mit HTTPS |
| `SECURE_SSL_REDIRECT` | `true`; lokal mit HTTP `false` |
| `CSRF_TRUSTED_ORIGINS` | Explizite Frontend-Urspr?nge mit Schema und Port; standardm??ig leer |
| `CORS_ALLOWED_ORIGINS` | Explizite Frontend-Urspr?nge; standardm??ig leer |
| `OPENAI_API_KEY` | Eigener OpenAI-API-Key f?r Whisper; standardm??ig leer |
| `GEMINI_API_KEY` | Eigener Gemini-API-Key; standardm??ig leer |
| `GEMINI_MODEL` | `gemini-2.5-flash`; verf?gbares Flash-Modell im eigenen Konto pr?fen |
| `FFMPEG_LOCATION` | Optionaler Pfad zum Verzeichnis mit FFmpeg und FFprobe |

API-Keys m?ssen vom Betreiber eingerichtet werden. Es wurden keine erfundenen
Zugangsdaten und keine kostenpflichtigen Live-Anfragen verwendet.
Ohne Keys oder Audio-Werkzeuge liefert automatische Generierung HTTP 503;
Registrierung, Login, Verwaltung und manuell erstellte Quizze funktionieren unabh?ngig.

## Browser-Anbindung und CSRF

JWTs stehen ausschlie?lich in den HTTP-only-Cookies `access_token` und
`refresh_token`, Pfad `/api/`. JSON enth?lt keine Tokens.
Authorization-Header und Tokens im Request-Body werden nicht als Anmeldung
verwendet. Access gilt 15 Minuten, Refresh sieben Tage.

Vor dem ersten schreibenden Request `GET /api/csrf/` aufrufen.
Der zur?ckgegebene `csrfToken` wird als `X-CSRFToken` gesendet.
Alle Requests ben?tigen `credentials: 'include'`. Nach Login erneut
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
// Nach erfolgreichem Login CSRF-Token erneut ?ber GET /csrf/ beziehen.
```

Frontend und Backend lokal konsistent ?ber localhost oder ?ber 127.0.0.1
ansprechen. F?r getrennte Ports beide Origin-Listen passend setzen.
Keine Wildcard-CORS-Freigabe verwenden.

Refresh rotiert beide JWTs und sperrt die alte Sitzung. Auch deren Access-Token
wird ung?ltig. Der Client sollte gleichzeitige Refresh-Aufrufe zusammenfassen.
Logout sperrt die Sitzung und entfernt Cookies; er funktioniert auch nach Ablauf
des Access-Tokens. Der Server pr?ft die Blacklist bei gesch?tzten Requests.
Ein Logout betrifft die aktuelle Sitzung, nicht andere Ger?te.

## API

Alle URLs haben einen abschlie?enden Slash. Schreibende Requests verwenden JSON.
Nur CSRF, Registrierung, Login, Refresh und Logout sind ohne Anmeldung erreichbar.

| Methode | Pfad unter /api/ | Zweck |
| --- | --- | --- |
| GET | `csrf/` | CSRF-Cookie und `{"csrfToken": "..."}` |
| POST | `register/` | Benutzer anlegen, HTTP 201 |
| POST | `login/` | Cookie-Sitzung, HTTP 200 |
| POST | `token/refresh/` | Refresh-Cookie rotieren, HTTP 200 |
| POST | `logout/` | Sitzung sperren und Cookies entfernen, HTTP 200 |
| GET | `quizzes/` | Eigene Quizze, neueste zuerst |
| GET | `quizzes/?period=today` | Heute erstellte eigene Quizze |
| GET | `quizzes/?period=week` | Heute und vorherige sechs Kalendertage |
| POST | `quizzes/` | Quiz erzeugen oder validierten Inhalt speichern, HTTP 201 |
| GET | `quizzes/{id}/` | Eigenes Quiz mit Fragen und aktuellem Fortschritt |
| PATCH | `quizzes/{id}/` | Titel/Beschreibung bearbeiten |
| DELETE | `quizzes/{id}/` | Quiz mit Fragen und Fortschritt l?schen, HTTP 204 |
| GET | `quizzes/{id}/progress/` | Gespeicherten Versuch fortsetzen |
| PATCH | `quizzes/{id}/progress/` | Einzelne Antwort speichern/ersetzen |
| POST | `quizzes/{id}/replay/` | Antworten zur?cksetzen, Versuchsz?hler erh?hen |

Datumsfilter verwenden Europe/Berlin, inklusive beider Datumsgrenzen.
Die Listenantwort ist ein JSON-Array. Fremde Objekt-IDs liefern HTTP 404.
Eigent?mer werden ausschlie?lich aus der Anmeldung gesetzt.

### Registrierung und Login

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "eigenes-starkes-passwort",
  "confirmed_password": "eigenes-starkes-passwort"
}
```

Registrierung liefert `id`, `username` und `email`.
Username, E-Mail-Format, Passwortbest?tigung und Django-Passwortregeln werden
gepr?ft. E-Mails sind auch auf Datenbankebene ohne Beachtung der Gro?schreibung
eindeutig. Passw?rter werden gehasht.

Login verwendet `{"username": "alice", "password": "..."}`.
Er liefert `{"user": {"id": 1, "username": "alice", "email": "alice@example.com"}}`
sowie beide Cookies. Fehlendes Konto und falsches Passwort erzeugen denselben
Fehler. Refresh und Logout brauchen keinen JSON-Body.

### Quiz erstellen

Automatisch:

```json
{"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
```

Optional k?nnen `title` und `description` das Generierungsergebnis ?berschreiben.
Der Aufruf arbeitet synchron und kann wegen Download und KI l?nger dauern.
Bei einem Fehler wird kein unvollst?ndiges Quiz gespeichert.

Ohne KI kann derselbe Endpunkt zus?tzlich `questions` entgegennehmen.
Die Liste muss genau zehn unterschiedliche Fragen enthalten. Beispiel eines
einzelnen Elements; die tats?chliche Anfrage ben?tigt zehn solche Elemente:

```json
{
  "question": "Welche Farbe hat ein klarer Tageshimmel?",
  "answers": [
    {"text": "Blau", "is_correct": true},
    {"text": "Gr?n", "is_correct": false},
    {"text": "Rot", "is_correct": false},
    {"text": "Schwarz", "is_correct": false}
  ]
}
```

Jede Frage braucht vier unterschiedliche Antworttexte und genau eine korrekte
L?sung. Diese Regeln gelten auch f?r KI-Antworten. Titel: maximal 200 Zeichen,
Beschreibung: 5000, Frage: 1000, Antwort: 500. Der Titel erh?lt bei manueller
Erstellung ohne Angabe den Wert `Quiz`.

### Spielen und auswerten

Die Quizantwort enth?lt `id`, `title`, `description`, `youtube_url`,
`created_at`, `questions` und `progress`.
Fragen enthalten `id`, `question`, `position`, `answers` und
`correct_answer`; Antworten enthalten nur `id` und `text`.

Eine Auswahl speichern:

```http
PATCH /api/quizzes/1/progress/
Content-Type: application/json

{"question": 12, "answer": 47}
```

Erneutes Senden f?r dieselbe Frage ersetzt die Auswahl.
Frage und Antwort m?ssen zum eigenen Quiz und zueinander geh?ren.
Fortschritt wird mit jeder Auswahl automatisch gespeichert; nach zehn
beantworteten Fragen wird `completed` wahr.
Fortschritt enth?lt `attempt`, `completed`, `updated_at`, `selections`
und `score`. `selections` enth?lt Frage-/Antwort-IDs.

Vor Abschluss sind `score` und `correct_answer` null.
Danach ist `score` die Prozentzahl 0?100, und `correct_answer` enth?lt
die korrekte Antwort-ID je Frage. Nachtr?gliche ?nderungen aktualisieren den
Score. Wiederholung l?scht die bisherigen Auswahlen und verdeckt die L?sungen.
Gespeichert wird der aktuelle Versuch; eine Versuchshistorie ist nicht vorgesehen.

### Fehler

- 400: Validierung, falsche Login-Daten oder ungeeignete Videodauer.
- 401: Anmeldung fehlt, Token ung?ltig/abgelaufen oder Sitzung gesperrt.
- 403: CSRF-Pr?fung fehlgeschlagen.
- 404: Quiz existiert nicht oder geh?rt einem anderen Nutzer.
- 429: Ratenbegrenzung, standardm??ig anonym 60/Minute, angemeldet 120/Minute.
- 502: Download, Transkription, KI-Ausgabe oder externer Dienst fehlgeschlagen.
- 503: API-Keys oder FFmpeg/FFprobe fehlen.

Validierungsfehler sind feldbezogene JSON-Objekte, allgemeine Fehler verwenden
`detail` beziehungsweise bei Login `non_field_errors`.
Providerfehler und Zugangsdaten werden nicht an API-Clients durchgereicht.

## Admin

Mit `createsuperuser` einen Administrator einrichten.
Quizliste mit Nutzer-/Titelsuche, Datumsfilter und Links zu einzelnen Fragen.
Titel und Beschreibung k?nnen bearbeitet und vollst?ndige Quizze gel?scht werden.
Einzelne Fragen lassen sich separat bearbeiten, einschlie?lich Antworttexten
und korrekter L?sung. Die Antwortvalidierung gilt auch im Admin.

Neue Quizze entstehen ?ber die validierte API. Einzelne Fragen k?nnen im Admin
nicht hinzugef?gt oder gel?scht werden, damit zehn Fragen und vier Antworten
erhalten bleiben. Administratoren haben bewusst Zugriff auf alle Quizze.
Benutzerkonten werden ?ber das normale Django-UserAdmin verwaltet.

## Tests und Qualit?t

```powershell
python manage.py test --settings=quizly.test_settings
python manage.py makemigrations --check --dry-run --settings=quizly.test_settings
python scripts/check_quality.py
ruff check .
ruff format --check .
python -m pip check
```

Tests verwenden eine tempor?re Datenbank, einen ausschlie?lich f?r Tests
vorgesehenen Schl?ssel und einen schnellen Passwort-Hasher.
`quizly.test_settings` niemals f?r Entwicklung oder Produktion verwenden.
Externe Dienste sind in Tests simuliert; es werden keine echten Kosten erzeugt.

Die Pr?fungen decken Registrierung, doppelte E-Mails, Passwortvalidierung,
Cookie-Flags, Login, Token-Rotation, Logout/Blacklist, CSRF, Berechtigungen,
CRUD, Datumsauswahl, Fortschritt, Antwort?nderung, Bewertung, Wiederholung,
Admin-Bearbeitung, URL-Validierung, KI-Schema, Rollback und Dateibereinigung ab.
Der AST-Check erzwingt f?r alle Projektfunktionen einschlie?lich Tests
maximal 14 physische Zeilen ab der def-Zeile, snake_case und Docstrings.
Djangos Test-Lifecycle wird ?ber `setUp = setup_test` angebunden.

## Deployment

Eigene Secrets, Domainnamen und HTTPS konfigurieren:
`DJANGO_DEBUG=false`, `COOKIE_SECURE=true`, `SECURE_SSL_REDIRECT=true`.
Frontend-Urspr?nge explizit in CORS und CSRF eintragen.
HSTS ist au?erhalb des Debug-Modus aktiv.
Bei einem Reverse Proxy die HTTPS-Erkennung passend zur vertrauensw?rdigen
Proxy-Konfiguration einrichten; beliebige Forwarded-Header nicht vertrauen.

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py flushexpiredtokens
```

`flushexpiredtokens` regelm??ig, beispielsweise t?glich, ausf?hren.
Statische Dateien durch den Webserver bereitstellen und einen geeigneten
WSGI-/ASGI-Server einsetzen. SQLite ist f?r die lokale Abgabe eingerichtet;
bei parallelem Produktionsbetrieb eine Datenbank mit Zeilensperren und einen
gemeinsamen Cache f?r Ratenbegrenzungen konfigurieren. Der eingebaute
Entwicklungsserver ist kein Produktionsserver.

## Abnahmestatus und Quellen

Die vollst?ndige Zuordnung aller DoD-Punkte mit offenen externen Pr?fungen steht
in [docs/definition-of-done.md](docs/definition-of-done.md).
Der echte YouTube ? FFmpeg ? Whisper ? Gemini-Durchlauf und die Integration eines
nicht mitgelieferten Frontends m?ssen in der Zielumgebung gepr?ft werden.

Verwendete offizielle Schnittstellendokumentation:
[OpenAI Whisper / Transkriptionen](https://developers.openai.com/api/reference/python/resources/audio/subresources/transcriptions/methods/create),
[Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output),
[yt-dlp](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp),
[Simple JWT Blacklist und Rotation](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/settings.html).
