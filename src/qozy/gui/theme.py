from PyQt6.QtGui import QFont

LIGHT = {
    "bg": "#F7F8FA",
    "surface": "#FFFFFF",
    "surface_alt": "#F2F4F7",
    "surface_hover": "#EEF1F4",
    "input": "#FCFCFD",
    "border": "#D9DEE7",
    "border_subtle": "#E8EBF0",
    "text": "#1B2430",
    "muted": "#667085",
    "placeholder": "#98A2B3",
    "primary": "#3B6FF5",
    "primary_hover": "#315ED6",
    "primary_pressed": "#294FB4",
    "selection": "#E4EBFF",
    "disabled": "#A7AFBC",
}

DARK = {
    "bg": "#0E1217",
    "surface": "#141A21",
    "surface_alt": "#1A222B",
    "surface_hover": "#202A34",
    "input": "#11171D",
    "border": "#2A3541",
    "border_subtle": "#202A33",
    "text": "#E7EBF0",
    "muted": "#9AA5B1",
    "placeholder": "#6F7A86",
    "primary": "#6C92F7",
    "primary_hover": "#7BA0FF",
    "primary_pressed": "#587EDC",
    "selection": "#25345A",
    "disabled": "#5E6874",
}


def stylesheet(c):
    return """
    * {{
        font-family: "Segoe UI", "Inter", sans-serif;
        outline: none;
    }}
    QMainWindow, QWidget#Root {{
        background: {bg};
        color: {text};
    }}
    QLabel {{ color: {text}; }}
    QLabel[role="muted"] {{ color: {muted}; }}
    QFrame[card="true"] {{
        background: {surface};
        border: 1px solid {border_subtle};
        border-radius: 12px;
    }}
    QFrame#Sidebar {{
        background: {surface};
        border-right: 1px solid {border_subtle};
    }}
    QLabel#Brand {{
        font-size: 18px;
        font-weight: 700;
        color: {text};
        letter-spacing: 0.5px;
    }}
    QLabel#PageTitle {{
        font-size: 28px;
        font-weight: 700;
        color: {text};
    }}
    QLabel#SectionTitle {{
        font-size: 17px;
        font-weight: 650;
        color: {text};
    }}
    QLabel#MetricValue {{
        font-size: 25px;
        font-weight: 700;
        color: {text};
    }}
    QPushButton {{
        min-height: 38px;
        padding: 0 14px;
        border-radius: 8px;
        border: 1px solid transparent;
        font-weight: 600;
        color: {text};
        background: transparent;
    }}
    QPushButton:hover {{ background: {surface_hover}; }}
    QPushButton:pressed {{ background: {surface_alt}; }}
    QPushButton:disabled {{
        color: {disabled};
        background: {surface_alt};
        border-color: {border_subtle};
    }}
    QPushButton#Primary {{
        background: {primary};
        color: white;
    }}
    QPushButton#Primary:hover {{ background: {primary_hover}; }}
    QPushButton#Primary:pressed {{ background: {primary_pressed}; }}
    QPushButton#Primary:disabled {{
        background: {surface_alt};
        color: {disabled};
        border-color: {border_subtle};
    }}
    QPushButton#Secondary {{
        background: {surface};
        color: {text};
        border-color: {border};
    }}
    QPushButton#Secondary:hover {{
        background: {surface_alt};
        border-color: {border};
    }}
    QPushButton#Secondary:pressed {{ background: {surface_hover}; }}
    QPushButton#Nav {{
        text-align: left;
        padding: 0 12px;
        background: transparent;
        color: {muted};
        border: none;
        min-height: 42px;
        font-weight: 600;
    }}
    QPushButton#Nav:hover {{
        background: {surface_alt};
        color: {text};
    }}
    QPushButton#Nav[active="true"] {{
        background: {selection};
        color: {primary};
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        min-height: 38px;
        border: 1px solid {border};
        border-radius: 8px;
        padding: 0 10px;
        background: {input};
        color: {text};
        selection-background-color: {selection};
        selection-color: {text};
    }}
    QLineEdit::placeholder, QComboBox QAbstractItemView {{ color: {placeholder}; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: {border};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {primary};
        background: {surface};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        color: {disabled};
        background: {surface_alt};
    }}
    QComboBox::drop-down {{
        width: 28px;
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background: {surface};
        color: {text};
        border: 1px solid {border};
        selection-background-color: {selection};
        selection-color: {text};
        padding: 4px;
    }}
    QCheckBox, QRadioButton {{
        color: {text};
        spacing: 8px;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
    }}
    QGroupBox {{
        color: {text};
        border: 1px solid {border_subtle};
        border-radius: 10px;
        margin-top: 10px;
        padding: 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        background: {surface};
    }}
    QTableWidget {{
        background: {surface};
        alternate-background-color: {input};
        border: 1px solid {border_subtle};
        border-radius: 10px;
        gridline-color: {border_subtle};
        color: {text};
        selection-background-color: {selection};
        selection-color: {text};
    }}
    QHeaderView::section {{
        background: {surface_alt};
        color: {muted};
        padding: 10px;
        border: none;
        border-bottom: 1px solid {border_subtle};
        font-weight: 600;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        min-height: 28px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {muted}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
        border: none;
    }}
    """.format(**c)


def apply_theme(app, mode):
    colors = DARK if mode == "dark" else LIGHT
    app.setStyleSheet(stylesheet(colors))
    app.setFont(QFont("Segoe UI", 10))
