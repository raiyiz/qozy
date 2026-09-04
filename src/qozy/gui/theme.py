from PyQt6.QtGui import QFont

BASE = {
    "font_family": '"Segoe UI", "Inter", sans-serif',
    "font_size": 10,
    "page_title_size": 28,
    "page_title_weight": 700,
    "section_title_size": 17,
    "section_title_weight": 650,
    "metric_size": 25,
    "metric_weight": 700,
    "brand_size": 18,
    "brand_weight": 700,
    "button_size": 10,
    "button_weight": 600,
    "control_height": 38,
    "nav_height": 42,
    "button_radius": 8,
    "card_radius": 12,
    "control_radius": 8,
    "group_radius": 10,
    "table_radius": 10,
}

CLASSIC_LIGHT = {
    **BASE,
    "bg": "#F6F7F9", "surface": "#FFFFFF", "surface_alt": "#F1F3F5",
    "surface_hover": "#E8EBEF", "input": "#FFFFFF", "border": "#D5DAE2",
    "border_subtle": "#E4E7EC", "text": "#101828", "muted": "#667085",
    "placeholder": "#98A2B3", "primary": "#2563EB", "primary_hover": "#1D4ED8",
    "primary_pressed": "#1B46C0", "selection": "#DCE7FF", "disabled": "#A7AFBC",
}

CLASSIC_DARK = {
    **BASE,
    "bg": "#0B0F14", "surface": "#121820", "surface_alt": "#1A222C",
    "surface_hover": "#212A34", "input": "#121820", "border": "#32404F",
    "border_subtle": "#26323E", "text": "#F2F4F7", "muted": "#98A2B3",
    "placeholder": "#6F7A86", "primary": "#4F8CFF", "primary_hover": "#6A9CFF",
    "primary_pressed": "#3D73D8", "selection": "#263A62", "disabled": "#5E6874",
}

SOFT_DARK = {
    **BASE,
    "bg": "#111518", "surface": "#1A2024", "surface_alt": "#22292E",
    "surface_hover": "#2A3238", "input": "#171D21", "border": "#39434A",
    "border_subtle": "#2C353B", "text": "#E8ECEF", "muted": "#A4ADB5",
    "placeholder": "#77828B", "primary": "#7E9FE9", "primary_hover": "#91AEF2",
    "primary_pressed": "#6787D0", "selection": "#2B3950", "disabled": "#68737C",
    "page_title_size": 27, "section_title_size": 16, "button_weight": 550,
    "control_height": 40, "nav_height": 40, "button_radius": 9, "card_radius": 14,
    "control_radius": 9, "group_radius": 12, "table_radius": 12,
}

SOFT_LIGHT = {
    **BASE,
    "bg": "#FAFAF7", "surface": "#FFFFFF", "surface_alt": "#F3F3EF",
    "surface_hover": "#EAEAE5", "input": "#FEFEFC", "border": "#D6D5CD",
    "border_subtle": "#E8E8E2", "text": "#272A25", "muted": "#747970",
    "placeholder": "#A0A49D", "primary": "#6076B2", "primary_hover": "#7188C5",
    "primary_pressed": "#53669B", "selection": "#E1E7F3", "disabled": "#A2A69E",
    "page_title_size": 27, "section_title_size": 16, "button_weight": 550,
    "control_height": 40, "nav_height": 40, "button_radius": 9, "card_radius": 14,
    "control_radius": 9, "group_radius": 12, "table_radius": 12,
}

THEME_ORDER = ("classic-light", "classic-dark", "soft-dark", "soft-light")
THEMES = {
    "classic-light": ("Classic Light", CLASSIC_LIGHT),
    "classic-dark": ("Classic Dark", CLASSIC_DARK),
    "soft-dark": ("Soft Dark", SOFT_DARK),
    "soft-light": ("Soft Light", SOFT_LIGHT),
}
THEMES["light"] = THEMES["classic-light"]
THEMES["dark"] = THEMES["classic-dark"]


