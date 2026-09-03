from PyQt6.QtWidgets import QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QFrame,QStackedWidget,QPushButton
from .components import NavButton
from .pages import DashboardPage,ProjectsPage,SettingsPage
from .theme import apply_theme

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__(); self.app=app; self.mode="light"
        self.setWindowTitle("QOZY"); self.resize(1180,760); self.setMinimumSize(920,600)
        root=QWidget(); root.setObjectName("Root")
        main=QHBoxLayout(root); main.setContentsMargins(0,0,0,0); main.setSpacing(0)
        main.addWidget(self.build_sidebar())
        self.pages=QStackedWidget()
        for page in (DashboardPage(),ProjectsPage(),SettingsPage()): self.pages.addWidget(page)
        main.addWidget(self.pages,1); self.setCentralWidget(root); self.select_page(0)

    def build_sidebar(self):
        sidebar=QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(230)
        layout=QVBoxLayout(sidebar); layout.setContentsMargins(16,22,16,16); layout.setSpacing(8)
        brand=QLabel("QOZY"); brand.setObjectName("Brand"); layout.addWidget(brand); layout.addSpacing(20)
        self.buttons=[]
        for i,text in enumerate(["Settings","Counts-Page","Polytope", "Heralded g2-measurement", "State-Tomography"]):
            b=NavButton(text,i); b.clicked.connect(lambda checked=False,idx=i:self.select_page(idx))
            self.buttons.append(b); layout.addWidget(b)
        layout.addStretch()
        theme=QPushButton("Toggle dark mode"); theme.setObjectName("Secondary"); theme.clicked.connect(self.toggle_theme)
        layout.addWidget(theme); return sidebar

    def select_page(self,index):
        self.pages.setCurrentIndex(index)
        for i,b in enumerate(self.buttons): b.set_active(i==index)

    def toggle_theme(self):
        self.mode="dark" if self.mode=="light" else "light"
        apply_theme(self.app,self.mode); self.select_page(self.pages.currentIndex())
