# style_settings.py
import json
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QWidget
)
from PySide6.QtCore import Qt, Signal
from touch_keyboard import TouchKeyboard

STYLES_FOLDER = "style_types"
STYLES_FILE = os.path.join(STYLES_FOLDER, "styles.json")

# ============================================================================
# CUSTOM TOUCH INPUT WIDGETS
# ============================================================================

class TouchLineEdit(QWidget):
    """Line edit with touch keyboard button"""
    textChanged = Signal(str)
    
    def __init__(self, keyboard_type="full", placeholder="", parent=None):
        super().__init__(parent)
        self.keyboard_type = keyboard_type
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Text display (read-only)
        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #121A2C;
                color: #E6E9EF;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                min-height: 40px;
            }
        """)
        
        # Touch keyboard button
        self.keyboard_btn = QPushButton("🔤")
        self.keyboard_btn.setFixedSize(60, 50)
        self.keyboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A5A9C;
                color: white;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #4C6FB5;
            }
            QPushButton:pressed {
                background-color: #2E4A80;
            }
        """)
        self.keyboard_btn.clicked.connect(self.show_keyboard)
        
        layout.addWidget(self.line_edit)
        layout.addWidget(self.keyboard_btn)
    
    def show_keyboard(self):
        """Show touch keyboard dialog"""
        keyboard = TouchKeyboard(self, keyboard_type=self.keyboard_type)
        keyboard.set_initial_text(self.line_edit.text())
        
        if keyboard.exec():
            text = keyboard.get_text()
            self.line_edit.setText(text)
            self.textChanged.emit(text)
    
    def text(self):
        return self.line_edit.text()
    
    def setText(self, text):
        self.line_edit.setText(text)


class TouchSpinBox(QWidget):
    """Spin box with touch numeric keyboard"""
    valueChanged = Signal(int)
    
    def __init__(self, minimum=0, maximum=100, parent=None):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.current_value = minimum
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Value display (read-only)
        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setText(str(self.current_value))
        self.line_edit.setAlignment(Qt.AlignRight)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #121A2C;
                color: #E6E9EF;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                min-height: 40px;
            }
        """)
        
        # Touch keyboard button
        self.keyboard_btn = QPushButton("🔢")
        self.keyboard_btn.setFixedSize(60, 50)
        self.keyboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A5A9C;
                color: white;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #4C6FB5;
            }
            QPushButton:pressed {
                background-color: #2E4A80;
            }
        """)
        self.keyboard_btn.clicked.connect(self.show_keyboard)
        
        layout.addWidget(self.line_edit)
        layout.addWidget(self.keyboard_btn)
    
    def show_keyboard(self):
        """Show numeric keyboard"""
        keyboard = TouchKeyboard(self, keyboard_type="numeric")
        keyboard.set_initial_text(str(self.current_value))
        
        if keyboard.exec():
            text = keyboard.get_text()
            if not text:  # Empty input
                return
            try:
                value = int(text)
                if self.minimum <= value <= self.maximum:
                    self.current_value = value
                    self.line_edit.setText(str(value))
                    self.valueChanged.emit(value)
                else:
                    QMessageBox.warning(
                        self, 
                        "Invalid Value", 
                        f"Please enter a value between {self.minimum} and {self.maximum}"
                    )
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid number")
    
    def value(self):
        return self.current_value
    
    def setValue(self, value):
        if self.minimum <= value <= self.maximum:
            self.current_value = value
            self.line_edit.setText(str(value))


class TouchDoubleSpinBox(QWidget):
    """Double spin box with touch decimal keyboard"""
    valueChanged = Signal(float)
    
    def __init__(self, minimum=0.0, maximum=100.0, decimals=1, parent=None):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals
        self.current_value = minimum
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Value display (read-only)
        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setText(f"{self.current_value:.{decimals}f}")
        self.line_edit.setAlignment(Qt.AlignRight)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #121A2C;
                color: #E6E9EF;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                min-height: 40px;
            }
        """)
        
        # Touch keyboard button
        self.keyboard_btn = QPushButton("🔢")
        self.keyboard_btn.setFixedSize(60, 50)
        self.keyboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A5A9C;
                color: white;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #4C6FB5;
            }
            QPushButton:pressed {
                background-color: #2E4A80;
            }
        """)
        self.keyboard_btn.clicked.connect(self.show_keyboard)
        
        layout.addWidget(self.line_edit)
        layout.addWidget(self.keyboard_btn)
    
    def show_keyboard(self):
        """Show decimal keyboard"""
        keyboard = TouchKeyboard(self, keyboard_type="decimal")
        keyboard.set_initial_text(f"{self.current_value:.{self.decimals}f}")
        
        if keyboard.exec():
            text = keyboard.get_text()
            if not text:  # Empty input
                return
            try:
                value = float(text)
                if self.minimum <= value <= self.maximum:
                    self.current_value = value
                    self.line_edit.setText(f"{value:.{self.decimals}f}")
                    self.valueChanged.emit(value)
                else:
                    QMessageBox.warning(
                        self, 
                        "Invalid Value", 
                        f"Please enter a value between {self.minimum} and {self.maximum}"
                    )
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid decimal number")
    
    def value(self):
        return self.current_value
    
    def setValue(self, value):
        if self.minimum <= value <= self.maximum:
            self.current_value = value
            self.line_edit.setText(f"{value:.{self.decimals}f}")


