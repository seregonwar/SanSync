from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
							QLabel, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt
import os
from dotenv import load_dotenv

class SettingsDialog(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Settings")
		self.setMinimumWidth(500)
		load_dotenv()
		self.init_ui()
		
	def init_ui(self):
		layout = QVBoxLayout(self)
		
		# Console Hotkey Section
		hotkey_layout = QHBoxLayout()
		hotkey_label = QLabel("Console Hotkey:")
		self.hotkey_input = QLineEdit()
		self.hotkey_input.setText(os.getenv('CONSOLE_HOTKEY', 'f12'))
		self.hotkey_input.setPlaceholderText("e.g., f12, f1")
		
		hotkey_layout.addWidget(hotkey_label)
		hotkey_layout.addWidget(self.hotkey_input)
		
		# Buttons
		btn_layout = QHBoxLayout()
		save_btn = QPushButton("Save")
		cancel_btn = QPushButton("Cancel")
		
		save_btn.clicked.connect(self.save_settings)
		cancel_btn.clicked.connect(self.reject)
		
		btn_layout.addWidget(save_btn)
		btn_layout.addWidget(cancel_btn)
		
		layout.addLayout(hotkey_layout)
		layout.addLayout(btn_layout)

	def save_settings(self):
		"""Save settings to .env file"""
		hotkey = self.hotkey_input.text()
		
		try:
			env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
			
			# Create or update .env file
			env_content = {}
			if os.path.exists(env_path):
				with open(env_path, 'r') as f:
					for line in f:
						if '=' in line:
							key, value = line.strip().split('=', 1)
							env_content[key] = value
			
			env_content['CONSOLE_HOTKEY'] = hotkey
			
			with open(env_path, 'w') as f:
				for key, value in env_content.items():
					f.write(f"{key}={value}\n")
			
			os.environ['CONSOLE_HOTKEY'] = hotkey
			self.accept()
			
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
