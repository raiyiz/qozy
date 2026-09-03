from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("card", True)


class MetricCard(Card):
    def __init__(self, title, value, hint, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)
        for text, name, role in [
            (title, "", "muted"),
            (value, "MetricValue", ""),
            (hint, "", "muted"),
        ]:
            label = QLabel(text)
            if name:
                label.setObjectName(name)
            if role:
                label.setProperty("role", role)
            layout.addWidget(label)


class NavButton(QPushButton):
    def __init__(self, text, index, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.setObjectName("Nav")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active):
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
