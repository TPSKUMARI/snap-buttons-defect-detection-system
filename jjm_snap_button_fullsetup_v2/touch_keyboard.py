# touch_keyboard.py
# FIXED - PROPER SIZING WITH MINIMUM SIZE ENFORCEMENT

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QPushButton, 
    QLineEdit, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont


class TouchKeyboard(QDialog):
    text_entered = Signal(str)

    def __init__(self, parent=None, keyboard_type="full"):
        super().__init__(parent)
        self.keyboard_type = keyboard_type.lower()
        self.current_text = ""
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        # Set window sizes - LARGER to prevent compression
        if self.keyboard_type == "full":
            self.setFixedSize(800, 450)
        else:
            self.setFixedSize(380, 520)
        
        self.setStyleSheet("background:#0c1427; border:4px solid #3A5A9C; border-radius:12px;")
        self.setup_ui()

    def setup_ui(self):
        """Setup the main UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Display field
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setMinimumHeight(65)
        self.display.setMaximumHeight(65)
        self.display.setFont(QFont("Arial", 22, QFont.Bold))
        self.display.setStyleSheet("""
            QLineEdit {
                background: #121a2c;
                color: #00ffcc;
                border: 3px solid #3A5A9C;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.display)

        # Keyboard layout
        if self.keyboard_type == "full":
            self.build_full_keyboard(layout)
        elif self.keyboard_type == "numeric":
            self.build_numeric_keyboard(layout)
        else:
            self.build_decimal_keyboard(layout)

    def build_full_keyboard(self, parent_layout):
        """Build full QWERTY keyboard"""
        # Create container widget for the grid
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(5)
        grid.setContentsMargins(0, 0, 0, 0)

        # Define all rows
        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
            ["Z", "X", "C", "V", "B", "N", "M", ",", "."]
        ]

        # Add regular keys (rows 0-3)
        for row_idx, row_keys in enumerate(rows):
            for col_idx, key in enumerate(row_keys):
                btn = self.create_key_button(key, 60, 50)
                grid.addWidget(btn, row_idx, col_idx, 1, 1)

        # Row 3: Add Backspace button (spans 2 columns)
        backspace_btn = self.create_key_button("Bksp", 125, 50, special=True)
        grid.addWidget(backspace_btn, 3, 9, 1, 2)

        # Row 4: CLR, SPACE, OK
        clr_btn = self.create_key_button("CLR", 125, 50, special=True)
        grid.addWidget(clr_btn, 4, 0, 1, 2)

        space_btn = self.create_key_button("SPACE", 265, 50)
        grid.addWidget(space_btn, 4, 2, 1, 4)

        ok_btn = self.create_key_button("OK", 265, 50, special=True)
        grid.addWidget(ok_btn, 4, 6, 1, 4)

        # Set fixed size for container
        container.setFixedSize(740, 290)
        parent_layout.addWidget(container)

    def build_numeric_keyboard(self, parent_layout):
        """Build numeric keypad"""
        # Create container widget
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        # Define numeric layout
        keys = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
            ["CLR", "0", "Bksp"]
        ]

        # Add number keys
        for row_idx, row_keys in enumerate(keys):
            for col_idx, key in enumerate(row_keys):
                is_special = key in ["CLR", "Bksp"]
                btn = self.create_key_button(key, 100, 65, special=is_special)
                grid.addWidget(btn, row_idx, col_idx, 1, 1)

        # OK button spans 3 columns
        ok_btn = self.create_key_button("OK", 316, 65, special=True)
        grid.addWidget(ok_btn, 4, 0, 1, 3)

        # Set fixed size for container
        container.setFixedSize(340, 355)
        parent_layout.addWidget(container)

    def build_decimal_keyboard(self, parent_layout):
        """Build decimal keypad"""
        # Create container widget
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        # Define decimal layout
        keys = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
            ["CLR", "0", "."]
        ]

        # Add number keys
        for row_idx, row_keys in enumerate(keys):
            for col_idx, key in enumerate(row_keys):
                is_special = key == "CLR"
                btn = self.create_key_button(key, 100, 65, special=is_special)
                grid.addWidget(btn, row_idx, col_idx, 1, 1)

        # Bottom row: Backspace and OK
        backspace_btn = self.create_key_button("Bksp", 100, 65, special=True)
        grid.addWidget(backspace_btn, 4, 0, 1, 1)

        ok_btn = self.create_key_button("OK", 208, 65, special=True)
        grid.addWidget(ok_btn, 4, 1, 1, 2)

        # Set fixed size for container
        container.setFixedSize(340, 355)
        parent_layout.addWidget(container)

    def create_key_button(self, text, width, height, special=False):
        """Create a single keyboard button with ENFORCED sizing"""
        btn = QPushButton(text)
        
        # CRITICAL: Set BOTH fixed size AND minimum/maximum size
        btn.setFixedSize(QSize(width, height))
        btn.setMinimumSize(QSize(width, height))
        btn.setMaximumSize(QSize(width, height))
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # Font size based on text length
        if text == "Bksp":
            font_size = 13
        elif text == "SPACE":
            font_size = 14
        elif len(text) > 2:
            font_size = 13
        else:
            font_size = 18
        
        btn.setFont(QFont("Arial", font_size, QFont.Bold))

        # Button colors
        if special:
            bg_color = "#FF6B35"
            hover_color = "#FF8555"
        else:
            bg_color = "#3A5A9C"
            hover_color = "#5A7BC8"

        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg_color};
                color: white;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                font-weight: bold;
                padding: 5px;
            }}
            QPushButton:hover {{
                background: {hover_color};
            }}
            QPushButton:pressed {{
                background: #2E4A80;
            }}
        """)

        # Connect button click - handling Bksp as Backspace
        if text == "Bksp":
            btn.clicked.connect(self.handle_backspace)
        elif text == "CLR":
            btn.clicked.connect(self.handle_clear)
        elif text == "OK":
            btn.clicked.connect(self.handle_ok)
        elif text == "SPACE":
            btn.clicked.connect(self.handle_space)
        else:
            btn.clicked.connect(lambda checked=False, t=text: self.handle_key_press(t))

        return btn

    def handle_key_press(self, char):
        """Handle regular key press"""
        self.current_text += char
        self.display.setText(self.current_text)

    def handle_space(self):
        """Handle space key"""
        self.current_text += " "
        self.display.setText(self.current_text)

    def handle_backspace(self):
        """Handle backspace key"""
        self.current_text = self.current_text[:-1]
        self.display.setText(self.current_text)

    def handle_clear(self):
        """Handle clear key"""
        self.current_text = ""
        self.display.setText("")

    def handle_ok(self):
        """Handle OK key"""
        self.text_entered.emit(self.current_text)
        self.accept()

    def set_initial_text(self, text=""):
        """Set initial text in display"""
        self.current_text = str(text)
        self.display.setText(self.current_text)

    def get_text(self):
        """Get current text"""
        return self.current_text