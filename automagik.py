#!/usr/bin/env python3
import sys
import json
import getpass
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QMessageBox,
    QDialog,
    QLineEdit,
    QFormLayout,
    QTextEdit,
    QSplitter,
    QInputDialog,
    QFileDialog,
    QFrame
)

CONFIG_DIR = Path.home() / ".config" / "automagik"
CONFIG_PATH = CONFIG_DIR / "profiles.json"
ICON_PATH = CONFIG_DIR / "Automagikbig.png"
FALLBACK_ICON_PATH = CONFIG_DIR / "AutoMagik.png"
DEFAULT_COUNTDOWN_SECONDS = 10


class ProfileEditorDialog(QDialog):
    """GUI Dialog for creating, editing, and deleting profiles in profiles.json."""
    def __init__(self, profiles_data_raw, config_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.profiles_data_raw = profiles_data_raw
        self.profiles = json.loads(json.dumps(profiles_data_raw.get("profiles", [])))

        self.setWindowTitle("AutoMagik Profile Editor")
        self.setMinimumSize(650, 480)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Profile Selection & Management
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("<b>Profiles:</b>"))
        self.profile_list = QListWidget()
        self.profile_list.currentRowChanged.connect(self.on_profile_selected)
        left_layout.addWidget(self.profile_list)

        profile_btn_layout = QHBoxLayout()
        self.add_profile_btn = QPushButton("Add")
        self.add_profile_btn.clicked.connect(self.add_profile)
        profile_btn_layout.addWidget(self.add_profile_btn)

        self.remove_profile_btn = QPushButton("Remove")
        self.remove_profile_btn.clicked.connect(self.remove_profile)
        profile_btn_layout.addWidget(self.remove_profile_btn)

        left_layout.addLayout(profile_btn_layout)
        splitter.addWidget(left_widget)

        # Right Panel: Selected Profile Form
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self.update_current_profile_data)
        form_layout.addRow("Name:", self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.textChanged.connect(self.update_current_profile_data)
        form_layout.addRow("Description:", self.desc_input)

        # Icon row with Browse button
        icon_layout = QHBoxLayout()
        self.icon_input = QLineEdit()
        self.icon_input.textChanged.connect(self.update_current_profile_data)
        icon_layout.addWidget(self.icon_input)

        self.icon_browse_btn = QPushButton("Browse...")
        self.icon_browse_btn.clicked.connect(self.browse_icon)
        icon_layout.addWidget(self.icon_browse_btn)

        form_layout.addRow("Icon (Theme/Path):", icon_layout)

        self.default_checkbox = QCheckBox("Set as Default Profile")
        self.default_checkbox.toggled.connect(self.on_default_toggled)
        form_layout.addRow("", self.default_checkbox)

        right_layout.addLayout(form_layout)

        right_layout.addWidget(QLabel("<b>Commands (one per line):</b>"))
        self.commands_edit = QTextEdit()
        self.commands_edit.textChanged.connect(self.update_current_profile_data)
        right_layout.addWidget(self.commands_edit)

        splitter.addWidget(right_widget)
        splitter.setSizes([200, 450])
        main_layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Config")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("font-weight: bold;")
        save_btn.clicked.connect(self.save_and_accept)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

        self.populate_profile_list()
        if self.profile_list.count() > 0:
            self.profile_list.setCurrentRow(0)

    def populate_profile_list(self):
        self.profile_list.blockSignals(True)
        self.profile_list.clear()
        for prof in self.profiles:
            item_text = prof.get("name", "Unnamed Profile")
            if prof.get("default", False):
                item_text += " (Default)"
            self.profile_list.addItem(item_text)
        self.profile_list.blockSignals(False)

    def on_profile_selected(self, index):
        if index < 0 or index >= len(self.profiles):
            self.clear_form()
            return

        prof = self.profiles[index]
        self.block_form_signals(True)

        self.name_input.setText(prof.get("name", ""))
        self.desc_input.setText(prof.get("description", ""))
        self.icon_input.setText(prof.get("icon", ""))
        self.default_checkbox.setChecked(prof.get("default", False))

        commands = prof.get("commands", [])
        self.commands_edit.setPlainText("\n".join(commands))

        self.block_form_signals(False)

    def block_form_signals(self, block: bool):
        self.name_input.blockSignals(block)
        self.desc_input.blockSignals(block)
        self.icon_input.blockSignals(block)
        self.default_checkbox.blockSignals(block)
        self.commands_edit.blockSignals(block)

    def clear_form(self):
        self.block_form_signals(True)
        self.name_input.clear()
        self.desc_input.clear()
        self.icon_input.clear()
        self.default_checkbox.setChecked(False)
        self.commands_edit.clear()
        self.block_form_signals(False)

    def update_current_profile_data(self):
        index = self.profile_list.currentRow()
        if index < 0 or index >= len(self.profiles):
            return

        prof = self.profiles[index]
        prof["name"] = self.name_input.text()
        prof["description"] = self.desc_input.text()
        prof["icon"] = self.icon_input.text()

        cmds_raw = self.commands_edit.toPlainText().splitlines()
        prof["commands"] = [c.strip() for c in cmds_raw if c.strip()]

        item = self.profile_list.item(index)
        if item:
            item_text = prof["name"]
            if prof.get("default", False):
                item_text += " (Default)"
            item.setText(item_text)

    def on_default_toggled(self, checked: bool):
        index = self.profile_list.currentRow()
        if index < 0 or index >= len(self.profiles):
            return

        if checked:
            for i, p in enumerate(self.profiles):
                p["default"] = (i == index)
        else:
            self.profiles[index]["default"] = False

        self.populate_profile_list()
        self.profile_list.setCurrentRow(index)

    def browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Icon Image",
            str(Path.home()),
            "Image Files (*.png *.svg *.xpm *.jpg);;All Files (*)"
        )
        if file_path:
            self.icon_input.setText(file_path)

    def add_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name:")
        if ok and name.strip():
            new_id = name.lower().replace(" ", "_")
            new_profile = {
                "id": new_id,
                "name": name.strip(),
                "icon": "preferences-desktop",
                "description": "",
                "commands": []
            }
            self.profiles.append(new_profile)
            self.populate_profile_list()
            self.profile_list.setCurrentRow(len(self.profiles) - 1)

    def remove_profile(self):
        index = self.profile_list.currentRow()
        if index < 0 or index >= len(self.profiles):
            return

        prof_name = self.profiles[index].get("name", "this profile")
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete profile '{prof_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.profiles[index]
            self.populate_profile_list()
            if self.profiles:
                self.profile_list.setCurrentRow(max(0, index - 1))
            else:
                self.clear_form()

    def save_and_accept(self):
        self.profiles_data_raw["profiles"] = self.profiles
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.profiles_data_raw, f, indent=2)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save profile configuration:\n{e}")


