
# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QApplication, QDockWidget, QHBoxLayout, QLabel,
                            QLineEdit, QMainWindow, QWidget)

# Local imports
from spyderlib.widgets.internalshell import InternalShell


class MyWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        label = QLabel("Imagine an extraordinary complex widget right here...")
        self.edit = QLineEdit("Text")
        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.edit)
        self.setLayout(layout)

    def get_text(self):
        """Return sample edit text"""
        return self.edit.text()

    def set_text(self, text):
        """Set sample edit text"""
        self.edit.setText(text)


class MyWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # Set this very simple widget as central widget
        widget = MyWidget()
        self.setCentralWidget(widget)

        # Create the console widget
        font = QFont("Courier new")
        font.setPointSize(10)
        ns = {'win': self, 'widget': widget}
        msg = "Try for example: widget.set_text('foobar') or win.close()"
        # Note: by default, the internal shell is multithreaded which is safer
        # but not compatible with graphical user interface creation.
        # For example, if you need to plot data with Matplotlib, you will need
        # to pass the option: multithreaded=False
        self.console = cons = InternalShell(self, namespace=ns, message=msg)

        # Setup the console widget
        cons.set_font(font)
        cons.set_codecompletion_auto(True)
        cons.set_calltips(True)
        cons.setup_calltips(size=600, font=font)
        cons.setup_completion(size=(300, 180), font=font)
        console_dock = QDockWidget("Console", self)
        console_dock.setWidget(cons)

        # Add the console widget to window as a dockwidget
        self.addDockWidget(Qt.BottomDockWidgetArea, console_dock)

        self.resize(800, 600)

    def closeEvent(self, event):
        self.console.exit_interpreter()
        event.accept()


def main():
    app = QApplication([])
    win = MyWindow()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
