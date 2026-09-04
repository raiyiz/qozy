from PyQt6.QtGui import QFont

CLASSIC_LIGHT = {
    "bg": "#F6F7F9",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F3F5",
    "surface_hover": "#EBEEF2",
    "input": "#FFFFFF",
    "border": "#E4E7EC",
    "border_subtle": "#EEF0F3",
    "text": "#101828",
    "muted": "#667085",
    "placeholder": "#98A2B3",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "primary_pressed": "#1B46C0",
    "selection": "#E8EEF9",
    "disabled": "#A7AFBC",
}

CLASSIC_DARK = {
    "bg": "#0B0F14",
    "surface": "#121820",
    "surface_alt": "#1A222C",
    "surface_hover": "#202A34",
    "input": "#121820",
    "border": "#283442",
    "border_subtle": "#202A33",
    "text": "#F2F4F7",
    "muted": "#98A2B3",
    "placeholder": "#6F7A86",
    "primary": "#4F8CFF",
    "primary_hover": "#3D7AF0",
    "primary_pressed": "#3769CF",
    "selection": "#24324F",
    "disabled": "#5E6874",
}

SOFT_DARK = {
    "bg": "#101419",
    "surface": "#171C22",
    "surface_alt": "#1D232B",
    "surface_hover": "#252C35",
    "input": "#14191F",
    "border": "#303943",
    "border_subtle": "#252C34",
    "text": "#E8EBEF",
    "muted": "#9AA3AD",
    "placeholder": "#737D88",
    "primary": "#7699E8",
    "primary_hover": "#86A7F0",
    "primary_pressed": "#6283CF",
    "selection": "#28344A",
    "disabled": "#626C77",
}

SOFT_LIGHT = {
    "bg": "#FAFAF8",
    "surface": "#FFFFFF",
    "surface_alt": "#F4F4F1",
    "surface_hover": "#ECEDE9",
    "input": "#FEFEFD",
    "border": "#DDDCD5",
    "border_subtle": "#ECECE7",
    "text": "#242721",
    "muted": "#74786F",
    "placeholder": "#A2A59E",
    "primary": "#5F78B8",
    "primary_hover": "#526AA7",
    "primary_pressed": "#465B91",
    "selection": "#E8EDF6",
    "disabled": "#A5A9A1",
}

THEME_ORDER = ("classic-light", "classic-dark", "soft-dark", "soft-light")
THEMES = {
    "classic-light": ("Classic Light", CLASSIC_LIGHT),
    "classic-dark": ("Classic Dark", CLASSIC_DARK),
    "soft-dark": ("Soft Dark", SOFT_DARK),
    "soft-light": ("Soft Light", SOFT_LIGHT),
}

# Backward-compatible aliases for startup code and existing callers.
THEMES["light"] = THEMES["classic-light"]
THEMES["dark"] = THEMES["classic-dark"]


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
    _label, colors = THEMES[mode]
    app.setStyleSheet(stylesheet(colors))
    app.setFont(QFont("Segoe UI", 10))
