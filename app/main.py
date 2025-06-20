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










# def delete(self):
#     """
#     Irreversibly deletes the drawing.
#     """
#     try:
#         # Step 1: Detach and undefine from JS
#         self.run_script(f'''
#             try {{
#                 if (typeof {self.id} !== 'undefined') {{
#                     {self.id}.detach();
#                     {self.id} = undefined;
#                 }}
#             }} catch (e) {{
#                 console.error("Error detaching drawing: {self.id}", e);
#             }}
#         ''')
#     except Exception as e:
#         print(f"[Error] JS detach failed for {self.id}: {e}")

#     try:
#         # Step 2: Remove from internal drawing tool registry (fixes the bug)
#         self.run_script(f'''
#             try {{
#                 const idx = {self.chart.id}.toolBox._drawingTool._drawings.findIndex(obj => obj._callbackName === "{self.id}");
#                 if (idx !== -1)
#                     {self.chart.id}.toolBox._drawingTool._drawings.splice(idx, 1);
#             }} catch (e) {{
#                 console.error("Error cleaning drawing tool for {self.id}", e);
#             }}
#         ''')
#     except Exception as e:
#         print(f"[Error] Failed to clean drawingTool for {self.id}: {e}")

#     try:
#         # Step 3: Remove Python-side handler
#         if self.id in self.win.handlers:
#             del self.win.handlers[self.id]
#             print(f"[Clean] Cleared Python callback for {self.id}")
#     except Exception as e:
#         print(f"[Error] Handler cleanup failed for {self.id}: {e}")

# def options(self, color='#1E80F0', style='solid', width=4):
#     self.run_script(f'''{self.id}.applyOptions({{
#         lineColor: '{color}',
#         lineStyle: {as_enum(style, LINE_STYLE)},
#         width: {width},
#     }})''')