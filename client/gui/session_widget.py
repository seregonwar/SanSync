from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
						   QLabel, QListWidget, QListWidgetItem, QInputDialog,
						   QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Optional

class SessionWidget(QWidget):
	session_changed = pyqtSignal(str)  # Emits session ID when changed

	def __init__(self, network_client):
		super().__init__()
		self.network_client = network_client
		self.current_session = None
		self.is_host = False
		self.init_ui()

	def init_ui(self):
		layout = QVBoxLayout(self)

		# Session info group
		session_group = QGroupBox("Session")
		session_layout = QVBoxLayout(session_group)

		# Current session info
		self.session_info = QLabel("Not in session")
		session_layout.addWidget(self.session_info)

		# Session controls
		controls_layout = QHBoxLayout()

		self.host_button = QPushButton("Host Session")
		self.host_button.clicked.connect(self.host_session)
		controls_layout.addWidget(self.host_button)

		self.join_button = QPushButton("Join Session")
		self.join_button.clicked.connect(self.join_session)
		controls_layout.addWidget(self.join_button)

		self.leave_button = QPushButton("Leave Session")
		self.leave_button.clicked.connect(self.leave_session)
		self.leave_button.setEnabled(False)
		controls_layout.addWidget(self.leave_button)

		session_layout.addLayout(controls_layout)
		layout.addWidget(session_group)

		# Session list
		self.session_list = QListWidget()
		self.session_list.itemDoubleClicked.connect(self.on_session_selected)
		layout.addWidget(self.session_list)

		# Refresh button
		refresh_button = QPushButton("Refresh Sessions")
		refresh_button.clicked.connect(self.refresh_sessions)
		layout.addWidget(refresh_button)

	def host_session(self):
		try:
			# Try to connect first if not already connected
			if not self.network_client.is_connected and not self.network_client.connect():
				QMessageBox.critical(self, "Connection Error", "Failed to connect to server")
				return

			response = self.network_client.create_session()
			if response.get('status') == 'created':
				self.current_session = response['session_id']
				self.is_host = True
				self.update_session_status()
				self.session_changed.emit(self.current_session)
				QMessageBox.information(self, "Success", f"Session created! ID: {self.current_session}")
			else:
				error_msg = response.get('error', 'Failed to create session')
				QMessageBox.warning(self, "Error", error_msg)
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to create session: {str(e)}")

	def join_session(self):
		# Try to connect first if not already connected
		if not self.network_client.is_connected and not self.network_client.connect():
			QMessageBox.critical(self, "Connection Error", "Failed to connect to server")
			return

		session_id, ok = QInputDialog.getText(self, "Join Session", "Enter Session ID:")
		if ok and session_id:
			try:
				response = self.network_client.join_session(session_id)
				if response.get('status') == 'joined':
					self.current_session = session_id
					self.is_host = False
					self.update_session_status()
					self.session_changed.emit(self.current_session)
				else:
					error_msg = response.get('error', 'Failed to join session')
					QMessageBox.warning(self, "Error", error_msg)
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to join session: {str(e)}")

	def leave_session(self):
		"""Leave the current session"""
		if self.current_session:
			try:
				response = self.network_client.disconnect()
				self.current_session = None
				self.is_host = False
				self.update_session_status()
				self.session_changed.emit("")
				
				# Refresh the session list
				self.refresh_sessions()
				return True
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to leave session: {str(e)}")
				return False
		return True  # Already not in a session

	def update_session_status(self):
		if self.current_session:
			status = f"{'Hosting' if self.is_host else 'Connected to'} Session: {self.current_session}"
			self.host_button.setEnabled(False)
			self.join_button.setEnabled(False)
			self.leave_button.setEnabled(True)
		else:
			status = "Not in session"
			self.host_button.setEnabled(True)
			self.join_button.setEnabled(True)
			self.leave_button.setEnabled(False)
		
		self.session_info.setText(status)

	def refresh_sessions(self):
		try:
			# Try to connect first if not already connected
			if not self.network_client.is_connected and not self.network_client.connect():
				QMessageBox.critical(self, "Connection Error", "Failed to connect to server")
				return

			sessions = self.network_client.get_available_sessions()
			self.session_list.clear()
			for session in sessions:
				item = QListWidgetItem(f"Session {session['id']} - Players: {session['player_count']}")
				item.setData(Qt.ItemDataRole.UserRole, session['id'])
				self.session_list.addItem(item)
		except Exception as e:
			QMessageBox.warning(self, "Error", f"Failed to refresh sessions: {str(e)}")

	def on_session_selected(self, item: QListWidgetItem):
		"""Handle session selection from the list"""
		try:
			session_id = item.data(Qt.ItemDataRole.UserRole)
			if not session_id:
				return
				
			if session_id != self.current_session:
				# Ask for confirmation if already in a session
				if self.current_session:
					reply = QMessageBox.question(
						self,
						"Join Session",
						"You are already in a session. Do you want to leave it and join the selected one?",
						QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
					)
					if reply == QMessageBox.StandardButton.No:
						return
						
					# Leave current session first
					self.leave_session()
					
				# Try to join the selected session
				response = self.network_client.join_session(session_id)
				if response.get('status') == 'joined':
					self.current_session = session_id
					self.is_host = False
					self.update_session_status()
					self.session_changed.emit(self.current_session)
				else:
					error_msg = response.get('error', 'Failed to join session')
					QMessageBox.warning(self, "Error", error_msg)
					# Refresh the session list to show current state
					self.refresh_sessions()
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to join session: {str(e)}")
			self.refresh_sessions()