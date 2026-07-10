import struct

import flame

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore


MENU_NAME = "EXR Layers To Action"
MENU_GROUP = "Jiawei"

print("Loaded exr_autocomp:", MENU_GROUP, "-", MENU_NAME)


def val(obj, name):
    if not hasattr(obj, name):
        return None
    value = getattr(obj, name)
    if callable(value):
        try:
            return value()
        except Exception:
            return None
    return value


def first(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def get_batch():
    batch = flame.batch
    if callable(batch):
        batch = batch()
    return batch


def is_selected(node):
    for attr in ["selected", "is_selected", "isSelected"]:
        selected = val(node, attr)
        if selected is True or str(selected).lower() in ["true", "1", "selected"]:
            return True
    return False


def get_selected_clip_node(selection=None):
    if selection:
        if isinstance(selection, (list, tuple)):
            return selection[0] if selection else None
        return selection

    for node in list(val(get_batch(), "nodes") or []):
        if is_selected(node):
            return node
    return None


def get_segment_from_clip_node(node):
    clip = val(node, "clip")
    version = first(val(clip, "versions")) if clip else None
    track = first(val(version, "tracks")) if version else None
    return first(val(track, "segments")) if track else None


def selected_node_exr_path(selection=None):
    node = get_selected_clip_node(selection)
    if not node:
        return None, None

    segment = get_segment_from_clip_node(node)
    path = val(segment, "file_path") if segment else None
    if path and ".exr" in str(path).lower():
        return node, str(path)

    return node, None


def read_cstring(data, pos):
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", errors="replace"), end + 1


def parse_chlist(raw):
    channels = []
    pos = 0
    while pos < len(raw):
        if raw[pos] == 0:
            break
        name, pos = read_cstring(raw, pos)
        pos += 4
        pos += 4
        pos += 8
        channels.append(name)
    return channels


def parse_string(raw):
    return raw.rstrip(b"\x00").decode("utf-8", errors="replace")


def channel_group_name(channel):
    channel = str(channel).strip()
    if not channel:
        return None

    if "." not in channel:
        if channel.upper() in ("R", "G", "B", "A"):
            return "__ROOT_COLOR__"
        return channel

    prefix, component = channel.rsplit(".", 1)
    if not prefix:
        return channel

    if component.lower() in {
        "r", "g", "b", "a",
        "red", "green", "blue", "alpha",
        "x", "y", "z", "u", "v",
    }:
        return prefix

    return channel


def group_exr_channels(channels):
    grouped = {}
    order = []

    for raw_channel in channels:
        channel = str(raw_channel).strip()
        group_name = channel_group_name(channel)
        if not group_name:
            continue

        if group_name not in grouped:
            grouped[group_name] = []
            order.append(group_name)
        grouped[group_name].append(channel)

    layers = []
    for group_name in order:
        group_channels = grouped[group_name]
        display_name = group_name

        if group_name == "__ROOT_COLOR__":
            components = {channel.upper() for channel in group_channels}
            display_name = "RGBA" if "A" in components else "RGB"

        layers.append({
            "name": display_name,
            "channels": group_channels,
        })

    return layers


def normalize_exr_layers(parts):
    if len(parts) != 1:
        return parts

    part = parts[0]
    grouped_layers = group_exr_channels(part.get("channels", []))
    part_name = str(part.get("name", ""))

    if part_name.startswith("part_") or len(grouped_layers) > 1:
        return grouped_layers

    return parts


def read_exr_parts(path):
    with open(path, "rb") as handle:
        data = handle.read(8 * 1024 * 1024)

    magic, version = struct.unpack_from("<II", data, 0)
    if magic != 20000630:
        raise ValueError("Not an EXR file")

    pos = 8
    parts = []

    while pos < len(data):
        try:
            channels = []
            part_name = None

            while pos < len(data):
                attr_name, pos = read_cstring(data, pos)
                if attr_name == "":
                    break

                attr_type, pos = read_cstring(data, pos)
                size = struct.unpack_from("<I", data, pos)[0]
                pos += 4
                raw = data[pos:pos + size]
                pos += size

                if attr_name == "channels" and attr_type == "chlist":
                    channels = parse_chlist(raw)

                if attr_name == "name" and attr_type == "string":
                    part_name = parse_string(raw)

            if not channels and not part_name:
                break

            parts.append({
                "name": part_name or ("part_%02d" % len(parts)),
                "channels": channels,
            })

        except Exception:
            break

    return parts


def find_socket(source, layer_name):
    sockets = val(source, "output_sockets") or []
    layer_name = str(layer_name)
    aliases = [layer_name]

    if layer_name.upper() == "RGBA":
        aliases.append("RGB")
    elif layer_name.upper() == "RGB":
        aliases.append("RGBA")

    for alias in aliases:
        candidates = [alias, alias + "_" + alias]
        for candidate in candidates:
            for socket in sockets:
                if (
                    str(socket).casefold() == candidate.casefold()
                    or socket_key(socket) == socket_key(candidate)
                ):
                    return socket

        prefix = alias.casefold() + "_"
        for socket in sockets:
            if str(socket).casefold().startswith(prefix):
                return socket

    return None


def socket_key(value):
    return "".join(
        character
        for character in str(value).casefold()
        if character.isalnum()
    )


def node_coordinate(node, name):
    value = getattr(node, name, None)
    getter = getattr(value, "get_value", None)
    if callable(getter):
        value = getter()
    elif callable(value):
        value = value()

    if isinstance(value, (int, float)):
        return value
    return None


def position_action_nodes(source, action, media=None, media_index=0):
    source_x = node_coordinate(source, "pos_x")
    source_y = node_coordinate(source, "pos_y")
    if source_x is None or source_y is None:
        return

    action.pos_x = source_x + 400
    action.pos_y = source_y

    if media is not None:
        media.pos_x = source_x + 200
        media.pos_y = source_y + (media_index * 100)


def assign_media_to_surface(surface, action):
    media_layers = val(action, "media_layers") or []
    if not media_layers:
        return False

    media_index = len(media_layers) - 1
    try:
        surface.assign_media(media_index)
        return True
    except Exception as error:
        print("assign_media index failed:", media_index, error)
        return False


def show_message(message):
    for method_name in ["message_dialog", "show_message", "display_message"]:
        method = getattr(flame, method_name, None)
        if callable(method):
            try:
                method(message)
                return
            except TypeError:
                method(MENU_NAME, message)
                return
            except Exception:
                pass
    print(message)


class DragCheckTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super(DragCheckTable, self).__init__(parent)
        self.drag_checking = False
        self.drag_state = QtCore.Qt.Checked
        self.setMouseTracking(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

    def mousePressEvent(self, event):
        row = self.rowAt(event.pos().y())
        if row >= 0:
            item = self.item(row, 0)
            if item:
                current = item.checkState()
                self.drag_state = QtCore.Qt.Unchecked if current == QtCore.Qt.Checked else QtCore.Qt.Checked
                item.setCheckState(self.drag_state)
                self.drag_checking = True
                self.selectRow(row)
                return
        super(DragCheckTable, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_checking:
            row = self.rowAt(event.pos().y())
            if row >= 0:
                item = self.item(row, 0)
                if item:
                    item.setCheckState(self.drag_state)
                    self.selectRow(row)
                return
        super(DragCheckTable, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_checking = False
        super(DragCheckTable, self).mouseReleaseEvent(event)


class ExrLayerDialog(QtWidgets.QDialog):
    def __init__(self, path, parts):
        super(ExrLayerDialog, self).__init__()
        self.setWindowTitle(MENU_NAME)
        self.resize(920, 650)

        self.table = DragCheckTable()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Use", "Layer", "Channels", "Blend"])
        self.table.setRowCount(len(parts))

        for row, part in enumerate(parts):
            check = QtWidgets.QTableWidgetItem()
            check.setFlags(check.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            check.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row, 0, check)

            layer_item = QtWidgets.QTableWidgetItem(part["name"])
            layer_item.setFlags(layer_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 1, layer_item)

            channels_item = QtWidgets.QTableWidgetItem(", ".join(part["channels"]))
            channels_item.setFlags(channels_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 2, channels_item)

            blend = QtWidgets.QComboBox()
            blend.addItems(["Add"])
            blend.setCurrentText("Add")
            self.table.setCellWidget(row, 3, blend)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

        select_all_btn = QtWidgets.QPushButton("Select All")
        select_none_btn = QtWidgets.QPushButton("Select None")
        create_btn = QtWidgets.QPushButton("Create Action")
        close_btn = QtWidgets.QPushButton("Close")

        select_all_btn.clicked.connect(lambda: self.set_all(True))
        select_none_btn.clicked.connect(lambda: self.set_all(False))
        create_btn.clicked.connect(self.accept)
        close_btn.clicked.connect(self.reject)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(select_all_btn)
        buttons.addWidget(select_none_btn)
        buttons.addStretch(1)
        buttons.addWidget(create_btn)
        buttons.addWidget(close_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(path))
        layout.addWidget(self.table)
        layout.addLayout(buttons)

    def set_all(self, enabled):
        state = QtCore.Qt.Checked if enabled else QtCore.Qt.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(state)

    def selected_layers(self):
        layers = []
        for row in range(self.table.rowCount()):
            check = self.table.item(row, 0)
            if check and check.checkState() == QtCore.Qt.Checked:
                layers.append(self.table.item(row, 1).text())
        return layers


def create_action_from_layers(source, layer_names):
    batch = get_batch()
    action = batch.create_node("Action")
    action.name = "EXR_LAYERS_ACTION"
    position_action_nodes(source, action)

    back_socket = find_socket(source, "RGBA")
    if back_socket:
        try:
            batch.connect_nodes(source, back_socket, action, "Back")
            print("RGBA -> Action Back OK")
        except Exception as error:
            print("RGBA -> Action Back failed:", error)

    count = 0
    media_position_index = 0
    unmatched_layers = []

    for name in layer_names:
        socket = find_socket(source, name)
        print("Layer:", name, "Socket:", socket)

        if not socket:
            unmatched_layers.append(name)
            continue

        media = action.add_media()
        position_action_nodes(
            source,
            action,
            media,
            media_index=media_position_index,
        )
        media_position_index += 1
        try:
            media.name = "MEDIA_" + name
        except Exception:
            pass

        try:
            batch.connect_nodes(source, socket, media, "Front")
        except Exception as error:
            print("connect failed:", error)
            continue

        surface = action.create_node("Surface")
        try:
            surface.name = "SURFACE_" + name
        except Exception:
            pass

        if assign_media_to_surface(surface, action):
            count += 1

    if unmatched_layers:
        print("Unmatched layers:", unmatched_layers)
        print("Available sockets:", val(source, "output_sockets") or [])

    if count == 0:
        available = val(source, "output_sockets") or []
        show_message(
            "No selected EXR layers matched the Flame output sockets.\n"
            "Selected: %s\nAvailable: %s"
            % (", ".join(layer_names), ", ".join(map(str, available)))
        )

    print("Created layers:", count)
    return action


def run_exr_layers_to_action(selection=None):
    node, path = selected_node_exr_path(selection)

    if not node:
        show_message("Please select an EXR ClipNode in Batch first.")
        return None

    if not path:
        show_message("Selected Batch node is not an EXR ClipNode.")
        return None

    parts = normalize_exr_layers(read_exr_parts(path))
    if not parts:
        show_message("No EXR layers were found.")
        return None

    dialog = ExrLayerDialog(path, parts)
    runner = getattr(dialog, "exec_", None) or getattr(dialog, "exec")
    result = runner()

    if result != QtWidgets.QDialog.Accepted:
        return None

    selected = dialog.selected_layers()
    if not selected:
        show_message("No layers selected.")
        return None

    return create_action_from_layers(node, selected)


def execute_exr_layers_to_action(*args, **kwargs):
    selection = kwargs.get("selection")
    if selection is None and args:
        selection = args[0]
    return run_exr_layers_to_action(selection)


def custom_ui_action():
    return {
        "name": MENU_NAME,
        "execute": execute_exr_layers_to_action,
        "minimumVersion": "2020.2",
    }


def batch_custom_ui_menu_actions():
    return [
        {
            "name": MENU_GROUP,
            "actions": [custom_ui_action()],
        }
    ]


def media_panel_custom_ui_menu_actions():
    return [
        {
            "name": MENU_GROUP,
            "actions": [custom_ui_action()],
        }
    ]


def get_batch_custom_ui_actions(*args, **kwargs):
    return batch_custom_ui_menu_actions()


def get_media_panel_custom_ui_actions(*args, **kwargs):
    return media_panel_custom_ui_menu_actions()
