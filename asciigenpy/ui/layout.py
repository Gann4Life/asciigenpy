from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QSlider, QLabel, QTextEdit, 
                             QLineEdit, QGroupBox, QComboBox, QCheckBox, QStyle)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class AsciigenUI(QWidget):
    """
    AsciigenUI: Responsible solely for creating, styling, and placing Qt widgets.
    Adheres to the Single Responsibility Principle by removing UI building boilerplate 
    from the main controller logic.
    """
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Top Action Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        
        self.btn_load = QPushButton()
        self.btn_load.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.btn_load.setToolTip("Import Image")
        self.btn_load.setFixedSize(40, 40)
        top_bar.addWidget(self.btn_load)
        
        self.btn_paste = QPushButton()
        self.btn_paste.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_paste.setToolTip("Paste Image from Clipboard (Ctrl+V)")
        self.btn_paste.setFixedSize(40, 40)
        top_bar.addWidget(self.btn_paste)
        
        self.btn_preview = QPushButton()
        self.btn_preview.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        self.btn_preview.setToolTip("Toggle Preview")
        self.btn_preview.setFixedSize(40, 40)
        self.btn_preview.setCheckable(True)
        top_bar.addWidget(self.btn_preview)

        self.btn_inv = QPushButton()
        self.btn_inv.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_inv.setToolTip("Invert Output")
        self.btn_inv.setFixedSize(40, 40)
        top_bar.addWidget(self.btn_inv)
        
        top_bar.addStretch()
        
        self.btn_copy = QPushButton(" Copy")
        self.btn_copy.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_copy.setToolTip("Copy to Clipboard")
        self.btn_copy.setStyleSheet("font-weight: bold; min-width: 100px; min-height: 40px; background-color: #2b2b2b; color: #eee; border-radius: 4px;")
        top_bar.addWidget(self.btn_copy)

        main_layout.addLayout(top_bar)

        # 2. Content Area Layout
        content_layout = QHBoxLayout()
        
        # 3. Control Panel Sidebar
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(0, 5, 15, 0)
        sidebar.setSpacing(15)
        
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(300)
        sidebar_widget.setLayout(sidebar)
        content_layout.addWidget(sidebar_widget)

        # 3a. Image Adjustments Group
        adj_group = QGroupBox("Image Adjustments")
        adj_layout = QVBoxLayout()
        adj_layout.setSpacing(10)
        
        self.c_label = QLabel("Contrast: 1.0")
        self.c_slider = self._create_slider(5, 50, 10, adj_layout, self.c_label)
        
        self.b_label = QLabel("Brightness: 1.0")
        self.b_slider = self._create_slider(5, 50, 10, adj_layout, self.b_label)
        
        adj_group.setLayout(adj_layout)
        sidebar.addWidget(adj_group)

        # 3b. ASCII Settings Group
        ascii_group = QGroupBox("ASCII Settings")
        ascii_layout = QVBoxLayout()
        ascii_layout.setSpacing(10)
        
        self.w_label = QLabel("Output Width: 120")
        self.w_slider = self._create_slider(20, 600, 120, ascii_layout, self.w_label)
        
        self.h_label = QLabel("Output Height: 60")
        self.h_slider = self._create_slider(10, 300, 60, ascii_layout, self.h_label)
        
        self.aspect_cb = QCheckBox("Keep Aspect Ratio")
        self.aspect_cb.setChecked(True)
        ascii_layout.addWidget(self.aspect_cb)
        
        ascii_layout.addWidget(QLabel("Charset Ramp:"))
        self.charset_combo = QComboBox()
        self.charset_presets = {
            "Standard (10 chars)": " .:-=+*#%@",
            "Detailed (70 chars)": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
            "Blocks": " ░▒▓█",
            "Binary": " 01",
            "Custom": " .:-=+*#%@"
        }
        self.charset_combo.addItems(list(self.charset_presets.keys()))
        ascii_layout.addWidget(self.charset_combo)

        self.charset_input = QLineEdit(self.charset_presets["Standard (10 chars)"])
        ascii_layout.addWidget(self.charset_input)
        
        ascii_group.setLayout(ascii_layout)
        sidebar.addWidget(ascii_group)
        
        sidebar.addStretch()

        # 4. ASCII Preview Workspace
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        # Force a fixed-pitch monospace font that works natively across systems 
        sys_font = QFont("Consolas", 8)
        sys_font.setStyleHint(QFont.StyleHint.Monospace)
        sys_font.setFixedPitch(True)
        self.output.setFont(sys_font)
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        content_layout.addWidget(self.output, 4)
        main_layout.addLayout(content_layout)

    def _create_slider(self, min_v, max_v, def_v, layout, label):
        """Helper to reduce slider configuration boilerplate."""
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_v, max_v)
        s.blockSignals(True) # Prevent initial value setting from triggering heavy ASCII recalculations on boot
        s.setValue(def_v)
        s.blockSignals(False)
        layout.addWidget(label)
        layout.addWidget(s)
        return s

    def apply_theme(self, is_inverted):
        """Changes the output text edit color scheme dynamically."""
        if is_inverted:
            self.output.setStyleSheet("background-color: #000; color: #fff; border: none;")
        else:
            self.output.setStyleSheet("background-color: #fff; color: #000; border: none;")
