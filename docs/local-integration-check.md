# Lokale Integrationsprüfung – aktueller Abschluss

Stand: 15.10.2026, nach lokaler Optimierung ohne weiteren echten API-Aufruf.
Keine kostenpflichtigen Gemini- oder OpenAI-API-Aufrufe wurden ausgeführt.

## Gemini-504: lokale Analyse und vorbereitete Optimierung

In dieser Arbeitsphase wurden ausschließlich lokale Prüfungen und simulierte
HTTP-Antworten verwendet. Keine Gemini-Metadatenabfragen, Tokenzählungs-API,
Generierungsaufrufe oder neuen Audio-Downloads. Das vorhandene Transkript mit
3834 Zeichen wurde unverändert für eine Offline-Requestvorbereitung genutzt.

| Möglicher Einfluss | Befund | Änderung / verbleibende Unsicherheit |
| --- | --- | --- |
| Clientseitiges Zeitlimit | SDK timeout=90000 ms wurde zu HTTPX connect/read/write/pool=90 Sekunden | Jetzt 190 Sekunden je Phase; kein garantierter Gesamt-Wallclock-Timeout |
| Serverseitiges Zeitlimit | Installiertes SDK erzeugte daraus zusätzlich X-Server-Timeout: 90; alter echter 504 nach 90,14 Sekunden | Explizit angeforderte 180 Sekunden, Clientreserve zehn Sekunden; Einhaltung und Dienstkapazität noch nicht real geprüft |
| Thinking | Nicht konfiguriert; Google dokumentiert medium als Standard für 3.8 Flash | Explizit low, keine Thought-Ausgabe; tatsächliche Latenzverbesserung noch offen |
| Promptumfang | 3834 Zeichen Transkript; bisheriger Systemprompt 310 Zeichen | Systemprompt 266 Zeichen; kein Beleg, dass die Eingangslänge den Fehler verursachte |
| Ausgabelänge | Kein anwendungseigenes max_output_tokens gesetzt; keine echte Tokenstatistik vom fehlgeschlagenen Aufruf | 8192 einschließlich Thinking; kurze Texte, keine Erklärungen; MAX_TOKENS kann weiterhin zu sicher verworfener Teilantwort führen |
| Automatische Wiederholungen | attempts=1 war gesetzt, aber SDK kann zusätzlich automatisch CONTINUATION folgen | Attempts weiterhin eins; Continuation, Function Calling und HTTP-Redirects explizit aus; keine Modelle als Fallback |
| HTTPX-Verbindungs-Retries | Standard-Transport hat retries=0 | Nicht aktiviert; simulierte ConnectError/ReadTimeout enden nach einem Request |
| Vorübergehender Gemini-Dienstfehler | Ein einzelner 504 und keine weiteren Servermetriken | Weder bewiesen noch ausgeschlossen; keine Live-Diagnose in dieser Phase |

Der beobachtete 504 war eine tatsächliche Providerantwort mit DEADLINE_EXCEEDED,
kein nachgewiesener lokaler ReadTimeout. Die SDK-Weitergabe der alten 90 Sekunden
an den Server wurde mit Dummy-Key und MockTransport lokal reproduziert. Die
Deadline ist damit ein konkreter Einfluss; eine einzelne abschließende Ursache
für die zu lange Berechnung lässt sich daraus nicht bestimmen.

Das bestehende Response-Schema stammt weiterhin aus QuizContentSerializer:
genau zehn Fragen, jeweils vier Antworten, erforderliche Text- und Booleanfelder.
Die vorhandene Inhaltsvalidierung fordert unterschiedliche Fragen/Optionen und
genau eine korrekte Antwort je Frage. Öffentliche Responses, Feldnamen, Statuscodes,
Fortschritt und Auswertung bleiben unverändert. Developer API wird explizit
gewählt; Modell gemini-3.8-flash und vorhandener API-Key bleiben unverändert.

### Tatsächlich ausgeführte lokale Prüfungen

- google-genai 2.31.0, HTTPX 0.28.1; SDK-Mindestversion auf 2.31 angehoben.
- Neun neue Tests mit echtem SDK und HTTPX MockTransport: LOW und Tokenlimit im
  Body, Schema 10/4, Deadline-/HTTPX-Einheiten, konfigurierbare Limits,
  keine Retries bei 408/429/500/502/503/504 oder Netzwerkfehlern, kein
  Redirect-Folgeaufruf, kein CONTINUATION-Folgeaufruf, abgewiesenes Teil-JSON
  bei MAX_TOKENS. Keine Verbindung zu Google.
