from PyQt6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
    QLineEdit,QComboBox,QPushButton,QGridLayout,QFormLayout,QCheckBox
)
from .components import Card, MetricCard

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        root=QVBoxLayout(self); root.setContentsMargins(32,28,32,28); root.setSpacing(22)
        title=QLabel("Dashboard"); title.setObjectName("PageTitle")
        sub=QLabel("A quick overview of your workspace"); sub.setProperty("role","muted")
        root.addWidget(title); root.addWidget(sub)
        grid=QGridLayout(); grid.setSpacing(16)
        for col, data in enumerate([
            ("Revenue","$42,520","+12.5% from last month"),
            ("Projects","24","4 active this week"),
            ("Team members","18","2 new this month")]):
            grid.addWidget(MetricCard(*data),0,col)
        root.addLayout(grid)
        section=QLabel("Recent activity"); section.setObjectName("SectionTitle"); root.addWidget(section)
        table=QTableWidget(5,3); table.setHorizontalHeaderLabels(["Project","Status","Updated"])
        rows=[("Website redesign","Complete","2 minutes ago"),("Mobile application","In progress","1 hour ago"),
              ("Analytics dashboard","Review","3 hours ago"),("Marketing site","Complete","Yesterday"),
              ("API migration","In progress","Yesterday")]
        for r,row in enumerate(rows):
            for c,v in enumerate(row): table.setItem(r,c,QTableWidgetItem(v))
        table.horizontalHeader().setStretchLastSection(True); root.addWidget(table,1)

class ProjectsPage(QWidget):
    def __init__(self):
        super().__init__()
        root=QVBoxLayout(self); root.setContentsMargins(32,28,32,28); root.setSpacing(18)
        top=QHBoxLayout(); title=QLabel("Projects"); title.setObjectName("PageTitle")
        top.addWidget(title); top.addStretch()
        add=QPushButton("New project"); add.setObjectName("Primary"); top.addWidget(add)
        root.addLayout(top)
        search=QLineEdit(); search.setPlaceholderText("Search projects…"); root.addWidget(search)
        table=QTableWidget(7,4); table.setHorizontalHeaderLabels(["Project","Owner","Status","Updated"])
        rows=[("Website redesign","Alex","Complete","Today"),("Mobile application","Sam","In progress","Today"),
              ("Analytics dashboard","Taylor","Review","Yesterday"),("Marketing site","Jordan","Complete","Yesterday"),
              ("API migration","Morgan","In progress","Mon"),("Design system","Alex","Complete","Fri"),
              ("Customer portal","Sam","Planning","Thu")]
        for r,row in enumerate(rows):
            for c,v in enumerate(row): table.setItem(r,c,QTableWidgetItem(v))
        table.horizontalHeader().setStretchLastSection(True); root.addWidget(table,1)

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        root=QVBoxLayout(self); root.setContentsMargins(32,28,32,28); root.setSpacing(18)
        title=QLabel("Settings"); title.setObjectName("PageTitle"); root.addWidget(title)
        card=Card(); form=QFormLayout(card); form.setContentsMargins(20,20,20,20); form.setSpacing(16)
        name=QLineEdit("Alex Morgan"); email=QLineEdit("alex@example.com")
        theme=QComboBox(); theme.addItems(["Light","Dark"])
        notifications=QCheckBox("Enable desktop notifications"); notifications.setChecked(True)
        form.addRow("Name",name); form.addRow("Email",email); form.addRow("Appearance",theme)
        form.addRow("",notifications)
        save=QPushButton("Save changes"); save.setObjectName("Primary"); form.addRow("",save)
        root.addWidget(card); root.addStretch()
