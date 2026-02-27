from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath

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
        self._notify_crop_change()

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
            self._notify_crop_change()

    def _notify_crop_change(self):
        # Resolve reference based on whether the label is in a detached window or a dock widget
        app = self.window().parent_app if hasattr(self.window(), 'parent_app') else self.window()
        if hasattr(app, 'on_crop_changed'):
            app.on_crop_changed()
        elif hasattr(app, 'trigger_update'):
            app.trigger_update()

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
    def __init__(self, parent=None):
        super().__init__(parent)
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
            if hasattr(self.parent_app, 'preview_dock'):
                self.parent_app.preview_dock.show()
                self.parent_app.preview_dock.raise_()


    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_V:
            if hasattr(self.parent_app, 'ui'):
                self.parent_app.ui.act_toggle_preview.setChecked(False)
            else:
                self.parent_app.act_toggle_preview.setChecked(False)
            self.parent_app.toggle_preview()
        elif event.key() == Qt.Key.Key_F:
            if hasattr(self.parent_app, 'toggle_invert'):
                self.parent_app.toggle_invert()
        super().keyPressEvent(event)


    @property
    def selection_rect(self):
        return self.label.selection_rect
