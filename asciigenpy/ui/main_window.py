import sys
import os
import io
import pyperclip
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image, ImageEnhance, ImageOps
from ascii_magic import AsciiArt

from .inspector import SourceWindow
from .layout import AsciigenUI

class AsciigenPy(QMainWindow):
    """
    Main Controller: Handles application logic, settings persistence, 
    and the real-time core ASCII generation loop while relying on AsciigenUI for visual structure. 
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AsciigenPy Workspace")
        self.setMinimumSize(1100, 850)
        self.setAcceptDrops(True)
        
        # Load external layout builder
        self.ui = AsciigenUI(self)
        self.setCentralWidget(self.ui)
        
        # Using QSettings("Organization", "Application")
        # Standardizing organization as "asciigenpy" produces ~/.config/asciigenpy/AsciigenPy.conf cleanly
        self.settings = QSettings("asciigenpy", "AsciigenPy")
        
        self.img_pil = None
        self.source_win = SourceWindow(self)
        self.is_inverted = False
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.process_ascii)

        self._connect_signals()
        self.ui.apply_theme(self.is_inverted)

    def _connect_signals(self):
        """Connects all UI widget interactions to controller methods."""
        # Top Bar
        self.ui.btn_load.clicked.connect(self.load_dialog)
        self.ui.btn_paste.clicked.connect(self.paste_image)
        self.ui.btn_preview.clicked.connect(self.toggle_preview)
        self.ui.btn_inv.clicked.connect(self.toggle_invert)
        self.ui.btn_copy.clicked.connect(self.to_clip)
        
        # Adjustments
        self.ui.c_slider.valueChanged.connect(self.update_image_preview)
        self.ui.b_slider.valueChanged.connect(self.update_image_preview)
        
        # ASCII Rules
        self.ui.w_slider.valueChanged.connect(self.sync_width)
        self.ui.h_slider.valueChanged.connect(self.sync_height)
        self.ui.w_slider.valueChanged.connect(self.trigger_update)
        self.ui.h_slider.valueChanged.connect(self.trigger_update)
        self.ui.aspect_cb.stateChanged.connect(self.aspect_changed)
        self.ui.aspect_cb.stateChanged.connect(self.trigger_update)
        self.ui.charset_combo.currentTextChanged.connect(self.on_charset_preset_changed)
        self.ui.charset_input.textEdited.connect(self.on_charset_custom_edited)

    def toggle_preview(self):
        # Using self.ui.btn_preview because btn_preview is a checkable state property we need to track
        self.preview_is_open = self.ui.btn_preview.isChecked()
        if self.preview_is_open:
            self.source_win.show()
            self.source_win.raise_()
        else:
            self.source_win.hide()

    def aspect_changed(self):
        if self.ui.aspect_cb.isChecked() and self.img_pil:
            self.sync_width(self.ui.w_slider.value())
            
    def _get_char_aspect(self):
        # Monospace terminal chars are roughly 2:1 aspect ratio (twice as tall as they are wide)
        return 0.5 

    def sync_width(self, val):
        if not self.ui.aspect_cb.isChecked() or not self.img_pil: return
        rect = self.source_win.selection_rect
        if not rect.isNull() and rect.width() > 5 and rect.height() > 5:
            img_aspect = rect.height() / rect.width()
        else:
            img_w, img_h = self.img_pil.size
            img_aspect = img_h / img_w
            
        new_h = int(val * img_aspect * self._get_char_aspect())
        self.ui.h_slider.blockSignals(True)
        self.ui.h_slider.setValue(max(self.ui.h_slider.minimum(), min(self.ui.h_slider.maximum(), new_h)))
        self.ui.h_slider.blockSignals(False)
        self.ui.h_label.setText(f"Height: {self.ui.h_slider.value()}")

    def sync_height(self, val):
        if not self.ui.aspect_cb.isChecked() or not self.img_pil: return
        rect = self.source_win.selection_rect
        if not rect.isNull() and rect.width() > 5 and rect.height() > 5:
            img_aspect = rect.width() / rect.height()
        else:
            img_w, img_h = self.img_pil.size
            img_aspect = img_w / img_h
            
        new_w = int(val * img_aspect / self._get_char_aspect())
        self.ui.w_slider.blockSignals(True)
        self.ui.w_slider.setValue(max(self.ui.w_slider.minimum(), min(self.ui.w_slider.maximum(), new_w)))
        self.ui.w_slider.blockSignals(False)
        self.ui.w_label.setText(f"Width: {self.ui.w_slider.value()}")

    def on_charset_preset_changed(self, text):
        if text != "Custom":
            self.ui.charset_input.setText(self.ui.charset_presets[text])
        else:
            self.ui.charset_input.setText(self.ui.charset_presets["Custom"])
        self.trigger_update()

    def on_charset_custom_edited(self, text):
        self.ui.charset_presets["Custom"] = text
        if self.ui.charset_combo.currentText() != "Custom":
            self.ui.charset_combo.setCurrentText("Custom")
        self.trigger_update()

    def toggle_invert(self):
        self.is_inverted = not self.is_inverted
        self.ui.apply_theme(self.is_inverted)
        self.update_image_preview()

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
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                qimage.save(buffer, "PNG")
                
                pil_buffer = io.BytesIO(byte_array.data())
                self.img_pil = Image.open(pil_buffer).convert("RGB")
                
                self.source_win.set_image(pixmap=QPixmap.fromImage(qimage))
                if not self.ui.btn_preview.isChecked():
                    self.ui.btn_preview.setChecked(True)
                    self.toggle_preview()
                if self.ui.aspect_cb.isChecked():
                    self.sync_width(self.ui.w_slider.value())
                self.update_image_preview()
        else:
            self.ui.output.setPlainText("CLIPBOARD ERROR: No valid image found in clipboard.")

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
            self.paste_image()
        super().keyPressEvent(event)

    def load_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        # Prevent default OS shortcuts firing during file load state
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Asset", last_dir, "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.settings.setValue("last_dir", os.path.dirname(path))
            self.load_image(path)

    def load_image(self, path):
        self.img_pil = Image.open(path).convert("RGB")
        self.source_win.set_image(path)
        if not self.ui.btn_preview.isChecked():
            self.ui.btn_preview.setChecked(True)
            self.toggle_preview()
        if self.ui.aspect_cb.isChecked():
            self.sync_width(self.ui.w_slider.value())
        self.update_image_preview()

    def on_crop_changed(self):
        if self.ui.aspect_cb.isChecked() and self.img_pil:
            self.sync_width(self.ui.w_slider.value())
        self.trigger_update()

    def apply_image_modifiers(self, img):
        """
        STANDARD IMAGE PIPELINE:
        ========================
        Any future parameters that alter the image visually (filters, colors, contrast, etc.) 
        MUST be implemented inside this method. Do NOT put isolated modifiers directly in process_ascii. 
        This guarantees that the UI preview window and the ASCII generation engine 
        are always 100% synchronized in how they process the image.
        """
        c = self.ui.c_slider.value() / 10.0
        b = self.ui.b_slider.value() / 10.0
        
        # We process the labels here too so they always stay synced with the state
        self.ui.c_label.setText(f"Contrast: {c}")
        self.ui.b_label.setText(f"Brightness: {b}")

        if self.is_inverted:
            img = ImageOps.invert(img)
        img = ImageEnhance.Contrast(img).enhance(c)
        img = ImageEnhance.Brightness(img).enhance(b)
        
        return img

    def update_image_preview(self):
        """Re-generates the inspector preview pixmap through the standard pipeline."""
        if self.img_pil:
            try:
                # Apply the standard pipeline to the base image for the inspector and cache it globally
                self.processed_img_pil = self.apply_image_modifiers(self.img_pil.copy())
                
                # Fast PIL -> QPixmap conversion
                if self.processed_img_pil.mode != "RGB":
                    self.processed_img_pil = self.processed_img_pil.convert("RGB")
                    
                data = self.processed_img_pil.tobytes("raw", "RGB")
                qimage = QImage(data, self.processed_img_pil.width, self.processed_img_pil.height, self.processed_img_pil.width * 3, QImage.Format.Format_RGB888)
                
                # Update the background texture (does not reset the window size or crop selection)
                self.source_win.label.original_pixmap = QPixmap.fromImage(qimage)
                self.source_win.label.update()
            except Exception as e:
                self.ui.output.setPlainText(f"PREVIEW ERROR: {e}")
                
        # Continues the cascade to compute the ASCII text rendering
        self.trigger_update()

    def trigger_update(self):
        # Use a short debounce (35ms) to keep image transformations and ASCII rendering feeling real-time and smooth
        self.update_timer.start(35)

    def process_ascii(self):
        if not hasattr(self, 'processed_img_pil') or not self.processed_img_pil:
            return
            
        try:
            rect = self.source_win.selection_rect
            if not rect.isNull() and rect.width() > 5 and rect.height() > 5:
                crop_box = (int(rect.x()), int(rect.y()), int(rect.right()), int(rect.bottom()))
                working_img = self.processed_img_pil.crop(crop_box)
            else:
                working_img = self.processed_img_pil.copy()

            w = self.ui.w_slider.value()
            h = self.ui.h_slider.value()
            
            self.ui.w_label.setText(f"Width: {w}")
            self.ui.h_label.setText(f"Height: {h}")

            try:
                # ascii_magic inherently maps Dark (0) -> index 0 (Space) and Light (255) -> index N (@).
                # To map the user's conceptual "White = Nothing, Dark = Something" pattern directly 
                # onto the visual state of the Preview Window, we must always invert the luminosity 
                # simply as an adapter for ascii_magic's scale expectation.
                working_img = ImageOps.invert(working_img)
                    
                charset = self.ui.charset_input.text()

                if hasattr(AsciiArt, 'from_pillow_image'):
                    resized_img = working_img.resize((w, h), Image.Resampling.LANCZOS)
                    art_resized = AsciiArt.from_pillow_image(resized_img)
                else:
                    resized_img = working_img.resize((w, h), Image.Resampling.LANCZOS)
                    res_io = io.BytesIO()
                    resized_img.save(res_io, format='PNG')
                    res_io.seek(0)
                    art_resized = AsciiArt.from_image(res_io)

                try:
                    res = art_resized.to_ascii(columns=w, char=charset, width_ratio=1.0)
                except TypeError:
                    res = art_resized.to_ascii(columns=w, chars=charset, width_ratio=1.0)
                
                self.ui.output.setPlainText(res)
            except Exception as inner_e:
                self.ui.output.setPlainText(f"ASCII ENGINE ERROR: {inner_e}")

            
        except Exception as e:
            self.ui.output.setPlainText(f"RUNTIME ERROR: {e}")

    def to_clip(self):
        try:
            pyperclip.copy(self.ui.output.toPlainText())
            self.ui.btn_copy.setText(" Copied!")
            QTimer.singleShot(2000, lambda: self.ui.btn_copy.setText(" Copy"))
        except Exception as e:
            QMessageBox.warning(self, "Clipboard Error", 
                                "Missing clipboard backend.\n\n"
                                "Please ensure you have a clipboard utility installed for your operating system "
                                "(e.g., 'wl-clipboard' or 'xclip' on Linux).")

    def closeEvent(self, event):
        self.source_win.close()
        QApplication.quit()
        super().closeEvent(event)
