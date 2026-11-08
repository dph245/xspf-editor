# XSPF-Editor

Nativer Desktop-Editor für Webradio-Playlists mit Python und PySide6. Die Anwendung arbeitet lokal mit XSPF-Dateien.

## Start

Mit Python 3.10 oder neuer im Projektverzeichnis:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python xspf_editor.py
```

Eine vorhandene Playlist lässt sich auch direkt mit `python xspf_editor.py /pfad/zur/liste.xspf` öffnen.

## Bedienung

- Unter **Datei** eine Playlist öffnen, neu anlegen, speichern oder unter einem anderen Namen speichern.
- Sendername und Stream-URL per Doppelklick oder **F2** bearbeiten. **Enter** übernimmt die Eingabe, **Esc** verwirft sie.
- Mit **Sender hinzufügen** eine Zeile anlegen oder die ausgewählte Zeile mit **Sender löschen** entfernen.
- Über **Sortieren** die Sendernamen aufsteigend (**A–Z**) oder absteigend (**Z–A**) sortieren. Leere Namen bleiben am Ende. Beim Speichern wird die neue Reihenfolge in die XSPF-Datei übernommen.
- Eine Zeile mit der Maus an den oberen oder unteren Rand einer anderen Zeile ziehen, um sie davor oder danach einzufügen.
- Beim Öffnen einer anderen Datei, beim Neuanlegen und beim Schließen fragt der Editor bei ungespeicherten Änderungen nach.

## XSPF-Dateien

Beim Speichern bleiben Playlist- und Sendermetadaten, XML-Namensräume, Kommentare und Erweiterungen erhalten. In der Tabelle wird die erste `location` eines Senders bearbeitet. Weitere `location`-Einträge bleiben erhalten. Die Ausgabe verwendet UTF-8 und kann sich in der XML-Formatierung von der Eingabedatei unterscheiden.

Einen flachen VLC-Index, der der Senderliste entspricht, führt der Editor bei Zeilenänderungen mit. Verschachtelte VLC-Ordner und eigene Reihenfolgen bleiben als XML erhalten. VLC kann die Wiedergabeliste deshalb weiterhin nach seiner Ordnerstruktur oder eigenen Reihenfolge anzeigen.

Relative Adressen bleiben beim Speichern als Text erhalten. Wird die Datei in einem anderen Ordner gespeichert, können sie dort auf andere Ziele verweisen.
