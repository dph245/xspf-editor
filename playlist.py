"""Edit station fields in the original XSPF document."""

from pathlib import Path
from xml.dom import Node, XMLNS_NAMESPACE, minidom

XSPF = "http://xspf.org/ns/0/"
VLC = "http://www.videolan.org/vlc/playlist/ns/0/"
VLC_APPLICATION = "http://www.videolan.org/vlc/playlist/0"


def elements(parent, namespace, name):
    return [
        node for node in parent.childNodes
        if node.nodeType == Node.ELEMENT_NODE
        and node.namespaceURI == namespace and node.localName == name
    ]


def text_of(element):
    return "".join(
        node.data for node in element.childNodes
        if node.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE)
    )


def indentation(node):
    if node is not None and node.nodeType == Node.TEXT_NODE and not node.data.strip():
        return node
    return None


def append_entry(parent, entry, previous=None):
    closing_space = indentation(parent.lastChild)
    if previous is not None and (space := indentation(previous.previousSibling)):
        parent.insertBefore(space.cloneNode(False), closing_space)
    elif closing_space is not None and "\n" in closing_space.data:
        parent.insertBefore(
            parent.ownerDocument.createTextNode(closing_space.data + "  "), closing_space
        )
    parent.insertBefore(entry, closing_space)


def remove_entry(entry):
    parent = entry.parentNode
    if space := indentation(entry.previousSibling):
        parent.removeChild(space)
    parent.removeChild(entry)


def move_entry(entry, before, last):
    if before is None:
        remove_entry(entry)
        append_entry(last.parentNode, entry, last)
    else:
        parent = before.parentNode
        remove_entry(entry)
        space = indentation(before.previousSibling)
        parent.insertBefore(entry, space or before)
        if space is not None:
            parent.insertBefore(space.cloneNode(False), entry)


class Playlist:
    def __init__(self, document):
        self.document = document
        root = document.documentElement
        self.namespace = root.namespaceURI
        if root.localName != "playlist" or self.namespace not in (XSPF, None):
            raise ValueError("Die Datei enthält keine XSPF-Wiedergabeliste.")
        track_lists = elements(root, self.namespace, "trackList")
        if len(track_lists) != 1:
            raise ValueError("Die Wiedergabeliste muss genau ein trackList-Element enthalten.")
        self.track_list = track_lists[0]
        self.tracks = elements(self.track_list, self.namespace, "track")
        self.vlc_index, self.vlc_items = self.find_flat_vlc_index(root)

    @classmethod
    def empty(cls):
        return cls(minidom.parseString(
            f'<playlist xmlns="{XSPF}" version="1">\n  <trackList>\n  </trackList>\n</playlist>'
        ))

    @classmethod
    def load(cls, path: Path):
        return cls(minidom.parseString(path.read_bytes()))

    def to_bytes(self):
        return self.document.toxml(encoding="UTF-8", standalone=self.document.standalone) + b"\n"

    def create_element(self, parent, name):
        qualified_name = f"{parent.prefix}:{name}" if parent.prefix else name
        return self.document.createElementNS(self.namespace, qualified_name)

    def field(self, row, name):
        matches = elements(self.tracks[row], self.namespace, name)
        return text_of(matches[0]) if matches else ""

    def set_field(self, row, name, value):
        track = self.tracks[row]
        matches = elements(track, self.namespace, name)
        if matches:
            field = matches[0]
            if text_of(field) == value:
                return False
            for child in list(field.childNodes):
                if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
                    field.removeChild(child)
        elif value:
            field = self.create_element(track, name)
            locations = elements(track, self.namespace, "location")
            identifiers = elements(track, self.namespace, "identifier")
            preceding = identifiers or locations
            after = preceding[-1] if name == "title" and preceding else None
            anchor = after.nextSibling if after else track.firstChild
            if space := indentation(after.previousSibling if after else anchor):
                track.insertBefore(space.cloneNode(False), anchor)
            track.insertBefore(field, anchor)
        else:
            return False
        if value:
            field.insertBefore(self.document.createTextNode(value), field.firstChild)
        return True

    def append_track(self):
        track = self.create_element(self.track_list, "track")
        append_entry(self.track_list, track, self.tracks[-1] if self.tracks else None)
        self.tracks.append(track)
        if self.vlc_index is not None:
            ids = {item.getAttribute("tid") for item in self.vlc_items.values()}
            tid = next(str(number) for number in range(len(ids) + 1) if str(number) not in ids)
            extension = self.create_element(track, "extension")
            extension.setAttribute("application", VLC_APPLICATION)
            track.appendChild(extension)
            identifier = self.document.createElementNS(VLC, "vlc:id")
            identifier.setAttributeNS(XMLNS_NAMESPACE, "xmlns:vlc", VLC)
            identifier.appendChild(self.document.createTextNode(tid))
            extension.appendChild(identifier)
            item = self.document.createElementNS(VLC, "vlc:item")
            item.setAttributeNS(XMLNS_NAMESPACE, "xmlns:vlc", VLC)
            item.setAttribute("tid", tid)
            previous = self.tracks[-2] if len(self.tracks) > 1 else None
            append_entry(self.vlc_index, item, self.vlc_items.get(previous))
            self.vlc_items[track] = item

    def remove_track(self, row):
        track = self.tracks.pop(row)
        remove_entry(track)
        if self.vlc_index is not None:
            remove_entry(self.vlc_items.pop(track))
            if not self.vlc_index.hasChildNodes():
                self.vlc_index.appendChild(self.document.createTextNode("\n"))

    def move_track(self, source, destination):
        track = self.tracks[source]
        before = self.tracks[destination] if destination < len(self.tracks) else None
        last = self.tracks[-1]
        move_entry(track, before, last)
        if self.vlc_index is not None:
            move_entry(self.vlc_items[track], self.vlc_items.get(before), self.vlc_items[last])
        self.tracks.pop(source)
        self.tracks.insert(destination - (destination > source), track)

    def find_flat_vlc_index(self, root):
        # A flat VLC index can mirror trackList. Leave custom order and folders alone.
        for extension in elements(root, self.namespace, "extension"):
            if extension.getAttribute("application") != VLC_APPLICATION:
                continue
            items = elements(extension, VLC, "item")
            if len(items) != sum(
                child.nodeType == Node.ELEMENT_NODE for child in extension.childNodes
            ):
                continue
            ids = [item.getAttribute("tid") for item in items]
            track_ids = []
            for track in self.tracks:
                track_ids.append([
                    text_of(identifier).strip()
                    for info in elements(track, self.namespace, "extension")
                    if info.getAttribute("application") == VLC_APPLICATION
                    for identifier in elements(info, VLC, "id")
                ])
            if (
                len(set(ids)) == len(ids)
                and all(
                    tid.isascii() and tid.isdecimal() and (tid == "0" or not tid.startswith("0"))
                    for tid in ids
                )
                and track_ids == [[tid] for tid in ids]
            ):
                return extension, dict(zip(self.tracks, items))
        return None, {}