class AutoMagikWindow(QMainWindow):
    def __init__(self, profiles_data, config_path):
        super().__init__()
        self.config_path = config_path
        self.profiles_data_raw = profiles_data
        self.profiles_data = profiles_data.get("profiles", [])

        self.countdown_duration = profiles_data.get("countdown_seconds", DEFAULT_COUNTDOWN_SECONDS)
        self.time_left = self.countdown_duration

        self.setWindowTitle("AutoMagik — Autostart Profile Selector")
        self.setMinimumSize(640, 480)

        self.set_app_icon()

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.init_ui()

        if self.auto_launch_checkbox.isChecked():
            self.setup_timer()
        else:
            self.timer_label.setText("Auto-launch disabled.")

    def set_app_icon(self):
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        elif FALLBACK_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(FALLBACK_ICON_PATH)))
        else:
            local_icon = Path(__file__).parent / "Automagikbig.png"
            if local_icon.exists():
                self.setWindowIcon(QIcon(str(local_icon)))

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header section with icon on the left of title and subtitle
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        icon_label = QLabel()
        logo_pixmap = self.get_header_pixmap()
        if not logo_pixmap.isNull():
            icon_label.setPixmap(logo_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        header_layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        username = getpass.getuser().capitalize()
        title = QLabel(f"Welcome back, {username}!")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        text_layout.addWidget(title)

        subtitle = QLabel("Select your AutoMagik profile to launch session applications:")
        text_layout.addWidget(subtitle)

        header_layout.addLayout(text_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Middle Content Layout (Presets on Left, Description Panel on Right)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)

        # Main Profile List (Left Side)
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.itemSelectionChanged.connect(self.on_profile_selection_changed)
        content_layout.addWidget(self.list_widget, stretch=1)

        # Description Panel (Right Side)
        desc_panel = QFrame()
        desc_panel.setObjectName("descPanel")
        desc_panel.setFrameShape(QFrame.Shape.NoFrame)
        desc_panel.setStyleSheet("""
            QFrame#descPanel {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        desc_layout = QVBoxLayout(desc_panel)
        desc_layout.setContentsMargins(12, 12, 12, 12)
        desc_layout.setSpacing(8)

        desc_title = QLabel("Preset Description:")
        desc_title.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #aaa;")
        desc_layout.addWidget(desc_title)

        self.desc_display_label = QLabel("No profile selected.")
        self.desc_display_label.setWordWrap(True)
        self.desc_display_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.desc_display_label.setStyleSheet("font-size: 10pt; background: transparent;")
        desc_layout.addWidget(self.desc_display_label, stretch=1)

        content_layout.addWidget(desc_panel, stretch=1)

        layout.addLayout(content_layout)

        self.populate_main_profile_list()

        # Auto-launch Controls Layout
        auto_launch_layout = QHBoxLayout()

        is_auto_enabled = self.profiles_data_raw.get("auto_launch_enabled", True)
        self.auto_launch_checkbox = QCheckBox("Enable auto-launch in:")
        self.auto_launch_checkbox.setChecked(is_auto_enabled)
        self.auto_launch_checkbox.toggled.connect(self.on_auto_launch_toggled)
        auto_launch_layout.addWidget(self.auto_launch_checkbox)

        self.spin_box = QSpinBox()
        self.spin_box.setRange(1, 60)
        self.spin_box.setSuffix("s")
        self.spin_box.setValue(self.countdown_duration)
        self.spin_box.setEnabled(is_auto_enabled)
        self.spin_box.valueChanged.connect(self.on_countdown_changed)
        auto_launch_layout.addWidget(self.spin_box)

        auto_launch_layout.addStretch()

        self.timer_label = QLabel()
        self.timer_label.setStyleSheet("color: #888; font-style: italic;")
        auto_launch_layout.addWidget(self.timer_label)

        layout.addLayout(auto_launch_layout)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()

        self.edit_btn = QPushButton("Edit Profiles...")
        self.edit_btn.setIcon(QIcon.fromTheme("preferences-system", QIcon.fromTheme("configure")))
        self.edit_btn.clicked.connect(self.open_profile_editor)
        btn_layout.addWidget(self.edit_btn)

        btn_layout.addStretch()

        self.skip_btn = QPushButton("Skip All")
        self.skip_btn.clicked.connect(self.cancel_and_close)
        btn_layout.addWidget(self.skip_btn)

        self.launch_btn = QPushButton()
        self.launch_btn.setDefault(True)
        self.launch_btn.setStyleSheet("font-weight: bold;")
        self.launch_btn.clicked.connect(self.launch_profile)
        btn_layout.addWidget(self.launch_btn)

        layout.addLayout(btn_layout)
        self.update_launch_button_text()

    def get_header_pixmap(self) -> QPixmap:
        """Finds and loads Automagikbig.png or fallbacks."""
        if ICON_PATH.exists():
            return QPixmap(str(ICON_PATH))
        if FALLBACK_ICON_PATH.exists():
            return QPixmap(str(FALLBACK_ICON_PATH))

        local_icon = Path(__file__).parent / "Automagikbig.png"
        if local_icon.exists():
            return QPixmap(str(local_icon))

        return QPixmap()

    def populate_main_profile_list(self):
        self.list_widget.clear()
        self.profiles_data = self.profiles_data_raw.get("profiles", [])

        default_row = 0
        for index, profile in enumerate(self.profiles_data):
            item = QListWidgetItem(profile.get("name", "Unnamed Profile"))

            icon_spec = profile.get("icon", "exec")
            icon = self.resolve_icon(icon_spec)
            item.setIcon(icon)

            item.setData(Qt.UserRole, profile)
            self.list_widget.addItem(item)

            if profile.get("default", False):
                default_row = index

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(default_row)

    def on_profile_selection_changed(self):
        self.stop_timer()
        current_item = self.list_widget.currentItem()
        if current_item:
            profile = current_item.data(Qt.UserRole)
            desc = profile.get("description", "").strip()
            if desc:
                self.desc_display_label.setText(desc)
            else:
                self.desc_display_label.setText("No description provided for this profile.")
        else:
            self.desc_display_label.setText("No profile selected.")

    def open_profile_editor(self):
        self.stop_timer()
        dialog = ProfileEditorDialog(self.profiles_data_raw, self.config_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.reload_config()

    def reload_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.profiles_data_raw = json.load(f)
            self.populate_main_profile_list()
        except Exception as e:
            print(f"Failed to reload config: {e}", file=sys.stderr)

    def setup_timer(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)
        self.timer.start(1000)
        self.update_timer_display()

    def on_timer_tick(self):
        self.time_left -= 1
        if self.time_left <= 0:
            self.stop_timer()
            self.launch_profile()
        else:
            self.update_timer_display()

    def stop_timer(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            self.update_launch_button_text()

    def on_auto_launch_toggled(self, checked: bool):
        self.spin_box.setEnabled(checked)
        self.save_config_key("auto_launch_enabled", checked)

        if checked:
            self.time_left = self.countdown_duration
            self.setup_timer()
        else:
            self.stop_timer()
            self.timer_label.setText("Auto-launch disabled.")
            self.update_launch_button_text()

    def on_countdown_changed(self, new_value: int):
        self.countdown_duration = new_value
        self.time_left = new_value
        self.save_config_key("countdown_seconds", new_value)

        if self.auto_launch_checkbox.isChecked():
            self.setup_timer()

    def save_config_key(self, key: str, value):
        self.profiles_data_raw[key] = value
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.profiles_data_raw, f, indent=2)
        except Exception as e:
            print(f"Failed to update '{key}' preference: {e}", file=sys.stderr)

    def update_timer_display(self):
        self.timer_label.setText(
            f"Auto-launching in {self.time_left} second{'s' if self.time_left != 1 else ''}..."
        )
        self.update_launch_button_text()

    def update_launch_button_text(self):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.launch_btn.setText(f"Launch Selected ({self.time_left}s)")
        else:
            self.launch_btn.setText("Launch Selected")

    def resolve_icon(self, icon_spec: str) -> QIcon:
        path = Path(icon_spec).expanduser()
        if path.is_absolute() and path.exists():
            return QIcon(str(path))

        return QIcon.fromTheme(icon_spec, QIcon.fromTheme("exec"))

    def cancel_and_close(self):
        self.stop_timer()
        self.close()

    def launch_profile(self):
        self.stop_timer()
        current_item = self.list_widget.currentItem()
        if not current_item:
            self.close()
            return

        profile = current_item.data(Qt.UserRole)
        commands = profile.get("commands", [])

        for cmd in commands:
            try:
                subprocess.Popen(
                    cmd,
                    shell=True,
                    start_new_session=True
                )
            except Exception as e:
                print(f"Failed to execute '{cmd}': {e}", file=sys.stderr)

        self.close()


def load_config():
    if not CONFIG_PATH.exists():
        local_config = Path(__file__).parent / "profiles.json"
        if local_config.exists():
            return local_config, local_config
    return CONFIG_PATH, CONFIG_PATH


def main():
    import os
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

    app = QApplication(sys.argv)

    app.setApplicationName("AutoMagik")
    app.setDesktopFileName("automagik")

    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    elif FALLBACK_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(FALLBACK_ICON_PATH)))
    else:
        local_icon = Path(__file__).parent / "Automagikbig.png"
        if local_icon.exists():
            app.setWindowIcon(QIcon(str(local_icon)))

    config_file, actual_path = load_config()
    if not config_file.exists():
        QMessageBox.critical(
            None,
            "AutoMagik Error",
            f"Configuration file not found at:\n{config_file}"
        )
        sys.exit(1)

    try:
        with open(config_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        QMessageBox.critical(
            None,
            "AutoMagik Error",
            f"Failed to parse profiles JSON:\n{e}"
        )
        sys.exit(1)

    window = AutoMagikWindow(data, actual_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
