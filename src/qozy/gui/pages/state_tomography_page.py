"""TODO: same as PolytopePage — placeholder until this measurement is
designed and ported. Not in plan.md's Phase 1-6 scope.
"""

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from qozy.gui.components import Card


class StateTomographyPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("State tomography")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        card = Card()
        card_layout = QVBoxLayout(card)
        note = QLabel("Not yet ported — placeholder page.")
        note.setProperty("role", "muted")
        card_layout.addWidget(note)
        root.addWidget(card)
        root.addStretch()
