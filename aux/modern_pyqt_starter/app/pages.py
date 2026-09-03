from PyQt6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
    QLineEdit,QComboBox,QPushButton,QGridLayout,QFormLayout,QCheckBox
)
from .components import Card, MetricCard


def build_standard_page_grid(widgets, columns=3, column_weights=None):
    if column_weights is None:
        column_weights = [2, 2, 1]
    if len(column_weights) < columns:
        column_weights = column_weights + [1] * (columns - len(column_weights))

    grid = QGridLayout()
    grid.setSpacing(16)

    for index in range(columns):
        grid.setColumnStretch(index, column_weights[index])

    for index, widget in enumerate(widgets):
        row, col = divmod(index, columns)
        grid.addWidget(widget, row, col)

    return grid


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(22)

        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        sub = QLabel("A quick overview of your workspace")
        sub.setProperty("role", "muted")
        root.addWidget(title)
        root.addWidget(sub)

        metrics = [
            MetricCard("Revenue", "$42,520", "+12.5% from last month"),
            MetricCard("Projects", "24", "4 active this week"),
            MetricCard("Team members", "18", "2 new this month"),
            MetricCard("Invoices", "$8,430", "3 pending this week"),
            MetricCard("Tasks", "126", "32 due today"),
            MetricCard("Satisfaction", "96%", "Up 4.2% QoQ"),
        ]
        root.addLayout(build_standard_page_grid(metrics))

        section = QLabel("Recent activity")
        section.setObjectName("SectionTitle")
        root.addWidget(section)

        table = QTableWidget(5, 3)
        table.setHorizontalHeaderLabels(["Project", "Status", "Updated"])
        rows = [
            ("Website redesign", "Complete", "2 minutes ago"),
            ("Mobile application", "In progress", "1 hour ago"),
            ("Analytics dashboard", "Review", "3 hours ago"),
            ("Marketing site", "Complete", "Yesterday"),
            ("API migration", "In progress", "Yesterday"),
        ]
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(v))
        table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(table, 1)


class ProjectsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        top = QHBoxLayout()
        title = QLabel("Projects")
        title.setObjectName("PageTitle")
        top.addWidget(title)
        top.addStretch()
        add = QPushButton("New project")
        add.setObjectName("Primary")
        top.addWidget(add)
        root.addLayout(top)

        search = QLineEdit()
        search.setPlaceholderText("Search projects…")
        root.addWidget(search)

        cards = [
            MetricCard("Website redesign", "On track", "Alex • 82% complete"),
            MetricCard("Mobile app", "In review", "Sam • 3 blockers"),
            MetricCard("Analytics", "Stable", "Taylor • 94% complete"),
            MetricCard("Design system", "Launching", "Jordan • 2 tasks left"),
            MetricCard("API migration", "Active", "Morgan • 18 endpoints"),
            MetricCard("Customer portal", "Planning", "Lee • 5 ideas queued"),
        ]
        root.addLayout(build_standard_page_grid(cards))

        table = QTableWidget(7, 4)
        table.setHorizontalHeaderLabels(["Project", "Owner", "Status", "Updated"])
        rows = [
            ("Website redesign", "Alex", "Complete", "Today"),
            ("Mobile application", "Sam", "In progress", "Today"),
            ("Analytics dashboard", "Taylor", "Review", "Yesterday"),
            ("Marketing site", "Jordan", "Complete", "Yesterday"),
            ("API migration", "Morgan", "In progress", "Mon"),
            ("Design system", "Alex", "Complete", "Fri"),
            ("Customer portal", "Sam", "Planning", "Thu"),
        ]
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(v))
        table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(table, 1)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        cards = [
            MetricCard("Profile", "Alex Morgan", "Workspace admin"),
            MetricCard("Security", "2FA enabled", "Last login 2h ago"),
            MetricCard("Notifications", "Desktop on", "3 channels active"),
            MetricCard("Appearance", "Dark mode", "Accent: Indigo"),
            MetricCard("Billing", "Team plan", "$29/month"),
            MetricCard("Integrations", "5 connected", "1 pending review"),
        ]
        root.addLayout(build_standard_page_grid(cards))

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(16)

        name = QLineEdit("Alex Morgan")
        email = QLineEdit("alex@example.com")
        theme = QComboBox()
        theme.addItems(["Light", "Dark"])
        notifications = QCheckBox("Enable desktop notifications")
        notifications.setChecked(True)

        form.addRow("Name", name)
        form.addRow("Email", email)
        form.addRow("Appearance", theme)
        form.addRow("", notifications)

        save = QPushButton("Save changes")
        save.setObjectName("Primary")
        form.addRow("", save)
        root.addWidget(card)
        root.addStretch()


class CountsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Counts")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        cards = [
            MetricCard("Total counts", "1.28M", "Last sample: 5.2s"),
            MetricCard("Coincidences", "83,400", "Within 2.0 ns"),
            MetricCard("Stability", "99.2%", "Noise floor stable"),
            MetricCard("Rate", "2.1 kHz", "Average over 1 min"),
            MetricCard("Efficiency", "87.6%", "Detector throughput"),
            MetricCard("Sync", "Nominal", "Clock locked"),
        ]
        root.addLayout(build_standard_page_grid(cards))

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.addRow("Mode", QComboBox())
        form.addRow("Window", QLineEdit("2.0 ns"))
        form.addRow("Threshold", QLineEdit("0.12"))
        form.addRow("", QPushButton("Run scan"))
        root.addWidget(card)


class PolytopePage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Polytope")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        cards = [
            MetricCard("Vertices", "12", "Measured points"),
            MetricCard("Volume", "0.74", "Normalized state volume"),
            MetricCard("Boundary", "Strong", "Stable contour"),
            MetricCard("Fit error", "0.06", "Residual norm"),
            MetricCard("Target", "Bell", "Current model"),
            MetricCard("Quality", "High", "Confidence 92%"),
        ]
        root.addLayout(build_standard_page_grid(cards))

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.addRow("State model", QComboBox())
        form.addRow("Resolution", QLineEdit("0.05"))
        form.addRow("Constraint", QLineEdit("radius = 1.0"))
        form.addRow("", QPushButton("Update polytope"))
        root.addWidget(card)


class HeraldedG2Page(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Heralded g2")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        cards = [
            MetricCard("g2(0)", "0.34", "Sub-Poissonian"),
            MetricCard("Heralding", "92%", "Signal efficiency"),
            MetricCard("Noise", "5.1%", "Background rate"),
            MetricCard("Acquisition", "4.8 s", "Measurement duration"),
            MetricCard("Signal", "9.6 kHz", "Detected heralds"),
            MetricCard("Quality", "Strong", "Bias corrected"),
        ]
        root.addLayout(build_standard_page_grid(cards))

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.addRow("Source", QComboBox())
        form.addRow("Delay", QLineEdit("0.80 ns"))
        form.addRow("Threshold", QLineEdit("0.18"))
        form.addRow("", QPushButton("Measure g2"))
        root.addWidget(card)


class StateTomographyPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("State tomography")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        cards = [
            MetricCard("Purity", "0.91", "Reconstructed state"),
            MetricCard("Fidelity", "97.4%", "Target state"),
            MetricCard("Entropy", "0.28", "Von Neumann"),
            MetricCard("Basis", "16", "Measurement settings"),
            MetricCard("Iterations", "240", "Runs completed"),
            MetricCard("Confidence", "High", "95% interval"),
        ]
        root.addLayout(build_standard_page_grid(cards))

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.addRow("Basis set", QComboBox())
        form.addRow("Samples", QLineEdit("5000"))
        form.addRow("Tolerance", QLineEdit("1e-3"))
        form.addRow("", QPushButton("Reconstruct state"))
        root.addWidget(card)

