from spyderlib.qt.QtCore import QTimer


class Spin:

    def __init__(self, parent_widget, interval=10, step=1):
        self.parent_widget = parent_widget
        self.interval, self.step = interval, step
        self.info = {}

    def _update(self, parent_widget):
        if self.parent_widget in self.info:
            timer, angle, step = self.info[self.parent_widget]

            if angle >= 360:
                angle = 0

            angle += step
            self.info[parent_widget] = timer, angle, step
            parent_widget.update()

    def setup(self, icon_painter, painter, rect):

        if self.parent_widget not in self.info:
            timer = QTimer()
            timer.timeout.connect(lambda: self._update(self.parent_widget))
            self.info[self.parent_widget] = [timer, 0, self.step]
            timer.start(self.interval)
        else:
            timer, angle, self.step = self.info[self.parent_widget]
            x_center = rect.width() * 0.5
            y_center = rect.height() * 0.5
            painter.translate(x_center, y_center)
            painter.rotate(angle)
            painter.translate(-x_center, -y_center)


class Pulse(Spin):

    def __init__(self, parent_widget):
        Spin.__init__(self, parent_widget, interval=300, step=45)