# ============================================================================
# STYLE LIST MANAGER (Main UI when clicking settings icon)
# ============================================================================
class StyleListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Style Management")
        self.setModal(True)
        self.resize(600, 500)
        self._build_ui()
        self.setStyleSheet(self.stylesheet())
        self.load_styles()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Manage Styles")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00BFFF;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Add New button at top
        self.add_new_btn = QPushButton("+ Add New Style")
        self.add_new_btn.clicked.connect(self.add_new_style)
        layout.addWidget(self.add_new_btn)

        # List of styles
        self.style_list = QListWidget()
        self.style_list.setMinimumHeight(250)
        layout.addWidget(self.style_list)

        # Action buttons for selected style
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)
        
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.close_btn = QPushButton("Close")
        
        self.edit_btn.clicked.connect(self.edit_style)
        self.delete_btn.clicked.connect(self.delete_style)
        self.close_btn.clicked.connect(self.close)
        
        action_layout.addWidget(self.edit_btn)
        action_layout.addWidget(self.delete_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.close_btn)
        
        layout.addLayout(action_layout)

    def stylesheet(self):
        return """
            QDialog {
                background-color: #0A0F1F;
                color: #E6E9EF;
            }
            QLabel {
                color: #E6E9EF;
                font-size: 18px;
            }
            QListWidget {
                background-color: #121A2C;
                color: #E6E9EF;
                border: 2px solid #1F2A40;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #1F2A40;
            }
            QListWidget::item:selected {
                background-color: #3A5A9C;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #2A4A7C;
            }
            QPushButton {
                background-color: #3A5A9C;
                color: white;
                border: 2px solid #1F2A40;
                padding: 15px 30px;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                min-height: 50px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #4C6FB5;
            }
            QPushButton:pressed {
                background-color: #2E4A80;
            }
        """

    def load_styles(self):
        """Load and display all styles"""
        self.style_list.clear()
        styles = self.get_all_styles()
        
        if not styles:
            item = QListWidgetItem("No styles available. Click 'Add New Style' to create one.")
            item.setFlags(Qt.NoItemFlags)  # Make it non-selectable
            self.style_list.addItem(item)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
        else:
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            for style_name, style_data in styles.items():
                button_count = style_data.get('button_count', 'N/A')
                button_distance = style_data.get('button_distance', 'N/A')
                item_text = f"{style_name}  |  Buttons: {button_count}  |  Distance: {button_distance}mm"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, style_name)  # Store style name
                self.style_list.addItem(item)

    def add_new_style(self):
        """Open dialog to add new style"""
        dialog = StyleEntryDialog(self)
        if dialog.exec():
            self.load_styles()  # Refresh list
            if self.parent():
                self.parent().load_styles_to_dropdown()  # Update main window dropdown

    def edit_style(self):
        """Edit selected style"""
        current_item = self.style_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a style to edit!")
            return
        
        style_name = current_item.data(Qt.UserRole)
        if not style_name:
            return
            
        style_data = self.get_style_data(style_name)
        if style_data:
            dialog = StyleEntryDialog(self, style_name, style_data)
            if dialog.exec():
                self.load_styles()  # Refresh list
                if self.parent():
                    self.parent().load_styles_to_dropdown()  # Update main window dropdown

    def delete_style(self):
        """Delete selected style"""
        current_item = self.style_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a style to delete!")
            return
        
        style_name = current_item.data(Qt.UserRole)
        if not style_name:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete style '{style_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            styles = self.get_all_styles()
            if style_name in styles:
                del styles[style_name]
                try:
                    os.makedirs(STYLES_FOLDER, exist_ok=True)
                    with open(STYLES_FILE, 'w') as f:
                        json.dump(styles, f, indent=4)
                    
                    QMessageBox.information(self, "Success", f"Style '{style_name}' deleted successfully!")
                    self.load_styles()  # Refresh list
                    if self.parent():
                        self.parent().load_styles_to_dropdown()  # Update main window dropdown
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete style: {str(e)}")

    @staticmethod
    def get_all_styles():
        """Load all styles from file"""
        if os.path.exists(STYLES_FILE):
            try:
                with open(STYLES_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading styles: {e}")
                return {}
        return {}

    @staticmethod
    def get_style_data(style_name):
        """Get data for specific style"""
        styles = StyleListDialog.get_all_styles()
        return styles.get(style_name, None)


# ============================================================================
# STYLE ENTRY DIALOG (Add/Edit UI)
# ============================================================================
class StyleEntryDialog(QDialog):
    def __init__(self, parent=None, style_name=None, style_data=None):
        super().__init__(parent)
        self.original_style_name = style_name
        self.is_edit_mode = style_name is not None
        
        title = "Edit Style" if self.is_edit_mode else "Add New Style"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 400)
        self._build_ui()
        self.setStyleSheet(self.stylesheet())
        
        # Load existing data if editing
        if self.is_edit_mode and style_data:
            self.name_input.setText(style_name)
            self.count_input.setValue(style_data.get('button_count', 3))
            self.distance_input.setValue(style_data.get('button_distance', 20.0))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Style Name - FULL KEYBOARD
        name_layout = QHBoxLayout()
        name_label = QLabel("Style Name:")
        name_label.setMinimumWidth(150)
        self.name_input = TouchLineEdit(
            keyboard_type="full", 
            placeholder="Enter style name (e.g., Style 01)"
        )
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)

        # Button Count - NUMERIC KEYBOARD
        count_layout = QHBoxLayout()
        count_label = QLabel("Button Count:")
        count_label.setMinimumWidth(150)
        self.count_input = TouchSpinBox(minimum=1, maximum=10)
        self.count_input.setValue(3)
        count_layout.addWidget(count_label)
        count_layout.addWidget(self.count_input)

        # Button Distance - DECIMAL KEYBOARD
        distance_layout = QHBoxLayout()
        distance_label = QLabel("Button Distance (mm):")
        distance_label.setMinimumWidth(150)
        self.distance_input = TouchDoubleSpinBox(
            minimum=0.0, 
            maximum=100.0, 
            decimals=1
        )
        self.distance_input.setValue(20.0)
        distance_layout.addWidget(distance_label)
        distance_layout.addWidget(self.distance_input)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.clicked.connect(self.save_style)
        self.cancel_btn.clicked.connect(self.cancel_action)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        # Add all layouts
        layout.addLayout(name_layout)
        layout.addLayout(count_layout)
        layout.addLayout(distance_layout)
        layout.addStretch()
        layout.addLayout(button_layout)

    def stylesheet(self):
        return """
            QDialog {
                background-color: #0A0F1F;
                color: #E6E9EF;
            }
            QLabel {
                color: #E6E9EF;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3A5A9C;
                color: white;
                border: 2px solid #1F2A40;
                padding: 15px 30px;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                min-height: 50px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #4C6FB5;
            }
            QPushButton:pressed {
                background-color: #2E4A80;
            }
        """

    def save_style(self):
        style_name = self.name_input.text().strip()
        
        if not style_name:
            QMessageBox.warning(self, "Warning", "Please enter a style name!")
            return

        button_count = self.count_input.value()
        button_distance = self.distance_input.value()

        # Create folder if it doesn't exist
        os.makedirs(STYLES_FOLDER, exist_ok=True)

        # Load existing styles
        styles = self.load_styles()

        # Check if renaming in edit mode
        if self.is_edit_mode and style_name != self.original_style_name:
            if style_name in styles:
                QMessageBox.warning(self, "Warning", f"Style '{style_name}' already exists!")
                return
            # Remove old name
            if self.original_style_name in styles:
                del styles[self.original_style_name]

        # Add/Update style
        style_data = {
            "button_count": button_count,
            "button_distance": button_distance
        }
        styles[style_name] = style_data

        # Save to file
        try:
            with open(STYLES_FILE, 'w') as f:
                json.dump(styles, f, indent=4)
            
            action = "updated" if self.is_edit_mode else "saved"
            QMessageBox.information(
                self, 
                "Success", 
                f"Style '{style_name}' {action} successfully!\n\n"
                f"Button Count: {button_count}\n"
                f"Button Distance: {button_distance} mm\n\n"
                f"Saved to: {STYLES_FILE}"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save style: {str(e)}")

    def cancel_action(self):
        # Clear all inputs
        self.name_input.setText("")
        self.count_input.setValue(3)
        self.distance_input.setValue(20.0)
        self.reject()

    @staticmethod
    def load_styles():
        if os.path.exists(STYLES_FILE):
            try:
                with open(STYLES_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading styles: {e}")
                return {}
        return {}


# ============================================================================
# BACKWARD COMPATIBILITY (for main.py imports)
# ============================================================================
class StyleSettingsDialog(StyleListDialog):
    """Alias for backward compatibility"""
    pass

    @staticmethod
    def get_style_names():
        styles = StyleListDialog.get_all_styles()
        return list(styles.keys())

    @staticmethod
    def get_style_data(style_name):
        return StyleListDialog.get_style_data(style_name)