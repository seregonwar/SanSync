from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
						   QLabel, QGroupBox)
from PyQt6.QtCore import Qt
from typing import Dict

class PlayerListWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.players = {}
		self.init_ui()

	def init_ui(self):
		layout = QVBoxLayout(self)
		
		# Players group
		players_group = QGroupBox("Players")
		players_layout = QVBoxLayout(players_group)
		
		# Player count
		self.player_count = QLabel("Players: 0")
		players_layout.addWidget(self.player_count)
		
		# Player list
		self.player_list = QListWidget()
		players_layout.addWidget(self.player_list)
		
		layout.addWidget(players_group)

	def add_player(self, player_id: str):
		if player_id not in self.players:
			item = QListWidgetItem(f"Player: {player_id}")
			item.setData(Qt.ItemDataRole.UserRole, player_id)
			self.player_list.addItem(item)
			self.players[player_id] = item
			self._update_player_count()

	def remove_player(self, player_id: str):
		if player_id in self.players:
			self.player_list.takeItem(self.player_list.row(self.players[player_id]))
			del self.players[player_id]
			self._update_player_count()

	def update_player_info(self, player_id: str, data: Dict):
		if player_id in self.players:
			item = self.players[player_id]
			health = data.get('health', 100)
			vehicle = data.get('vehicle', {})
			
			# Update player info display
			info_text = f"Player: {player_id}\n"
			info_text += f"Health: {health}%\n"
			
			if vehicle:
				info_text += f"Vehicle: {vehicle.get('type', 'Unknown')}\n"
				info_text += f"Speed: {vehicle.get('speed', 0):.1f} mph"
			
			item.setText(info_text)

	def _update_player_count(self):
		self.player_count.setText(f"Players: {len(self.players)}")