- Gesamte Testsuite: 102 Backend-Tests und neun Frontend-Tests erfolgreich.
- Ruff, Formatierung und 14-Zeilen-/snake_case-/Docstring-Prüfung erfolgreich.
- `python scripts/prepare_gemini_test.py` mit dem tatsächlichen gespeicherten
  Transkript ausgeführt. Dummy-Key, in-memory Transport, null Providerrequests.
- `.cache/gemini-next-request.json` enthält den serialisierten Request ohne
  Zugangsdaten: 5029 Bytes JSON-Body, LOW, 8192 Tokens, Serverdeadline 180 und
  HTTPX-Phasenlimits 190 Sekunden. Der Transkript-Hash erlaubt die Wiedererkennung.
  Die Datei enthält den vollständigen Quelltext und bleibt von Git ausgeschlossen.
- Frontend unverändert und weiterhin im separaten Repository.

### Vorbereiteter einzelner Echtversuch: noch nicht freigegeben

1. Gesonderte Nutzerfreigabe und weiterhin kostenlosen Projekttarif bestätigen.
2. Gespeichertes Transkript direkt verwenden; keine erneute Transkription nötig.
3. Genau einen echten generateContent-Request mit optimierter Konfiguration
   beobachten; weder Retry noch Continuation, Function Calling oder Fallback.
4. Bei Fehler HTTP-Code und bereinigte Meldung erfassen und stoppen.
5. Bei Erfolg Inhalte validieren, über vorhandene Services atomar speichern,
   den dokumentierten API-Response prüfen und das Quiz im Frontend spielen.

Die Optimierung ist lokal abgesichert, aber noch kein erfolgreicher echter
Generierungsnachweis. Der letzte echte Aufruf bleibt der unten dokumentierte 504;
es wurde kein neues Quiz erzeugt. Hosting und erfolgreiche Gesamtabnahme bleiben offen.

