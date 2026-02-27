import sys
import os
import io
import pyperclip
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QSettings, QRectF
from PyQt6.QtGui import QPixmap, QImage, QPainter
from PyQt6.QtSvg import QSvgGenerator
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
        
        self.source_win = SourceWindow(self)
        
        from PyQt6.QtWidgets import QDockWidget
        from PyQt6.QtCore import Qt
        
        self.preview_dock = QDockWidget("Image Component Inspector", self)
        self.preview_dock.setWidget(self.source_win)
        self.preview_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.preview_dock)
        self.preview_dock.hide()
        self.preview_dock.visibilityChanged.connect(self._sync_preview_toggle)
        
        self.is_inverted = False
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.process_ascii)

        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_image_preview)
        
        self._is_modified = False
        self.current_project_path = None

        self._connect_signals()
        self.ui.apply_theme(self.is_inverted)
        self.update_title()

    def _connect_signals(self):
        """Connects all UI widget interactions to controller methods."""
        # Menu Bar Action Hooks
        self.ui.act_open_image.triggered.connect(self.load_dialog)
        self.ui.act_open_project.triggered.connect(self.load_project_dialog)
        self.ui.act_save_project.triggered.connect(self.save_project)
        self.ui.act_exit.triggered.connect(self.close)
        
        self.ui.act_exp_txt.triggered.connect(self.export_txt)
        self.ui.act_exp_png.triggered.connect(lambda: self.export_image(".png"))
        self.ui.act_exp_svg.triggered.connect(lambda: self.export_image(".svg"))
        
        self.ui.act_copy.triggered.connect(self.to_clip)
        self.ui.act_paste.triggered.connect(self.paste_image)
        
        self.ui.act_toggle_preview.triggered.connect(self.toggle_preview)
        self.ui.act_invert_processing.triggered.connect(self.toggle_invert)
        
        self._populate_recent_images()
        self._populate_recent_projects()
        
        # Crop Area Sync Hooks
        self.ui.crop_x.valueChanged.connect(self.apply_manual_crop)
        self.ui.crop_y.valueChanged.connect(self.apply_manual_crop)
        self.ui.crop_w.valueChanged.connect(self.apply_manual_crop)
        self.ui.crop_h.valueChanged.connect(self.apply_manual_crop)
        
        # Adjustments
        self.ui.c_slider.valueChanged.connect(self.trigger_preview_update)
        self.ui.b_slider.valueChanged.connect(self.trigger_preview_update)
        
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
        # Update the boolean tracking flag and sync the dock state
        self.preview_is_open = self.ui.act_toggle_preview.isChecked()
        if self.preview_is_open:
            self.preview_dock.show()
            self.preview_dock.raise_()
        else:
            self.preview_dock.hide()

    def _sync_preview_toggle(self, is_visible):
        self.preview_is_open = is_visible
        self.ui.act_toggle_preview.setChecked(is_visible)

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
                
                old_crop = None
                if hasattr(self.ui, 'crop_lock_cb') and self.ui.crop_lock_cb.isChecked():
                    old_crop = QRectF(self.ui.crop_x.value(), self.ui.crop_y.value(), self.ui.crop_w.value(), self.ui.crop_h.value())
                
                self.source_win.set_image(pixmap=QPixmap.fromImage(qimage))
                self._apply_image_bounds(old_crop)
                
                self.current_project_path = None
                self.mark_modified()
                
                if not self.ui.act_toggle_preview.isChecked():
                    self.ui.act_toggle_preview.setChecked(True)
                    self.toggle_preview()
                if self.ui.aspect_cb.isChecked():
                    self.sync_width(self.ui.w_slider.value())
                self.update_image_preview()
        else:
            self.ui.output.setPlainText("CLIPBOARD ERROR: No valid image found in clipboard.")

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
            self.paste_image()
        elif event.key() == Qt.Key.Key_V:
            self.ui.act_toggle_preview.setChecked(not self.ui.act_toggle_preview.isChecked())
            self.toggle_preview()
        elif event.key() == Qt.Key.Key_F:
            self.ui.act_invert_processing.setChecked(not self.ui.act_invert_processing.isChecked())
            self.toggle_invert()
        super().keyPressEvent(event)

    def serialize_state(self):
        return {
            "crop_x": self.ui.crop_x.value(),
            "crop_y": self.ui.crop_y.value(),
            "crop_w": self.ui.crop_w.value(),
            "crop_h": self.ui.crop_h.value(),
            "contrast": self.ui.c_slider.value(),
            "brightness": self.ui.b_slider.value(),
            "width": self.ui.w_slider.value(),
            "height": self.ui.h_slider.value(),
            "keep_aspect": self.ui.aspect_cb.isChecked(),
            "charset": self.ui.charset_input.text(),
            "invert": self.is_inverted
        }
        
    def deserialize_state(self, state):
        self.ui.crop_x.setValue(state.get("crop_x", 0))
        self.ui.crop_y.setValue(state.get("crop_y", 0))
        self.ui.crop_w.setValue(state.get("crop_w", 100))
        self.ui.crop_h.setValue(state.get("crop_h", 100))
        self.ui.c_slider.setValue(state.get("contrast", 10))
        self.ui.b_slider.setValue(state.get("brightness", 10))
        self.ui.w_slider.setValue(state.get("width", 120))
        self.ui.h_slider.setValue(state.get("height", 60))
        self.ui.aspect_cb.setChecked(state.get("keep_aspect", True))
        self.ui.charset_input.setText(state.get("charset", self.ui.charset_presets["Standard (10 chars)"]))
        
        self.is_inverted = state.get("invert", False)
        if self.is_inverted != self.ui.act_invert_processing.isChecked():
            self.ui.act_invert_processing.setChecked(self.is_inverted)
        self.ui.apply_theme(self.is_inverted)
        
        self.apply_manual_crop()
        self.update_image_preview()
        self.trigger_update()

    def save_project(self):
        if not self.img_pil:
            QMessageBox.warning(self, "No Image", "You must load an image before saving a project.")
            return
            
        last_dir = self.settings.value("last_dir", "")
        # Prevent default OS shortcuts firing during file load state
        path, _ = QFileDialog.getSaveFileName(
            self, "Save AsciigenPy Project", last_dir, "AsciigenPy Project (*.agp)"
        )
        if not path:
            return
            
        if not path.endswith('.agp'):
            path += '.agp'
            
        self.settings.setValue("last_dir", os.path.dirname(path))
        
        try:
            state = self.serialize_state()
            
            # Package into a custom extension ZIP
            import tempfile, json, zipfile
            with tempfile.TemporaryDirectory() as tmpdir:
                img_path = os.path.join(tmpdir, "source.png")
                self.img_pil.save(img_path, "PNG")
                
                conf_path = os.path.join(tmpdir, "config.json")
                with open(conf_path, "w") as f:
                    json.dump(state, f)
                    
                with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(img_path, "source.png")
                    zf.write(conf_path, "config.json")
                    
            self._add_recent_project(path)
            self.current_project_path = path
            self._is_modified = False
            self.update_title()
            
            self.statusBar().showMessage(f"Project saved to {os.path.basename(path)}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save project:\n{e}")

    def load_project_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open AsciigenPy Project", last_dir, "AsciigenPy Project (*.agp)"
        )
        if path:
            self.settings.setValue("last_dir", os.path.dirname(path))
            self.load_project(path)
            
    def load_project(self, path):
        import tempfile, json, zipfile
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                if 'source.png' not in zf.namelist() or 'config.json' not in zf.namelist():
                    raise ValueError("Invalid .agp project format.")
                    
                with tempfile.TemporaryDirectory() as tmpdir:
                    zf.extract('source.png', tmpdir)
                    zf.extract('config.json', tmpdir)
                    
                    # 1. Load the raw image back into the application natively
                    img_path = os.path.join(tmpdir, "source.png")
                    self.load_image(img_path)
                    
                    # 2. Inject the extracted state exactly as it was saved
                    conf_path = os.path.join(tmpdir, "config.json")
                    with open(conf_path, "r") as f:
                        state = json.load(f)
                        
                    self.deserialize_state(state)
                    
            self._add_recent_project(path)
            self.current_project_path = path
            self._is_modified = False
            self.update_title()
            
            self.statusBar().showMessage("Project loaded successfully", 5000)
                    
        except Exception as e:
            QMessageBox.critical(self, "Load Failed", f"Could not open project:\n{e}")

    def load_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        # Prevent default OS shortcuts firing during file load state
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Asset", last_dir, "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.settings.setValue("last_dir", os.path.dirname(path))
            self._add_recent_image(path)
            self.load_image(path)

    def _add_recent_image(self, path):
        # Retrieve the current list of recent files, add the new path to the front, and cap at 5
        recent = self.settings.value("recent_images", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        recent = recent[:5]
        self.settings.setValue("recent_images", recent)
        self._populate_recent_images()

    def _populate_recent_images(self):
        self.ui.menu_recent_images.clear()
        recent = self.settings.value("recent_images", [])
        if not recent:
            self.ui.menu_recent_images.setDisabled(True)
            return
            
        self.ui.menu_recent_images.setDisabled(False)
        for path in recent:
            # We create a dummy action that implicitly passes its path to load_image via a lambda loop closure
            act = self.ui.menu_recent_images.addAction(os.path.basename(path))
            act.setToolTip(path)
            act.triggered.connect(lambda checked, p=path: self.load_image(p))

    def _add_recent_project(self, path):
        recent = self.settings.value("recent_projects", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        recent = recent[:5]
        self.settings.setValue("recent_projects", recent)
        self._populate_recent_projects()

    def _populate_recent_projects(self):
        self.ui.menu_recent_projects.clear()
        recent = self.settings.value("recent_projects", [])
        if not recent:
            self.ui.menu_recent_projects.setDisabled(True)
            return
            
        self.ui.menu_recent_projects.setDisabled(False)
        for path in recent:
            act = self.ui.menu_recent_projects.addAction(os.path.basename(path))
            act.setToolTip(path)
            act.triggered.connect(lambda checked, p=path: self.load_project(p))

    def _apply_image_bounds(self, override_crop=None):
        if self.img_pil:
            w, h = self.img_pil.size
            self.ui.crop_x.setMaximum(w)
            self.ui.crop_y.setMaximum(h)
            self.ui.crop_w.setMaximum(w)
            self.ui.crop_h.setMaximum(h)
            self.ui._toggle_crop_inputs(True)
            
            if override_crop:
                self.ui.crop_x.setValue(int(override_crop.x()))
                self.ui.crop_y.setValue(int(override_crop.y()))
                self.ui.crop_w.setValue(int(override_crop.width()))
                self.ui.crop_h.setValue(int(override_crop.height()))
                self.apply_manual_crop()
            else:
                self.on_crop_changed()

    def load_image(self, path):
        self.img_pil = Image.open(path).convert("RGB")
        
        old_crop = None
        if hasattr(self.ui, 'crop_lock_cb') and self.ui.crop_lock_cb.isChecked():
            old_crop = QRectF(self.ui.crop_x.value(), self.ui.crop_y.value(), self.ui.crop_w.value(), self.ui.crop_h.value())
            
        self.source_win.set_image(path)
        self._apply_image_bounds(old_crop)
        
        self.current_project_path = None
        self.mark_modified()
        
        if not self.ui.act_toggle_preview.isChecked():
            self.ui.act_toggle_preview.setChecked(True)
            self.toggle_preview()
        if self.ui.aspect_cb.isChecked():
            self.sync_width(self.ui.w_slider.value())
        self.update_image_preview()

    def apply_manual_crop(self):
        x = self.ui.crop_x.value()
        y = self.ui.crop_y.value()
        w = self.ui.crop_w.value()
        h = self.ui.crop_h.value()
        self.source_win.label.selection_rect = QRectF(x, y, w, h)
        if hasattr(self.source_win.label, 'original_pixmap') and not self.source_win.label.original_pixmap.isNull():
            self.source_win.label.update()
        self.trigger_update()

    def on_crop_changed(self):
        rect = self.source_win.selection_rect
        self.ui.crop_x.blockSignals(True)
        self.ui.crop_y.blockSignals(True)
        self.ui.crop_w.blockSignals(True)
        self.ui.crop_h.blockSignals(True)
        
        if not rect.isNull():
            self.ui.crop_x.setValue(int(rect.x()))
            self.ui.crop_y.setValue(int(rect.y()))
            self.ui.crop_w.setValue(int(rect.width()))
            self.ui.crop_h.setValue(int(rect.height()))
            
        self.ui.crop_x.blockSignals(False)
        self.ui.crop_y.blockSignals(False)
        self.ui.crop_w.blockSignals(False)
        self.ui.crop_h.blockSignals(False)
        
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

    def update_title(self):
        title = "AsciigenPy Workspace"
        if hasattr(self, 'current_project_path') and self.current_project_path:
            title += f" - {os.path.basename(self.current_project_path)}"
        if getattr(self, '_is_modified', False):
            title += " *"
        self.setWindowTitle(title)
        
    def mark_modified(self):
        if hasattr(self, '_is_modified') and not self._is_modified:
            self._is_modified = True
            self.update_title()
            
    def trigger_preview_update(self):
        self.mark_modified()
        self.preview_timer.start(50)

    def trigger_update(self):
        self.mark_modified()
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
            self.statusBar().showMessage("ASCII art copied to clipboard!", 5000)
        except Exception as e:
            QMessageBox.warning(self, "Clipboard Error", 
                                "Missing clipboard backend.\n\n"
                                "Please ensure you have a clipboard utility installed for your operating system "
                                "(e.g., 'wl-clipboard' or 'xclip' on Linux).")

    def export_txt(self):
        last_dir = self.settings.value("last_dir", "")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as Text", last_dir, "Text Document (*.txt)"
        )
        if path:
            if not path.endswith('.txt'): path += '.txt'
            self.settings.setValue("last_dir", os.path.dirname(path))
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.ui.output.toPlainText())
                self.statusBar().showMessage(f"Exported to {os.path.basename(path)}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Could not export text:\n{e}")

    def export_image(self, initial_ext):
        if not self.ui.output.toPlainText().strip():
            QMessageBox.warning(self, "Empty Workspace", "There is no ASCII art to export!")
            return
            
        from .export_dialog import ExportOptionsDialog
        dialog = ExportOptionsDialog(self, ascii_text=self.ui.output.toPlainText(), base_font=self.ui.output.font(), default_ext=initial_ext)
        if not dialog.exec():
            return
            
        opts = dialog.get_options()
        ext = opts['ext']
        font_size = opts['font_size']
        
        last_dir = self.settings.value("last_dir", "")
        filter_str = "PNG Image (*.png)" if ext == ".png" else "SVG Vector (*.svg)"
        path, _ = QFileDialog.getSaveFileName(self, f"Export as {ext.upper()}", last_dir, filter_str)
        
        if not path: return
        if not path.endswith(ext): path += ext
        self.settings.setValue("last_dir", os.path.dirname(path))
        
        try:
            # Match colors directly to the UI theme
            bg_color = Qt.GlobalColor.black if self.is_inverted else Qt.GlobalColor.white
            text_color = "white" if self.is_inverted else "black"
                
            ascii_text = self.ui.output.toPlainText()
            lines = ascii_text.split('\n')
            max_chars = max([len(l) for l in lines] + [1])
            
            if ext == ".png":
                # Render via QTextDocument for PNG
                from PyQt6.QtGui import QTextDocument, QFont, QFontMetrics
                doc = QTextDocument()
                font = self.ui.output.font()
                font.setPointSize(font_size)
                doc.setDefaultFont(font)
                
                # Use setHtml to hard-force the text color through standard CSS
                doc.setHtml(f"<pre style='color:{text_color}; margin:0;'>{ascii_text}</pre>")
                
                fm = QFontMetrics(font)
                doc_w = fm.horizontalAdvance("A") * (max_chars) + (fm.horizontalAdvance("A"))
                doc_h = fm.lineSpacing() * (len(lines)) + (fm.lineSpacing())
                doc.setTextWidth(doc_w)
                
                img = QImage(int(doc_w), int(doc_h), QImage.Format.Format_ARGB32)
                img.fill(bg_color if bg_color != Qt.GlobalColor.transparent else Qt.GlobalColor.transparent)
                painter = QPainter(img)
                doc.drawContents(painter)
                painter.end()
                img.save(path)
                
            elif ext == ".svg":
                # Build custom SVG XML Manually for true editable text
                import html
                
                # Heuristic mapping for standard monospaced browser rendering
                c_width = font_size * 0.60
                c_height = font_size * 1.20 # Approximate line height
                doc_w = c_width * max_chars
                doc_h = c_height * len(lines) + c_height
                
                bg_hex = "transparent"
                if bg_color == Qt.GlobalColor.white: bg_hex = "#ffffff"
                elif bg_color == Qt.GlobalColor.black: bg_hex = "#000000"
                
                t_color = "#000000" if text_color == "black" else "#ffffff"
                
                svg_lines = []
                svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {doc_w} {doc_h}" width="{doc_w}" height="{doc_h}">')
                if bg_hex != "transparent":
                    svg_lines.append(f'  <rect width="100%" height="100%" fill="{bg_hex}"/>')
                
                svg_lines.append(f'  <text x="0" y="0" font-family="{self.ui.output.font().family()}" font-size="{font_size}px" fill="{t_color}" xml:space="preserve">')
                
                for i, line in enumerate(lines):
                    # SVG Text renders from the baseline, meaning y=0 is cut off. Offset identically by line-height
                    y_pos = (i + 1) * c_height * 0.85
                    escaped = html.escape(line)
                    if not escaped: escaped = " "
                    svg_lines.append(f'    <tspan x="0" y="{y_pos}">{escaped}</tspan>')
                    
                svg_lines.append('  </text>')
                svg_lines.append('</svg>')
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(svg_lines))
                
            self.statusBar().showMessage(f"Exported to {os.path.basename(path)}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export {ext}:\n{e}")

    def closeEvent(self, event):
        if getattr(self, '_is_modified', False):
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save your project before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                self.save_project()
                if getattr(self, '_is_modified', False): # User cancelled save or it failed
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
                
        self.source_win.close()
        QApplication.quit()
        super().closeEvent(event)
