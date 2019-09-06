from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QListView, QLabel, QVBoxLayout, QApplication

from spyder.config.gui import get_font
from spyder.config.manager import CONF


class Kite_CTA(QListView):
    def __init__(self, parent):
        # Only QListView provides the correct border, highlight on focus
        QListView.__init__(self, parent)

        self.parent_widget = parent

        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        # Reuse completion window size
        self.resize(*CONF.get('main', 'kite_cta/size'))
        self.setFont(get_font())

        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.setup_message()
        self.setup_links()
        self.setup_dismissal_link()

        self.layout.insertStretch(-1)
        self.hide()

    def show(self):
        # TODO: Check if Kite is already active.
        if CONF.get('main', 'show_kite_cta') and self.isHidden():
            self.orient()
            QListView.show(self)

    def setup_message(self):
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        # TODO: Localization
        self.label.setText(
            "No completions found. You can get more completions by installing Kite.")
        self.layout.addWidget(self.label)

    def setup_links(self):
        self.install_link = QLabel(self)
        self.install_link.setAlignment(
            Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        # TODO: Localization
        self.install_link.setText(
            "<html><head/><body><p><a href=\"https://kite.com/download/\">Install Kite</span></a></p></body></html>")
        self.install_link.setOpenExternalLinks(True)
        self.layout.addWidget(self.install_link)

        self.info_link = QLabel(self)
        self.info_link.setAlignment(
            Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        # TODO: Localization
        self.info_link.setText(
            "<html><head/><body><p><a href=\"https://kite.com\">Learn more</span></a></p></body></html>")
        self.info_link.setOpenExternalLinks(True)
        self.layout.addWidget(self.info_link)

    def setup_dismissal_link(self):
        self.dismiss_label = QLabel(self)
        self.dismiss_label.setAlignment(
            Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        # TODO: Localization
        self.dismiss_label.setText(
            "<html><head/><body><p><a href=\"#\"><span style=\" text-decoration: underline;\">Dismiss forever</span></p></body></html>")
        self.dismiss_label.linkActivated.connect(self.on_click)
        self.layout.addWidget(self.dismiss_label)

    @Slot()
    def on_click(self):
        self.hide()
        CONF.set('main', 'show_kite_cta', False)

    # Taken from spyder/plugins/editor/widgets/base.py
    # Places CTA next to cursor
    def orient(self):
        # Retrieve current screen height
        desktop = QApplication.desktop()
        srect = desktop.availableGeometry(desktop.screenNumber(self))
        screen_right = srect.right()
        screen_bottom = srect.bottom()
        point = self.parent_widget.cursorRect().bottomRight()
        point = self.parent_widget.calculate_real_position(point)
        point = self.parent_widget.mapToGlobal(point)
        # Computing completion widget and its parent right positions
        comp_right = point.x() + self.width()
        ancestor = self.parent()
        if ancestor is None:
            anc_right = screen_right
        else:
            anc_right = min([ancestor.x() + ancestor.width(), screen_right])

        # Moving completion widget to the left
        # if there is not enough space to the right
        if comp_right > anc_right:
            point.setX(point.x() - self.width())

        # Computing completion widget and its parent bottom positions
        comp_bottom = point.y() + self.height()
        ancestor = self.parent()
        if ancestor is None:
            anc_bottom = screen_bottom
        else:
            anc_bottom = min([ancestor.y() + ancestor.height(), screen_bottom])

        # Moving completion widget above if there is not enough space below
        x_position = point.x()
        if comp_bottom > anc_bottom:
            point = self.parent_widget.cursorRect().topRight()
            point = self.parent_widget.mapToGlobal(point)
            point.setX(x_position)
            point.setY(point.y() - self.height())

        if ancestor is not None:
            # Useful only if we set parent to 'ancestor' in __init__
            point = ancestor.mapFromGlobal(point)
        self.move(point)