def stylesheet(c):
    return """
    * {{ font-family: {font_family}; font-size: {font_size}pt; outline: none; }}
    QMainWindow, QWidget#Root {{ background: {bg}; color: {text}; }}
    QWidget {{ color: {text}; }}
    QLabel {{ color: {text}; font-weight: 400; }}
    QLabel[role="muted"] {{ color: {muted}; font-weight: 450; }}
    QFrame[card="true"] {{
        background: {surface}; border: 1px solid {border_subtle}; border-radius: {card_radius}px;
    }}
    QFrame#Sidebar {{ background: {surface}; border-right: 1px solid {border_subtle}; }}
    QLabel#Brand {{ font-size: {brand_size}pt; font-weight: {brand_weight}; color: {text}; letter-spacing: 0.7px; }}
    QLabel#PageTitle {{ font-size: {page_title_size}pt; font-weight: {page_title_weight}; color: {text}; }}
    QLabel#SectionTitle {{ font-size: {section_title_size}pt; font-weight: {section_title_weight}; color: {text}; }}
    QLabel#MetricValue {{ font-size: {metric_size}pt; font-weight: {metric_weight}; color: {text}; }}
    QPushButton {{
        min-height: {control_height}px; padding: 0 14px; border-radius: {button_radius}px;
        border: 1px solid transparent; font-size: {button_size}pt; font-weight: {button_weight};
        color: {text}; background: transparent;
    }}
    QPushButton:hover {{ background: {surface_hover}; }}
    QPushButton:pressed {{ background: {surface_alt}; }}
    QPushButton:disabled {{ color: {disabled}; background: {surface_alt}; border-color: {border_subtle}; }}
    QPushButton#Primary {{ background: {primary}; color: white; border: 1px solid {primary}; }}
    QPushButton#Primary:hover {{ background: {primary_hover}; border-color: {primary_hover}; }}
    QPushButton#Primary:pressed {{ background: {primary_pressed}; border-color: {primary_pressed}; }}
    QPushButton#Primary:disabled {{ background: {surface_alt}; color: {disabled}; border-color: {border_subtle}; }}
    QPushButton#Secondary {{ background: {surface}; color: {text}; border-color: {border}; }}
    QPushButton#Secondary:hover {{ background: {surface_alt}; border-color: {border}; }}
    QPushButton#Secondary:pressed {{ background: {surface_hover}; }}
    QPushButton#Nav {{
        text-align: left; padding: 0 12px; background: transparent; color: {muted};
        border: none; min-height: {nav_height}px; font-size: {button_size}pt;
        font-weight: {button_weight}; border-radius: {button_radius}px;
    }}
    QPushButton#Nav:hover {{ background: {surface_alt}; color: {text}; }}
    QPushButton#Nav[active="true"] {{ background: {selection}; color: {primary}; font-weight: 650; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        min-height: {control_height}px; border: 1px solid {border}; border-radius: {control_radius}px;
        padding: 0 10px; background: {input}; color: {text};
        selection-background-color: {selection}; selection-color: {text};
    }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {border}; background: {surface}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {primary}; background: {surface}; }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ color: {disabled}; background: {surface_alt}; }}
    QLineEdit::placeholder {{ color: {placeholder}; }}
    QComboBox::drop-down {{ width: 28px; border: none; }}
    QComboBox QAbstractItemView {{
        background: {surface}; color: {text}; border: 1px solid {border};
        selection-background-color: {selection}; selection-color: {text}; padding: 4px; outline: none;
    }}
    QCheckBox, QRadioButton {{ color: {text}; spacing: 8px; font-weight: 400; }}
    QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
    QGroupBox {{
        color: {text}; border: 1px solid {border_subtle}; border-radius: {group_radius}px;
        margin-top: 12px; padding: 14px; font-weight: 600;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; background: {surface}; }}
    QTableWidget {{
        background: {surface}; alternate-background-color: {input}; border: 1px solid {border_subtle};
        border-radius: {table_radius}px; gridline-color: {border_subtle}; color: {text};
        selection-background-color: {selection}; selection-color: {text};
    }}
    QHeaderView::section {{
        background: {surface_alt}; color: {muted}; padding: 10px; border: none;
        border-bottom: 1px solid {border_subtle}; font-size: {button_size}pt; font-weight: 600;
    }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {border}; min-height: 28px; border-radius: 5px; }}
    QScrollBar::handle:vertical:hover {{ background: {muted}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; border: none; }}
    """.format(**c)


def apply_theme(app, mode):
    _label, colors = THEMES[mode]
    app.setStyleSheet(stylesheet(colors))
    app.setFont(QFont("Segoe UI", 10))
