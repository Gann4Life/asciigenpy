from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QSlider, QLabel, QTextEdit, 
                             QLineEdit, QGroupBox, QComboBox, QCheckBox, QStyle,
                             QMenuBar, QMenu, QSpinBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction

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
        self._create_menu_bar(main_layout)
        
        # 1. Top Action Bar: Crop Area Controls
        top_bar = QHBoxLayout()
        top_bar.setSpacing(15)
        
        top_bar.addWidget(QLabel("Crop Area: "))
        
        self.crop_x = self._create_spinbox("X:", top_bar, 0, 9999, 0)
        self.crop_y = self._create_spinbox("Y:", top_bar, 0, 9999, 0)
        self.crop_w = self._create_spinbox("Width:", top_bar, 1, 9999, 100)
        self.crop_h = self._create_spinbox("Height:", top_bar, 1, 9999, 100)
        
        self.crop_lock_cb = QCheckBox("Lock Values")
        self.crop_lock_cb.setChecked(False)
        top_bar.addWidget(self.crop_lock_cb)
        
        # Disable them initially until an image is loaded and a crop is active
        self._toggle_crop_inputs(False)
        
        top_bar.addStretch()
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
        
        self.w_label = QLabel("Width: 120")
        self.w_slider = self._create_slider(20, 600, 120, ascii_layout, self.w_label)
        
        self.h_label = QLabel("Height: 60")
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
        
    def _create_spinbox(self, label_text, layout, min_v, max_v, def_v):
        """Helper to create labeled horizontal spinboxes for crop coordinates."""
        layout.addWidget(QLabel(label_text))
        sb = QSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(def_v)
        layout.addWidget(sb)
        return sb
        
    def _toggle_crop_inputs(self, state):
        self.crop_x.setEnabled(state)
        self.crop_y.setEnabled(state)
        self.crop_w.setEnabled(state)
        self.crop_h.setEnabled(state)
        if hasattr(self, 'crop_lock_cb'):
            self.crop_lock_cb.setEnabled(state)

    def _create_menu_bar(self, layout):
        """Constructs the Context Menu Bar at the top of the application."""
        self.menu_bar = QMenuBar()
        layout.setMenuBar(self.menu_bar)
        
        # --- File Menu ---
        self.menu_file = self.menu_bar.addMenu("File")
        
        self.act_new_project = QAction("New Project", self.parent_window)
        self.menu_file.addAction(self.act_new_project)
        
        self.menu_file.addSeparator()
        
        self.act_open_image = QAction("Open Image...", self.parent_window)
        self.act_open_image.setShortcut("Ctrl+O")
        self.menu_file.addAction(self.act_open_image)
        
        self.act_open_project = QAction("Open Project...", self.parent_window)
        self.menu_file.addAction(self.act_open_project)
        
        self.menu_file.addSeparator()
        
        self.menu_recent_images = self.menu_file.addMenu("Recent Images")
        self.menu_recent_projects = self.menu_file.addMenu("Recent Projects")
        
        self.menu_file.addSeparator()
        
        self.act_save_project = QAction("Save Project as .agp", self.parent_window)
        self.act_save_project.setShortcut("Ctrl+S")
        self.menu_file.addAction(self.act_save_project)
        
        self.menu_export = self.menu_file.addMenu("Export As...")
        self.act_exp_txt = QAction("Text Document (.txt)", self.parent_window)
        self.act_exp_png = QAction("Image (.png)", self.parent_window)
        self.act_exp_svg = QAction("Vector (.svg)", self.parent_window)
        self.menu_export.addAction(self.act_exp_txt)
        self.menu_export.addAction(self.act_exp_png)
        self.menu_export.addAction(self.act_exp_svg)
        
        self.menu_file.addSeparator()
        self.act_exit = QAction("Exit", self.parent_window)
        self.menu_file.addAction(self.act_exit)

        # --- Edit Menu ---
        self.menu_edit = self.menu_bar.addMenu("Edit")
        
        self.act_copy = QAction("Copy ASCII to Clipboard", self.parent_window)
        self.act_copy.setShortcut("Ctrl+C")
        self.menu_edit.addAction(self.act_copy)
        
        self.act_paste = QAction("Paste Image from Clipboard", self.parent_window)
        self.act_paste.setShortcut("Ctrl+V")
        self.menu_edit.addAction(self.act_paste)
        
        # --- View Menu ---
        self.menu_view = self.menu_bar.addMenu("View")
        
        self.act_toggle_preview = QAction("Show Image Preview Window", self.parent_window)
        self.act_toggle_preview.setCheckable(True)
        self.act_toggle_preview.setChecked(False)
        self.menu_view.addAction(self.act_toggle_preview)
        
        self.act_invert_processing = QAction("Invert ASCII Calculation", self.parent_window)
        self.act_invert_processing.setCheckable(True)
        self.act_invert_processing.setChecked(False)
        self.menu_view.addAction(self.act_invert_processing)

    def apply_theme(self, is_inverted):
        """Changes the output text edit color scheme dynamically."""
        if is_inverted:
            self.output.setStyleSheet("background-color: #000; color: #fff; border: none;")
        else:
            self.output.setStyleSheet("background-color: #fff; color: #000; border: none;")
