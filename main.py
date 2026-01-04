import sys
from PyQt6.QtWidgets import QApplication
from ui.mainwindow import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Optional: Set global font or style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
