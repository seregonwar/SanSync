from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
						   QPushButton, QLabel, QListWidget, QTabWidget, 
						   QLineEdit, QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
import psutil
import os
import time
from dotenv import load_dotenv
from typing import Dict, List
from ..network_client import GTACoopClient
from ..game_interface import GTAInterface
from .map_widget import MapWidget
from .session_widget import SessionWidget
from .player_list_widget import PlayerListWidget
from .settings_dialog import SettingsDialog
from .game_console import GameConsole

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("SanSync - GTA5 Co-op")
		self.setMinimumSize(1200, 800)
		
		# Load environment variables
		load_dotenv()
		
		# Initialize interfaces
		self.network_client = GTACoopClient()
		self.game_interface = GTAInterface()
		
		# Register network callbacks
		self.network_client.register_callback('player_joined', self.on_player_joined)
		self.network_client.register_callback('player_left', self.on_player_left)
		self.network_client.register_callback('sync_update', self.on_sync_update)
		
		self.init_ui()
		self.init_timers()
		
		# Initialize game console
		self.game_console = GameConsole(self)
		self.game_console.command_executed.connect(self.handle_console_command)
		self.game_console.hide()
		
		# Start status monitoring
		self.check_game_status()

	
	def check_gta_path(self) -> bool:
		gta_path = os.getenv('GTA_LAUNCHER_PATH')
		return gta_path is not None and os.path.exists(gta_path)
		
	def show_settings_dialog(self, first_run=False):
		dialog = SettingsDialog(self)
		if first_run:
			QMessageBox.information(
				self,
				"Welcome to SanSync",
				"Please select your GTAVLauncher.exe location to continue."
			)
		result = dialog.exec()
		if result == QDialog.DialogCode.Accepted:
			# Reload hotkey after settings change
			self.game_console.register_hotkey()
		elif first_run:
			QMessageBox.critical(
				self,
				"Setup Required",
				"GTA Launcher path setup is required for SanSync to function. The application will now close."
			)
			self.close()
		
	def init_ui(self):
		# Create central widget and main layout
		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		main_layout = QHBoxLayout(central_widget)
		
		# Left panel for sessions and players
		left_panel = QWidget()
		left_layout = QVBoxLayout(left_panel)
		
		# Session controls
		self.session_widget = SessionWidget(self.network_client)
		left_layout.addWidget(self.session_widget)
		
		# Player list
		self.player_list = PlayerListWidget()
		left_layout.addWidget(self.player_list)
		
		# Game status
		game_status = QWidget()
		game_layout = QHBoxLayout(game_status)
		self.game_status = QLabel("Game: Not Running")
		game_layout.addWidget(self.game_status)
		left_layout.addWidget(game_status)
		
		# Add game sync status
		self.sync_status = QLabel("Sync Status: Not Connected")
		left_layout.addWidget(self.sync_status)
		
		main_layout.addWidget(left_panel)
		
		# Right panel for map and game info
		right_panel = QWidget()
		right_layout = QVBoxLayout(right_panel)
		
		# Map widget
		self.map_widget = MapWidget()
		right_layout.addWidget(self.map_widget)
		
		main_layout.addWidget(right_panel)
		
		# Set layout ratios
		main_layout.setStretch(0, 1)  # Left panel
		main_layout.setStretch(1, 2)  # Right panel

		
	def init_timers(self):
		# Game status check timer
		self.game_check_timer = QTimer()
		self.game_check_timer.timeout.connect(self.check_game_status)
		self.game_check_timer.start(5000)  # Check every 5 seconds
		
		# Game state sync timer
		self.sync_timer = QTimer()
		self.sync_timer.timeout.connect(self.sync_game_state)
		self.sync_timer.start(100)  # Sync every 100ms
		
	def launch_game(self):
		"""Launch GTA5 through Rockstar Games Launcher"""
		try:
			if not self.is_game_running():
				gta_path = os.getenv('GTA_LAUNCHER_PATH')
				if not gta_path:
					QMessageBox.warning(
						self,
						"Configuration Error",
						"GTA Launcher path not configured. Please check settings."
					)
					self.show_settings_dialog()
					return
				
				if not os.path.exists(gta_path):
					QMessageBox.warning(
						self,
						"Path Error",
						"Configured GTA Launcher path does not exist. Please check settings."
					)
					self.show_settings_dialog()
					return
				
				os.startfile(gta_path)
				QMessageBox.information(self, "Game Launch", "Starting GTA5 through Rockstar Games Launcher...")
				
				# Give the game a moment to start
				QTimer.singleShot(5000, self._initialize_game_interface)
			else:
				# Game is already running, try to initialize interface
				self._initialize_game_interface()
				
		except Exception as e:
			QMessageBox.critical(self, "Launch Error", f"Failed to launch game: {str(e)}")
			
	def _initialize_game_interface(self):
		"""Initialize connection to GTA5 process"""
		try:
			retry_count = 0
			max_retries = 10  # Try for 10 seconds
			
			while retry_count < max_retries:
				if self.game_interface.initialize():
					self.sync_status.setText("Sync Status: Connected")
					QMessageBox.information(self, "Success", "Game interface loaded successfully")
					return True
					
				# Check if initialization failed due to missing ScriptHookV
				if "Missing required file: ScriptHookV.dll" in self.game_interface.last_error:
					QMessageBox.critical(self, "Missing Dependencies",
						"ScriptHookV is not installed. Please check the README.md file for installation instructions.")
					return False
				elif "Missing required file: ScriptHookVDotNet" in self.game_interface.last_error:
					QMessageBox.critical(self, "Missing Dependencies",
						"ScriptHookVDotNet is not installed. Please check the README.md file for installation instructions.")
					return False
					
				retry_count += 1
				time.sleep(1)
			
			self.sync_status.setText("Sync Status: Failed to connect")
			QMessageBox.warning(self, "Connection Error", 
							  "Failed to connect to GTA5 process after multiple attempts.")
			return False
			
		except Exception as e:
			self.sync_status.setText(f"Sync Status: Error - {str(e)}")
			QMessageBox.critical(self, "Error", 
							   f"Failed to initialize game interface: {str(e)}")
			return False
			
	def is_game_running(self) -> bool:
		"""Check if GTA5 is running"""
		try:
			process_name = os.getenv('PROCESS_NAME', 'GTA5.exe')
			for proc in psutil.process_iter(['name', 'status']):
				if proc.info['name'] == process_name and proc.info['status'] == psutil.STATUS_RUNNING:
					return True
			return False
		except Exception as e:
			print(f"Error checking game status: {e}")
			return False

	def check_game_status(self):
		"""Check GTA5 process status and update UI"""
		try:
			is_running = self.is_game_running()
			self.game_status.setText(f"Game: {'Running' if is_running else 'Not Running'}")
			
			# Check if game interface needs cleanup
			if not is_running and self.game_interface.is_initialized:
				print("GTA5 process terminated, cleaning up resources")
				self.game_interface.close()
				self.sync_status.setText("Sync Status: Not Connected")
				QMessageBox.warning(self, "Game Status", "GTA5 process has terminated.")
			elif is_running and not self.game_interface.is_initialized:
				# Auto-initialize when game is detected
				self._initialize_game_interface()
		except Exception as e:
			print(f"Error checking game status: {e}")
			self.sync_status.setText("Sync Status: Error")
			
	def sync_game_state(self):
		"""Synchronize game state with other players"""
		if not self.game_interface.is_initialized:
			return
			
		try:
			# Get local player state through shared memory
			state = self.game_interface.get_player_state()
			if state:
				# Send state update to server
				self.network_client.send_player_update(state)
				
				# Update local UI
				if 'position' in state:
					self.map_widget.update_player_position(
						self.network_client.local_player_id,
						state['position']
					)
		except Exception as e:
			print(f"Failed to sync game state: {e}")
			self.sync_status.setText(f"Sync Status: Error - {str(e)}")

		
	def on_player_joined(self, data: Dict):
		self.player_list.add_player(data['player_id'])
		self.map_widget.add_player_marker(data['player_id'])
		
	def on_player_left(self, data: Dict):
		self.player_list.remove_player(data['player_id'])
		self.map_widget.remove_player_marker(data['player_id'])
		
	def on_sync_update(self, data: Dict):
		"""Handle state updates from other players"""
		if not self.game_interface.is_initialized:
			return
			
		try:
			# Update game state for remote player
			self.game_interface.update_remote_player(
				data['player_id'],
				(data['position']['x'], data['position']['y'], data['position']['z']),
				data['health'],
				data.get('vehicle')
			)
			
			# Update UI
			self.map_widget.update_player_position(data['player_id'], data['position'])
			self.player_list.update_player_info(data['player_id'], data)
			
		except Exception as e:
			print(f"Failed to handle sync update: {e}")
		
	def handle_console_command(self, command: str):
		"""Handle commands from the game console"""
		if self.game_interface.is_initialized:
			result = self.game_interface.execute_console_command(command)
			self.game_console.print_message(result)
		else:
			self.game_console.print_message("Error: Game not running", "red")
			
	def closeEvent(self, event):
		"""Handle application close"""
		try:
			# Clean up game interface
			if self.game_interface.is_initialized:
				print("Cleaning up game interface...")
				self.game_interface.close()
			
			# Clean up network client
			if self.network_client:
				print("Cleaning up network client...")
				self.network_client.disconnect()
			
			# Clean up game console
			if self.game_console:
				print("Cleaning up game console...")
				self.game_console.close()
				
			print("Cleanup completed")
		except Exception as e:
			print(f"Error during cleanup: {e}")
		
		super().closeEvent(event)