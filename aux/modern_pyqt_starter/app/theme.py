from PyQt6.QtGui import QFont

LIGHT = {
    "bg": "#F6F7F9",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F3F5",
    "border": "#E4E7EC",
    "text": "#101828",
    "muted": "#667085",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
}
DARK = {
    "bg": "#0B0F14",
    "surface": "#121820",
    "surface_alt": "#1A222C",
    "border": "#283442",
    "text": "#F2F4F7",
    "muted": "#98A2B3",
    "primary": "#4F8CFF",
    "primary_hover": "#3D7AF0",
}


def stylesheet(c):
    return """
    * {{ font-family: "Segoe UI", "Inter", sans-serif; }}
    QMainWindow, QWidget#Root {{ background: {bg}; color: {text}; }}
    QLabel {{ color: {text}; }}
    QLabel[role="muted"] {{ color: {muted}; }}
    QFrame[card="true"] {{
        background: {surface}; border: 1px solid {border}; border-radius: 12px;
    }}
    QFrame#Sidebar {{ background: {surface}; border-right: 1px solid {border}; }}
    QLabel#Brand {{ font-size: 18px; font-weight: 700; }}
    QLabel#PageTitle {{ font-size: 28px; font-weight: 700; }}
    QLabel#SectionTitle {{ font-size: 17px; font-weight: 650; }}
    QLabel#MetricValue {{ font-size: 25px; font-weight: 700; }}
    QPushButton {{
        min-height: 38px; padding: 0 14px; border-radius: 8px;
        border: 1px solid transparent; font-weight: 600;
    }}
    QPushButton#Primary {{ background: {primary}; color: white; }}
    QPushButton#Primary:hover {{ background: {primary_hover}; }}
    QPushButton#Secondary {{
        background: {surface}; color: {text}; border-color: {border};
    }}
    QPushButton#Secondary:hover {{ background: {surface_alt}; }}
    QPushButton#Nav {{
        text-align: left; padding: 0 12px; background: transparent;
        color: {muted}; border: none; min-height: 42px; font-weight: 600;
    }}
    QPushButton#Nav:hover {{ background: {surface_alt}; color: {text}; }}
    QPushButton#Nav[active="true"] {{
        background: {surface_alt}; color: {primary};
    }}
    QLineEdit, QComboBox {{
        min-height: 38px; border: 1px solid {border}; border-radius: 8px;
        padding: 0 10px; background: {surface}; color: {text};
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 2px solid {primary}; }}
    QTableWidget {{
        background: {surface}; border: 1px solid {border}; border-radius: 10px;
        gridline-color: {border}; color: {text};
        selection-background-color: {surface_alt}; selection-color: {text};
    }}
    QHeaderView::section {{
        background: {surface_alt}; color: {muted}; padding: 10px;
        border: none; font-weight: 600;
    }}
    """.format(**c)


def apply_theme(app, mode):
    app.setStyleSheet(stylesheet(DARK if mode == "dark" else LIGHT))
    app.setFont(QFont("Segoe UI", 10))
