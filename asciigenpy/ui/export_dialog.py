from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QSpinBox, 
                             QPushButton, QDialogButtonBox)
from PyQt6.QtGui import QTextDocument, QFont
from PyQt6.QtCore import Qt

class ExportOptionsDialog(QDialog):
    def __init__(self, parent=None, ascii_text="", base_font=None, default_ext=".png"):
        super().__init__(parent)
        self.setWindowTitle("Export Settings")
        self.setModal(True)
        self.setFixedSize(350, 180)
        
        self.ascii_text = ascii_text
        self.base_font = base_font
        self.lines = self.ascii_text.split('\n')
        self.max_chars = max([len(l) for l in self.lines] + [1])

        layout = QVBoxLayout(self)

        # Extension
        ext_layout = QHBoxLayout()
        ext_layout.addWidget(QLabel("Format:"))
        self.ext_combo = QComboBox()
        self.ext_combo.addItems([".png", ".svg"])
        self.ext_combo.setCurrentText(default_ext)
        ext_layout.addWidget(self.ext_combo)
        layout.addLayout(ext_layout)

        # Resolution / Font Size
        size_layout = QHBoxLayout()
        lbl_size = QLabel("Font Size:")
        lbl_size.setToolTip("Higher font size generates exponentially higher resolution images.")
        size_layout.addWidget(lbl_size)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 500)
        self.size_spin.setValue(12)
        self.size_spin.valueChanged.connect(self._update_resolution_label)
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)
        
        # Real-time resolution display
        self.res_label = QLabel("Final Resolution: 0x0")
        self.res_label.setStyleSheet("color: gray;")
        self.res_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.res_label)
        
        # Initial calculation
        self._update_resolution_label()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addStretch()
        layout.addWidget(buttons)
        
    def _update_resolution_label(self):
        if not self.base_font or not self.ascii_text: return
        font_size = self.size_spin.value()
        
        from PyQt6.QtGui import QFontMetrics
        doc = QTextDocument()
        font = QFont(self.base_font)
        font.setPointSize(font_size)
        doc.setDefaultFont(font)
        
        fm = QFontMetrics(font)
        doc_w = fm.horizontalAdvance("A") * (self.max_chars) + (fm.horizontalAdvance("A"))
        doc_h = fm.lineSpacing() * (len(self.lines)) + (fm.lineSpacing())
        
        self.res_label.setText(f"Final Resolution: {doc_w}x{doc_h}")

    def get_options(self):
        return {
            "ext": self.ext_combo.currentText(),
            "font_size": self.size_spin.value(),
        }
