"""Local XSPF editor using Qt Widgets."""

import sys
from pathlib import Path
from xml.parsers.expat import ExpatError, ParserCreate

from PySide6.QtCore import QIODevice, QSaveFile, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow, QMessageBox, QTableView, QToolBar,
)

from playlist import Playlist
from station_model import StationModel

FILE_FILTER = "XSPF-Wiedergabelisten (*.xspf);;Alle Dateien (*)"
APP_NAME = "XSPF-Editor"


class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = None
        self.model = StationModel(self)
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setDragDropMode(QTableView.DragDropMode.InternalMove)
        self.table.setDragDropOverwriteMode(False)
        self.table.setDropIndicatorShown(True)
        self.table.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setColumnWidth(0, 260)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setTabKeyNavigation(True)
        self.setCentralWidget(self.table)

        file_menu = self.menuBar().addMenu("&Datei")
        edit_menu = self.menuBar().addMenu("&Bearbeiten")
        toolbar = QToolBar("Aktionen", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new = self.make_action("&Neu", self.new_playlist, QKeySequence.StandardKey.New)
        open_file = self.make_action("Ö&ffnen …", self.open_dialog, QKeySequence.StandardKey.Open)
        save = self.make_action("&Speichern", self.save, QKeySequence.StandardKey.Save)
        save_as = self.make_action(
            "Speichern &unter …", self.save_as, QKeySequence.StandardKey.SaveAs
        )
        quit_action = self.make_action("&Schließen", self.close, QKeySequence.StandardKey.Close)
        add = self.make_action("Sender &hinzufügen", self.add_station)
        self.remove = self.make_action("Sender &löschen", self.remove_station)
        file_menu.addActions([new, open_file, save, save_as])
        file_menu.addSeparator()
        file_menu.addAction(quit_action)
        edit_menu.addActions([add, self.remove])
        toolbar.addActions([new, open_file, save])
        toolbar.addSeparator()
        toolbar.addActions([add, self.remove])

        self.table.selectionModel().selectionChanged.connect(self.update_selection)
        self.model.modelReset.connect(self.update_selection)
        self.model.dataChanged.connect(self.mark_changed)
        self.model.rowsInserted.connect(self.mark_changed)
        self.model.rowsRemoved.connect(self.mark_changed)
        self.model.rowsMoved.connect(self.mark_changed)
        self.update_selection()
        self.update_title()
        self.statusBar().showMessage("Zellen per Doppelklick bearbeiten, Senderzeilen zum Sortieren ziehen.")
        self.resize(900, 530)

    def make_action(self, text, handler, shortcut=None):
        action = QAction(text, self)
        action.triggered.connect(handler)
        if shortcut is not None:
            action.setShortcut(shortcut)
        return action

    def update_selection(self, *_):
        self.remove.setEnabled(self.table.selectionModel().hasSelection())

    def mark_changed(self, *_):
        self.setWindowModified(True)

    def update_title(self):
        name = self.path.name if self.path else "Unbenannt"
        self.setWindowTitle(f"{name}[*] – {APP_NAME}")

    def set_playlist(self, playlist, path=None):
        self.model.replace_playlist(playlist)
        self.path = path
        self.update_title()
        self.setWindowModified(False)

    def new_playlist(self):
        if self.can_discard_changes():
            self.set_playlist(Playlist.empty())

    def open_dialog(self):
        name, _ = QFileDialog.getOpenFileName(
            self, "Wiedergabeliste öffnen", str(self.path.parent) if self.path else "", FILE_FILTER
        )
        if name:
            self.open_playlist(Path(name))

    def open_playlist(self, path):
        if not self.can_discard_changes():
            return
        try:
            playlist = Playlist.load(path)
        except (OSError, ValueError, LookupError, ExpatError) as error:
            QMessageBox.critical(self, "Öffnen fehlgeschlagen", f"{path}\n\n{error}")
            return
        self.set_playlist(playlist, path)

    def add_station(self):
        self.table.setFocus()
        index = self.model.append_station()
        self.table.setCurrentIndex(index)
        self.table.scrollTo(index)
        self.table.edit(index)

    def remove_station(self):
        self.table.setFocus()
        selection = self.table.selectionModel().selectedRows()
        if selection:
            self.model.removeRow(selection[0].row())

    def save(self):
        self.table.setFocus()
        return self.save_to(self.path) if self.path else self.save_as()

    def save_as(self):
        self.table.setFocus()
        dialog = QFileDialog(
            self, "Wiedergabeliste speichern",
            str(self.path) if self.path else "Unbenannt.xspf", FILE_FILTER,
        )
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix("xspf")
        if not dialog.exec():
            return False
        return self.save_to(Path(dialog.selectedFiles()[0]))

    def save_to(self, path):
        # QSaveFile replaces the destination only after the full write succeeds.
        output = QSaveFile(str(path))
        try:
            data = self.model.playlist.to_bytes()
            ParserCreate().Parse(data, True)
            if not output.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(output.errorString())
            if output.write(data) != len(data):
                output.cancelWriting()
                raise OSError(output.errorString())
            if not output.commit():
                raise OSError(output.errorString())
        except (OSError, ValueError, ExpatError) as error:
            QMessageBox.critical(self, "Speichern fehlgeschlagen", f"{path}\n\n{error}")
            return False
        self.path = path
        self.update_title()
        self.setWindowModified(False)
        self.statusBar().showMessage(f"Gespeichert: {path.name}", 4000)
        return True

    def can_discard_changes(self):
        self.table.setFocus()
        if not self.isWindowModified():
            return True
        button = QMessageBox.question(
            self, "Ungespeicherte Änderungen", "Änderungen an der Wiedergabeliste speichern?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if button == QMessageBox.StandardButton.Save:
            return self.save()
        return button == QMessageBox.StandardButton.Discard

    def closeEvent(self, event):
        if self.can_discard_changes():
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    editor = Editor()
    editor.show()
    if len(sys.argv) > 1:
        editor.open_playlist(Path(sys.argv[1]))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
