import sys
import io
import pyperclip
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QSlider, QLabel, QTextEdit, QFileDialog, QLineEdit,
                             QGroupBox, QComboBox, QCheckBox, QStyle)
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, QTimer, QRectF, QPointF, QSizeF
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QColor, QPainterPath
from PIL import Image, ImageEnhance, ImageOps
from ascii_magic import AsciiArt

class SourceLabel(QWidget):
    """Core Canvas for AsciigenPy: Handles native top-layer drawing for crop area"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = QPixmap()
        self.selection_rect = QRectF()
        self.interaction_state = None
        self.drag_start_pos = QPointF()
        self.drag_start_rect = QRectF()
        self.setMouseTracking(True)
        self._scale_factor = 1.0
        self._offset = QPointF(0, 0)
        self.setMinimumSize(300, 300)

    def map_to_screen(self, rect_or_point):
        if isinstance(rect_or_point, QRectF):
            return QRectF(
                rect_or_point.x() * self._scale_factor + self._offset.x(),
                rect_or_point.y() * self._scale_factor + self._offset.y(),
                rect_or_point.width() * self._scale_factor,
                rect_or_point.height() * self._scale_factor
            )
        else:
            return QPointF(
                rect_or_point.x() * self._scale_factor + self._offset.x(),
                rect_or_point.y() * self._scale_factor + self._offset.y()
            )

    def map_to_image(self, pos):
        return QPointF(
            (pos.x() - self._offset.x()) / self._scale_factor,
            (pos.y() - self._offset.y()) / self._scale_factor
        )

    def get_hit_area(self, pos):
        if self.selection_rect.isNull():
            return 'create'
        
        screen_rect = self.map_to_screen(self.selection_rect)
        handle_size = 12
        
        handles = {
            'tl': screen_rect.topLeft(),
            'tr': screen_rect.topRight(),
            'bl': screen_rect.bottomLeft(),
            'br': screen_rect.bottomRight()
        }
        
        for name, hp in handles.items():
            if QRectF(hp.x() - handle_size, hp.y() - handle_size, handle_size*2, handle_size*2).contains(pos):
                return name
                
        if screen_rect.contains(pos):
            return 'move'
            
        return 'create'

    def mouseMoveEvent(self, event):
        pos = event.position()
        
        if self.interaction_state is None:
            area = self.get_hit_area(pos)
            if area in ('tl', 'br'):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif area in ('tr', 'bl'):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif area == 'move':
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            return

        img_pos = self.map_to_image(pos)
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()
        
        if self.interaction_state == 'create':
            self.selection_rect = QRectF(self.drag_start_pos, img_pos).normalized()
        elif self.interaction_state == 'move':
            delta = img_pos - self.drag_start_pos
            new_rect = self.drag_start_rect.translated(delta)
            if new_rect.left() < 0: new_rect.moveLeft(0)
            if new_rect.top() < 0: new_rect.moveTop(0)
            if new_rect.right() > img_w: new_rect.moveRight(img_w)
            if new_rect.bottom() > img_h: new_rect.moveBottom(img_h)
            self.selection_rect = new_rect
        elif self.interaction_state == 'tl':
            self.selection_rect.setTopLeft(img_pos)
            self.selection_rect = self.selection_rect.normalized()
        elif self.interaction_state == 'tr':
            self.selection_rect.setTopRight(img_pos)
            self.selection_rect = self.selection_rect.normalized()
        elif self.interaction_state == 'bl':
            self.selection_rect.setBottomLeft(img_pos)
            self.selection_rect = self.selection_rect.normalized()
        elif self.interaction_state == 'br':
            self.selection_rect.setBottomRight(img_pos)
            self.selection_rect = self.selection_rect.normalized()
            
        self.selection_rect = self.selection_rect.intersected(QRectF(0, 0, img_w, img_h))
        self.update()
        if hasattr(self.window(), 'parent_app') and self.window().parent_app:
            self.window().parent_app.trigger_update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            area = self.get_hit_area(pos)
            self.interaction_state = area
            self.drag_start_pos = self.map_to_image(pos)
            self.drag_start_rect = QRectF(self.selection_rect)
            
            if area == 'create':
                self.selection_rect = QRectF(self.drag_start_pos, QSizeF())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.interaction_state = None
            if hasattr(self.window(), 'parent_app') and self.window().parent_app:
                self.window().parent_app.trigger_update()

    def paintEvent(self, event):
        if self.original_pixmap.isNull():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        widget_size = self.size()
        pixmap_size = self.original_pixmap.size()
        
        if pixmap_size.width() == 0 or pixmap_size.height() == 0:
            return
            
        scale_x = widget_size.width() / pixmap_size.width()
        scale_y = widget_size.height() / pixmap_size.height()
        self._scale_factor = min(scale_x, scale_y)
        
        new_w = pixmap_size.width() * self._scale_factor
        new_h = pixmap_size.height() * self._scale_factor
        
        self._offset = QPointF((widget_size.width() - new_w) / 2, (widget_size.height() - new_h) / 2)
        
        target_rect = QRectF(self._offset.x(), self._offset.y(), new_w, new_h)
        painter.drawPixmap(target_rect, self.original_pixmap, QRectF(self.original_pixmap.rect()))
        
        if not self.selection_rect.isNull() and self.selection_rect.width() > 0 and self.selection_rect.height() > 0:
            screen_rect = self.map_to_screen(self.selection_rect)
            
            path = QPainterPath()
            path.addRect(QRectF(self.rect()))
            path.addRect(screen_rect)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)
            
            pen = QPen(QColor(0, 153, 255), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(screen_rect)
            
            handle_size = 10
            painter.setBrush(QColor(0, 153, 255))
            for pt in [screen_rect.topLeft(), screen_rect.topRight(), screen_rect.bottomLeft(), screen_rect.bottomRight()]:
                painter.drawRect(QRectF(pt.x() - handle_size/2, pt.y() - handle_size/2, handle_size, handle_size))

class SourceWindow(QWidget):
    """AsciigenPy Image Inspector: Floating reference for crop operations"""
    def __init__(self, parent):
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("AsciigenPy - Source Inspector")
        self.parent_app = parent
        self.label = SourceLabel(self)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)

    def set_image(self, path=None, pixmap=None):
        if path:
            pixmap = QPixmap(path)
        if pixmap:
            self.label.original_pixmap = pixmap
            self.label.selection_rect = QRectF()
            self.label.update()
        
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(pixmap.width(), screen.width() // 2)
        h = min(pixmap.height(), screen.height() // 2)
        self.resize(w, h)
        if hasattr(self.parent_app, 'preview_is_open') and self.parent_app.preview_is_open:
            self.show()

    def closeEvent(self, event):
        if hasattr(self.parent_app, 'preview_is_open'):
            self.parent_app.preview_is_open = False
            self.parent_app.btn_preview.setChecked(False)
        super().closeEvent(event)

    @property
    def selection_rect(self):
        return self.label.selection_rect

class AsciigenPy(QMainWindow):
    """Main Workspace: Handles realtime ASCII engine and parameter management"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AsciigenPy Workspace")
        self.setMinimumSize(1100, 850)
        self.setAcceptDrops(True)
        
        self.img_pil = None
        self.source_win = SourceWindow(self)
        self.is_inverted = False
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.process_ascii)

        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QVBoxLayout(container) # Changed to VBox for Top Bar
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Top Action Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        
        self.btn_load = QPushButton()
        self.btn_load.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.btn_load.setToolTip("Import Image")
        self.btn_load.setFixedSize(40, 40)
        self.btn_load.clicked.connect(self.load_dialog)
        top_bar.addWidget(self.btn_load)
        
        self.btn_paste = QPushButton()
        self.btn_paste.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)) # Simple stand-in icon
        self.btn_paste.setToolTip("Paste Image from Clipboard (Ctrl+V)")
        self.btn_paste.setFixedSize(40, 40)
        self.btn_paste.clicked.connect(self.paste_image)
        top_bar.addWidget(self.btn_paste)
        
        self.btn_preview = QPushButton()
        self.btn_preview.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        self.btn_preview.setToolTip("Toggle Preview")
        self.btn_preview.setFixedSize(40, 40)
        self.btn_preview.setCheckable(True)
        self.preview_is_open = False
        self.btn_preview.clicked.connect(self.toggle_preview)
        top_bar.addWidget(self.btn_preview)

        self.btn_inv = QPushButton()
        self.btn_inv.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_inv.setToolTip("Invert Output")
        self.btn_inv.setFixedSize(40, 40)
        self.btn_inv.clicked.connect(self.toggle_invert)
        top_bar.addWidget(self.btn_inv)
        
        top_bar.addStretch()
        
        self.btn_copy = QPushButton(" Copy")
        self.btn_copy.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_copy.setToolTip("Copy to Clipboard")
        self.btn_copy.clicked.connect(self.to_clip)
        self.btn_copy.setStyleSheet("font-weight: bold; min-width: 100px; min-height: 40px; background-color: #2b2b2b; color: #eee; border-radius: 4px;")
        top_bar.addWidget(self.btn_copy)

        main_layout.addLayout(top_bar)

        # Content Area Layout
        content_layout = QHBoxLayout()
        
        # Control Panel Sidebar
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(0, 5, 15, 0)
        sidebar.setSpacing(15)
        
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(300)
        sidebar_widget.setLayout(sidebar)
        content_layout.addWidget(sidebar_widget)



        # Image Adjustments Group
        adj_group = QGroupBox("Image Adjustments")
        adj_layout = QVBoxLayout()
        adj_layout.setSpacing(10)
        
        self.c_label = QLabel("Contrast: 1.0")
        self.c_slider = self.add_control(5, 50, 10, adj_layout, self.c_label)
        
        self.b_label = QLabel("Brightness: 1.0")
        self.b_slider = self.add_control(5, 50, 10, adj_layout, self.b_label)
        
        adj_group.setLayout(adj_layout)
        sidebar.addWidget(adj_group)

        # ASCII Settings Group
        ascii_group = QGroupBox("ASCII Settings")
        ascii_layout = QVBoxLayout()
        ascii_layout.setSpacing(10)
        
        self.w_label = QLabel("Output Width: 120")
        self.w_slider = self.add_control(20, 600, 120, ascii_layout, self.w_label)
        
        self.h_label = QLabel("Output Height: 60")
        self.h_slider = self.add_control(10, 300, 60, ascii_layout, self.h_label)
        
        self.aspect_cb = QCheckBox("Keep Aspect Ratio")
        self.aspect_cb.setChecked(True)
        self.aspect_cb.stateChanged.connect(self.aspect_changed)
        ascii_layout.addWidget(self.aspect_cb)
        
        # We hook up the sliders to our smart aspect ratio linker
        self.w_slider.valueChanged.connect(self.sync_width)
        self.h_slider.valueChanged.connect(self.sync_height)

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
        self.charset_combo.currentTextChanged.connect(self.on_charset_preset_changed)
        ascii_layout.addWidget(self.charset_combo)

        self.charset_input = QLineEdit(self.charset_presets["Standard (10 chars)"])
        self.charset_input.textEdited.connect(self.on_charset_custom_edited)
        ascii_layout.addWidget(self.charset_input)
        
        ascii_group.setLayout(ascii_layout)
        sidebar.addWidget(ascii_group)
        
        sidebar.addStretch()

        # ASCII Preview Workspace
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Monospace", 7))
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.apply_theme()
        content_layout.addWidget(self.output, 4)
        
        main_layout.addLayout(content_layout)

    def toggle_preview(self):
        self.preview_is_open = not self.preview_is_open
        if self.preview_is_open:
            self.source_win.show()
            self.source_win.raise_()
        else:
            self.source_win.hide()

    def aspect_changed(self):
        if self.aspect_cb.isChecked() and self.img_pil:
            self.sync_width(self.w_slider.value())
            
    def _get_char_aspect(self):
        # Monospace terminal chars are roughly 2:1 aspect ratio (twice as tall as they are wide)
        return 0.5 

    def sync_width(self, val):
        if not self.aspect_cb.isChecked() or not self.img_pil: return
        rect = self.source_win.selection_rect
        if not rect.isNull() and rect.width() > 5 and rect.height() > 5:
            img_aspect = rect.height() / rect.width()
        else:
            img_w, img_h = self.img_pil.size
            img_aspect = img_h / img_w
            
        new_h = int(val * img_aspect * self._get_char_aspect())
        self.h_slider.blockSignals(True)
        self.h_slider.setValue(max(self.h_slider.minimum(), min(self.h_slider.maximum(), new_h)))
        self.h_slider.blockSignals(False)
        self.h_label.setText(f"Output Height: {self.h_slider.value()}")

    def sync_height(self, val):
        if not self.aspect_cb.isChecked() or not self.img_pil: return
        rect = self.source_win.selection_rect
        if not rect.isNull() and rect.width() > 5 and rect.height() > 5:
            img_aspect = rect.width() / rect.height()
        else:
            img_w, img_h = self.img_pil.size
            img_aspect = img_w / img_h
            
        new_w = int(val * img_aspect / self._get_char_aspect())
        self.w_slider.blockSignals(True)
        self.w_slider.setValue(max(self.w_slider.minimum(), min(self.w_slider.maximum(), new_w)))
        self.w_slider.blockSignals(False)
        self.w_label.setText(f"Output Width: {self.w_slider.value()}")

    def on_charset_preset_changed(self, text):
        if text != "Custom":
            self.charset_input.setText(self.charset_presets[text])
        else:
            self.charset_input.setText(self.charset_presets["Custom"])
        self.trigger_update()

    def on_charset_custom_edited(self, text):
        self.charset_presets["Custom"] = text
        if self.charset_combo.currentText() != "Custom":
            self.charset_combo.setCurrentText("Custom")
        self.trigger_update()

    def add_control(self, min_v, max_v, def_v, layout, label):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(def_v)
        s.valueChanged.connect(self.trigger_update)
        layout.addWidget(label)
        layout.addWidget(s)
        return s

    def apply_theme(self):
        if self.is_inverted:
            self.output.setStyleSheet("background-color: #000; color: #fff; border: none;")
        else:
            self.output.setStyleSheet("background-color: #fff; color: #000; border: none;")

    def toggle_invert(self):
        self.is_inverted = not self.is_inverted
        self.apply_theme()
        self.trigger_update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].toLocalFile()
        self.load_image(path)
        
    def paste_image(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        if mime_data.hasImage():
            from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
            qimage = clipboard.image()
            if not qimage.isNull():
                # Write QImage to QByteArray buffer in RAM
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                qimage.save(buffer, "PNG")
                
                # Read from RAM buffer to PIL Image
                pil_buffer = io.BytesIO(byte_array.data())
                self.img_pil = Image.open(pil_buffer).convert("RGB")
                
                # Send the native pixmap directly to inspector GUI
                self.source_win.set_image(pixmap=QPixmap.fromImage(qimage))
                if not self.preview_is_open:
                    self.toggle_preview()
                if self.aspect_cb.isChecked():
                    self.sync_width(self.w_slider.value())
                self.trigger_update()
        else:
            self.output.setPlainText("CLIPBOARD ERROR: No valid image found in clipboard.")

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
            self.paste_image()
        super().keyPressEvent(event)

    def load_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Asset", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.load_image(path)

    def load_image(self, path):
        self.img_pil = Image.open(path).convert("RGB")
        self.source_win.set_image(path)
        if not self.preview_is_open:
            self.toggle_preview()
        if self.aspect_cb.isChecked():
            self.sync_width(self.w_slider.value())
        self.trigger_update()

    def trigger_update(self):
        self.update_timer.start(35)

    def process_ascii(self):
        if not self.img_pil: return
        try:
            rect = self.source_win.selection_rect
            if not rect.isNull() and rect.width() > 5 and rect.height() > 5:
                crop_box = (int(rect.x()), int(rect.y()), int(rect.right()), int(rect.bottom()))
                working_img = self.img_pil.crop(crop_box)
            else:
                working_img = self.img_pil.copy()

            c = self.c_slider.value() / 10.0
            b = self.b_slider.value() / 10.0
            w = self.w_slider.value()
            h = self.h_slider.value()
            
            self.c_label.setText(f"Contrast: {c}")
            self.b_label.setText(f"Brightness: {b}")
            self.w_label.setText(f"Output Width: {w}")
            self.h_label.setText(f"Output Height: {h}")
            
            if self.is_inverted:
                working_img = ImageOps.invert(working_img)
            working_img = ImageEnhance.Contrast(working_img).enhance(c)
            working_img = ImageEnhance.Brightness(working_img).enhance(b)

            # Unified Engine Call
            img_io = io.BytesIO()
            working_img.save(img_io, format='PNG')
            img_io.seek(0)
            
            art = AsciiArt.from_image(img_io)
            # Resize image cleanly to exact dimensions matching terminal char sizes before sending to engine
            resized_img = working_img.resize((w, h), Image.Resampling.LANCZOS)
            res_io = io.BytesIO()
            resized_img.save(res_io, format='PNG')
            res_io.seek(0)
            
            art_resized = AsciiArt.from_image(res_io)
            try:
                # Force engine width slightly larger to ensure our target W is hit post-aspect-calc inside the lib
                res = art_resized.to_ascii(columns=w, char=self.charset_input.text(), width_ratio=1.0)
            except TypeError:
                res = art_resized.to_ascii(columns=w, chars=self.charset_input.text(), width_ratio=1.0)
            
            self.output.setPlainText(res)
            
        except Exception as e:
            self.output.setPlainText(f"RUNTIME ERROR: {e}")

    def to_clip(self):
        try:
            pyperclip.copy(self.output.toPlainText())
        except Exception:
            self.output.setPlainText("CLIPBOARD ERROR: Missing backend (sudo pacman -S wl-clipboard)")

    def closeEvent(self, event):
        self.source_win.close()
        QApplication.quit()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AsciigenPy()
    window.show()
    sys.exit(app.exec())
