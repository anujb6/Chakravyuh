import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui.main_window import MainWindow

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

def main():
    app = QApplication(sys.argv)
    
    with open('styles/dark_theme.qss', 'r') as f:
        app.setStyleSheet(f.read())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
