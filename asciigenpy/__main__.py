import sys
from PyQt6.QtWidgets import QApplication
from asciigenpy.ui.main_window import AsciigenPy

def main():
    app = QApplication(sys.argv)
    
    import qdarktheme
    app.setStyleSheet(qdarktheme.load_stylesheet())
    
    window = AsciigenPy()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
