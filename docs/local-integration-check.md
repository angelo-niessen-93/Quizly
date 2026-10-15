# Lokale Integrationsprüfung – aktueller Abschluss

Stand: 15.10.2026, aktualisiert nach Umstellung auf lokales Whisper und
Anbindung des Spielfortschritts. Keine kostenpflichtigen Gemini- oder
OpenAI-API-Aufrufe wurden ausgeführt.

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

## Noch offen

- Ausdrückliche Freigabe für einen echten Gemini-Aufruf.
- Anschließend Gemini-Key-/Modellberechtigung sowie vollständige Kette
  YouTube → Audio → lokales Whisper → Gemini → Quiz → Datenbank prüfen.
- Produktives Hosting und HTTPS separat abnehmen.

Es fehlen keine lokalen Audio-Werkzeuge und kein OpenAI-API-Key mehr.