Quellen (15.10.2026):
[Thinking/Tokenlimit](https://ai.google.dev/gemini-api/docs/generate-content/thinking),
[SDK](https://github.com/googleapis/python-genai),
[Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output).

## Letzter echter Versuch mit Gemini 3.8 Flash: HTTP 504

Für diesen Folgeversuch bestätigte der Benutzer erneut den Free Tier seines
Projekts und erlaubte höchstens einen echten Generierungsaufruf. Standard-
Textinput und Textoutput sind laut aktueller Google-Preisliste dort kostenlos.
Es wurden keine Tools, Grounding, Batch-Jobs, kostenpflichtigen Funktionen oder
anderen Modelle aufgerufen. Der vorhandene Key blieb unverändert.

Die lesende Abfrage für models/gemini-3.8-flash war erfolgreich und nennt
generateContent als unterstützte Aktion. Sie garantiert weder freie Kapazität
noch einen erfolgreichen Abschluss. Konkrete RPM-/TPM-/RPD-Projektwerte waren
weiterhin nicht einsehbar; es werden keine numerischen Limits behauptet.

| Schritt | Tatsächliches Ergebnis des Folgeversuchs |
| --- | --- |
| Modell / Methode | gemini-3.8-flash; generateContent über Metadaten bestätigt |
| Transkript wiederverwenden | Vorheriges Transkript nicht gespeichert; geeignetes YouTube-Video erneut verarbeitet |
| Video | https://www.youtube.com/watch?v=rb7TVW77ZCs; TED-Ed, ca. 275 Sekunden |
| yt-dlp / FFmpeg | MP3 erfolgreich, 2.201.132 Bytes, 3,81 Sekunden |
| Lokales Whisper small | Erfolgreich, 3.834 Zeichen, 18,33 Sekunden |
| Registrierung / Login | Erfolgreich, beide JWT-Cookies HTTP-only |
| POST /api/quizzes/ | Ein echter Request mit ausschließlich url; HTTP 502 nach 112,30 Sekunden |
| Tatsächliche Gemini-HTTP-Requests | Genau einer; HTTP-Request-Hook mit persistenter Einmal-Sperre; SDK attempts=1 |
| Gemini-Antwort | HTTP 504, DEADLINE_EXCEEDED; 90,14 Sekunden |
| Exakte bereinigte Provider-Meldung | Deadline expired before operation could complete. |
| Öffentliche API-Fehlermeldung | Quiz generation failed. Please try again later. |
| Generierte Fragen / Antwortmöglichkeiten | 0 / 0; kein Quiz-JSON geliefert |
| JSON / Lösungen validieren, Quiz speichern und GET abrufen | Nicht erreicht; keine erfolgreiche Generierungsantwort |
| Generiertes Quiz im Frontend spielen / auswerten | Nicht erreicht; kein Ersatzquiz als KI-Erfolg ausgegeben |
| Separates Frontend im echten Edge-Browser | Login-Seite erreichbar; credentialed CSRF-Fetch zur Backend-API HTTP 200, CORS erfolgreich |
| Audio-Dateien / Testkonto / Tokens | Audioordner gelöscht; Testkonto und Tokens entfernt |
| Automatisierte Tests | 93 Backend-Tests und neun Frontend-Tests erfolgreich |

Der 504 ist ein Provider-Deadline-Fehler, kein nachgewiesener Fehler des Keys
oder der Quizvalidierung. Es gab weder einen automatischen noch einen manuellen
zweiten Generierungsaufruf in diesem Folgeversuch. Ein längeres Timeout oder
andere Generierungsparameter wurden ohne weiteren Echtversuch nicht als Lösung
behauptet. Die bestehenden API-Verträge und die sichere 502 bleiben unverändert.

Ein neuer netzwerkfreier Regressionstest bildet die beobachtete Provider-504
nach: Die API antwortet mit 502, gibt keine privaten Providerdetails aus und
speichert kein Teilquiz. Der vorhandene SDK-Transporttest prüft zusätzlich,
dass temporäre Fehler nur einen tatsächlichen HTTP-Versuch auslösen.

Die zusätzliche SQLite-Nachprüfung im temporären Prüfskript verwendete zunächst
auth_user statt der vorhandenen Tabelle accounts_user und scheiterte separat.
Das war nicht die Ursache der API-502. Die Nachprüfung wurde über das tatsächliche
Django-Benutzermodell durchgeführt: null verbliebene Testkonten und null ihnen
zugeordnete Quizze. Der automatisierte Provider-504-Test prüft den unveränderten
Quizbestand vor einer Bereinigung in einer isolierten Testdatenbank.

Das neue Transkript liegt für einen ausdrücklich freigegebenen Folgeversuch
unter .cache/flash38-transcript.txt. Der Ordner ist von Git ausgeschlossen;
temporäres Audio und Prüfserver werden nicht dauerhaft benötigt.

**Offen:** Erfolgreiche Gemini-Antwort mit zehn validierten Fragen und vier
Optionen je Frage, deren SQLite-Speicherung, exakter GET-Response und Spiel
dieses tatsächlich generierten Quiz im Frontend. Ein weiterer Generierungsaufruf
benötigt eine neue Freigabe. Backend und Frontend bleiben eigenständige
Repositories; es wurde nichts committet oder gepusht.

Quellen (15.10.2026):
[Preise](https://ai.google.dev/gemini-api/docs/pricing),
[Limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Vorheriger Versuch mit Gemini 2.5 Flash

Der Benutzer bestätigte den Free Tier seines Projekts und erlaubte genau
einen kostenlosen Versuch. Googles Preisliste bestätigt kostenlosen Textinput
und Textoutput für Gemini 2.5 Flash im Free Tier. Projektbezogene numerische
RPM-/TPM-/RPD-Limits und Restkontingente waren hier nicht einsehbar; Google
verweist dafür auf AI Studio. Es wurden keine Quotenwerte erfunden.

| Schritt | Tatsächliches Ergebnis dieses Versuchs |
| --- | --- |
| Gemini-Konfiguration | Key gesetzt und unverändert; beim Test gemini-2.5-flash |
| Modell-Metadaten / Modellliste | Erfolgreiche lesende Requests; generateContent wird aufgeführt, dies beweist keine Generierungsberechtigung |
| Registrierung / Login / Cookies | HTTP 201 / 200; beide JWT-Cookies HTTP-only |
| POST /api/quizzes/ mit ausschließlich url | Genau einmal über echten lokalen Django-Server; HTTP 502 nach Providerfehler |
| Öffentliches gesprochenes Video | TED-Ed: How do vaccines work?; https://www.youtube.com/watch?v=rb7TVW77ZCs; ca. 275 Sekunden |
| yt-dlp und FFmpeg | Erfolgreich; MP3 mit 2.201.132 Bytes; 3,80 Sekunden |
| Lokales Whisper small / CUDA | Erfolgreich; 3.834 Zeichen Transkript; 19,84 Sekunden |
| Gemini Flash | Genau ein echter Generierungsversuch; ClientError, HTTP 404 nach 0,84 Sekunden |
| Generierte Fragen / Antworten | 0 / 0; kein gültiger Modellinhalt zur Validierung oder Speicherung |
| Gesamter POST | 24,50 Sekunden; sichere 502 ohne Providerdetails oder Zugangsdaten |
| Generiertes Quiz speichern und GET abrufen | Nicht erreicht; kein generiertes Quiz vorhanden |
| Generiertes Quiz im Frontend spielen / auswerten | Nicht erreicht; kein manuelles Testquiz als Ersatz ausgegeben |
| Temporäre Dateien / Testkonto | Temporärer Audioordner entfernt; isoliertes Testkonto und Tokens entfernt |

Google beschränkt 2.5-Modelle auf zuvor aktive Projekte. Das ist eine plausible
Erklärung für den 404; die konkrete Providerursache ist nicht abschließend
bewiesen. Ein nichtleerer Key, eine Modellliste und gültige Free-Tier-Preise
sind keine Garantie für einen erfolgreichen generateContent-Aufruf.

Nach dem fehlgeschlagenen Versuch wurden Standard, .env.example und die
nicht geheime lokale GEMINI_MODEL-Einstellung auf gemini-3.8-flash vorbereitet.
Dieses Modell wird in der lesend abgerufenen Modellliste aufgeführt und von
Google für neue Projekte empfohlen; Textinput/-output sind im Free Tier frei.
Der vorhandene API-Key wurde dabei nicht verändert. Es wurde weder mit diesem
Modell noch mit einem anderen Modell eine weitere Generierung ausgeführt.
Die Änderung ist deshalb ausdrücklich noch kein erfolgreicher Funktionstest.

Automatische SDK-Retries sind jetzt deaktiviert: attempts=1. Ein zusätzlicher
Test mit echtem SDK und lokalem HTTP-MockTransport prüft, dass selbst ein
temporärer HTTP-503-Providerfehler nur einen HTTP-Versuch auslöst. Kein
automatischer Modell-Fallback. Aktuell: 92 Backend- und neun Frontend-Tests
erfolgreich; API-Verträge unverändert; Frontend unverändert und separat.

Für den nächsten Versuch: konkrete Free-Tier-Projektlimits in AI Studio
prüfen und einen weiteren einmaligen Aufruf freigeben. Erfolgreiche Generierung,
zehn validierte Fragen, SQLite-Speicherung, GET und Browser-Spiel bleiben offen.

Quellen (15.10.2026):
[Preise](https://ai.google.dev/gemini-api/docs/pricing),
[Limits](https://ai.google.dev/gemini-api/docs/rate-limits),
[Modellzugriff](https://ai.google.dev/gemini-api/docs/deprecations).

## Frühere lokale Nachweise

Die folgenden Abschnitte dokumentieren die vorangegangene Audio- und
Fortschrittsprüfung. Aussagen über den damals noch nicht ausgeführten
Gemini-Aufruf werden durch das aktuelle Ergebnis oben ersetzt.

## Getrennte Repositories und laufende Dienste

- Backend: D:\DEVAkademie\Projekte\Quizly, eigenes .git,
  http://127.0.0.1:8000/.
- Frontend: D:\DEVAkademie\Projekte\Quizly-Frontend, eigenes .git,
  http://127.0.0.1:5500/.
- Frontend-Quelle:
  [Developer-Akademie-Backendkurs/project.Quizly](https://github.com/Developer-Akademie-Backendkurs/project.Quizly),
  Ausgangscommit ae8e8637e39d328e3b8a55670db77f121deffb49.
- Kommunikation ausschließlich per REST; keine Frontend-Dateien im Backend.
- Keine Commits, Pushes oder Änderungen am GitHub-Repository der Akademie.

## Whisper, PyTorch und FFmpeg

| Prüfung | Tatsächliches Ergebnis |
| --- | --- |
| openai-whisper | 20250625 in Backend-.venv installiert; Paket aus openai/whisper |
| OpenAI-Transkriptions-API | Vollständig entfernt; OpenAI-API-SDK aus Requirements und .venv entfernt |
| Modell | small; offizieller Modelldownload im ignorierten Cache |
| PyTorch | 2.14.1+cu130, innerhalb der Backend-.venv |
| NVIDIA | RTX 5070 Ti, Treiber 610.74, Compute Capability 12.0 |
| CUDA | Runtime 13.0, verfügbar; echte Tensor-Matrixmultiplikation erfolgreich |
| Tatsächliche Modellplatzierung | cuda:0 |
| Modellwiederverwendung | Zwei lokale Aufrufe: ein Cache-Miss, ein Cache-Hit |
| FFmpeg | 9.0.2, ffmpeg -version erfolgreich |
| FFprobe | 9.0.2, ffprobe -version erfolgreich |
| Windows-Installation | winget install --id Gyan.FFmpeg -e, Installer-Hash verifiziert |
| Erreichbarkeit | Windows-Befehle nach PATH-Aktualisierung; zusätzlich FFMPEG_LOCATION in .env gesetzt |

FFMPEG_LOCATION zeigt auf den bin-Ordner der WinGet-Installation.
Die Django-Einstellungen ergänzen diesen Pfad für lokale Whisper-Unterprozesse.
Der vorhandene Gemini-Key wurde beim Aktualisieren dieser nicht geheimen
Einstellung unverändert erhalten.

Eine lokale WAV-Datei wurde mit Windows-Sprachausgabe erzeugt.
Whisper erkannte den bekannten englischen Testsatz korrekt; beide Aufrufe
lieferten denselben Text. Der zweite Aufruf benötigte ungefähr 0,44 Sekunden
einschließlich Spracherkennung, ohne erneutes Modellladen.

Das Modell wird pro Prozess einmal lazy geladen. Ein Lock umfasst Laden und
Inferenz, sodass parallele Requests nicht mehrere Modelle laden.
Die Tests prüfen auch CPU-Fallback, FP16-Auswahl und Wiederholung nach Ladefehler.

## Gemini und .env ohne Secret-Ausgabe

| Variable | Ergebnis |
| --- | --- |
| GEMINI_API_KEY | Im Backend-.env vorhanden; von frischem Django-Prozess geladen |
| GEMINI_MODEL | gemini-2.5-flash |
| OPENAI_API_KEY | Keine Anwendungseinstellung mehr; nicht benötigt |
| WHISPER_MODEL | small als Standard |
| WHISPER_DEVICE | auto, tatsächlich CUDA gewählt |
| WHISPER_CACHE_DIR | Standard .cache/whisper, von Git ausgeschlossen |
| FFMPEG_LOCATION | Konfiguriert; beide Programme tatsächlich erreichbar |
| Django SECRET_KEY | Vorhanden; Wert nicht ausgegeben |
| CORS und CSRF | Bestehende lokale Origins auf Port 5500 beibehalten |
| Cookie-Einstellungen | HTTP-only aktiv; Secure=false ausschließlich für bestehenden lokalen HTTP-Betrieb |

Der frühere Leermeldungs-Befund war vor dem Eintragen des Keys entstanden.
Die aktuelle Datei verwendet bereits den richtigen Namen. Ein frischer Prozess
liest den Key; der alte Entwicklungsserver musste neu gestartet werden.
Es wurde weder ein gültiger Key verändert noch ein Ersatzwert erfunden.

Konfigurationsprüfung für Gemini und beide Audio-Werkzeuge erfolgreich.
Die externe Gültigkeit und Modellberechtigung des Gemini-Keys bleibt ohne
freigegebenen echten Aufruf ungeprüft.

## Echte Verarbeitungskette und ihre Grenze

| Stufe | Ergebnis |
| --- | --- |
| YouTube-URL / Metadaten | Erfolgreich, echter Netzwerkzugriff |
| yt-dlp Audio-Download | Erfolgreich, echtes Beispielvideo dQw4w9WgXcQ |
| FFmpeg MP3-Konvertierung | Erfolgreich |
| FFprobe | mp3, 213,04 Sekunden, 1.704.812 Bytes |
| Lokales Whisper small auf GPU | Erfolgreich, nichtleeres Transkript mit 1.773 Zeichen |
| Temporäre Dateien entfernen | Erfolgreich, temporärer Ordner nach Verarbeitung nicht mehr vorhanden |
| Gemini-Generierung | Nicht ausgeführt: Kostenfreigabe fehlt |
| Tatsächliches Gemini-Ergebnis → Datenbank | Offen bis zum freigegebenen Gemini-Durchlauf |
| Manuelles Testquiz → Datenbank | Erfolgreich, echte REST-Requests mit zehn Fragen und 40 Antworten |
| Generierte JSON-Inhalte validieren und speichern | Weiterhin durch Tests mit simuliertem Gemini-Inhalt abgesichert |

Der Transkriptinhalt des YouTube-Beispiels wurde nicht im Bericht gespeichert.
Der echte kostenlose Audiopfad ist damit geprüft. Ein manuelles Testquiz
oder ein simuliertes Gemini-Ergebnis ersetzt keinen echten Gemini-Nachweis.

## Fortschritt im echten Browser und in SQLite

Geprüft mit Microsoft Edge 155.0.4283.45 und Selenium 4.43.0.
Der Browser kommunizierte mit dem echten Django-Server und SQLite.
Testbenutzer, Tokens und manuelle Quizdaten wurden nach dem Test entfernt.

| Schritt | Tatsächliches Ergebnis |
| --- | --- |
| Registrierung und Login | Weiterhin erfolgreich über echte Formulare |
| Auswahl ohne Weiter-Klick | Sofort PATCH; gespeicherte Auswahl direkt in SQLite nachgewiesen |
| Neuladen | Erster unbeantworteter Eintrag geöffnet; bisherige Auswahl beim Zurückgehen markiert |
| Antwort ändern | Auswahl ersetzt, weiterhin genau ein Datensatz für dieselbe Frage |
| Erneutes Neuladen | Geänderte Antwort korrekt wiederhergestellt |
| Zehn Fragen abschließen | completed=true, zehn gespeicherte Auswahlen, UI und Backend zeigen 90 % |
| Antwort nach Abschluss ändern | Gespeicherte Bewertung und bestehende UI-Auswertung wechseln auf 100 % |
| Wiederholen | POST replay; attempt=2, completed=false und null Auswahlen |
| Neuladen nach Wiederholung | Zurückgesetzter Zustand bleibt erhalten |
| Eingespritzter Speicherfehler 503 | Kein falscher Erfolgszustand; UI-Auswahl wird auf bestätigten Serverstand zurückgesetzt |
| Danach erneut speichern | Erfolgreich, Backend erhält die Auswahl |

Ein dabei gefundener Fehler in restoreSelectedAnswer wurde behoben:
Eine fehlende gespeicherte Auswahl entfernt jetzt eine zuvor markierte
Antwort. Ein zusätzlicher automatisierter Frontend-Test sichert das ab.

QuizProgress serialisiert Schreibzugriffe, damit schnelle Änderungen und
Replay nicht in anderer Reihenfolge auf dem Server ankommen. Fehler brechen
die Warteschlange nicht dauerhaft; weitere Versuche bleiben möglich.
Die bestehenden öffentlichen Quiz-Response-Felder wurden nicht geändert.

## Automatisierte Prüfungen

- 91 Backend-Tests erfolgreich: bisherige 83 Regressionen mit angepasstem
  Transkriptionstest sowie acht neue lokale Whisper-Tests.
- Neun Frontend-Tests erfolgreich: Wiederherstellung, Autosave-Zuordnung,
  Ersetzen, Reihenfolge, Reload, Replay, Fehler-/Retry-Verhalten,
  unbekannte Antworten und UI-Rollback.
- Ruff, Formatierung, 14-Zeilen-/snake_case-/Docstring-Prüfung erfolgreich.
- Keine ausstehenden Modellmigrationen oder Abhängigkeitskonflikte.
- JavaScript-Syntax und git diff --check in beiden Repositories geprüft.
- Backend-API-Verträge, Cookies und Berechtigungen bleiben unverändert.

## Damals noch offen; aktueller Stand siehe oben

- Ausdrückliche Freigabe für einen echten Gemini-Aufruf.
- Anschließend Gemini-Key-/Modellberechtigung sowie vollständige Kette
  YouTube → Audio → lokales Whisper → Gemini → Quiz → Datenbank prüfen.
- Produktives Hosting und HTTPS separat abnehmen.

Es fehlen keine lokalen Audio-Werkzeuge und kein OpenAI-API-Key mehr.
