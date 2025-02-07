from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, pyqtSlot
import json
import os
from typing import Dict, Tuple

class MapWidget(QWidget):
	def __init__(self):
		super().__init__()
		self.init_ui()
		self.players = {}
		
	def init_ui(self):
		layout = QVBoxLayout(self)
		
		# Create web view for the map
		self.web_view = QWebEngineView()
		self.web_view.setMinimumHeight(600)
		
		# Load the map HTML file
		map_path = os.path.join(os.path.dirname(__file__), 'resources', 'map.html')
		self.web_view.setUrl(QUrl.fromLocalFile(map_path))
		
		layout.addWidget(self.web_view)
		
	def add_player_marker(self, player_id: str):
		"""Add a new player marker to the map"""
		script = f"""
		addPlayerMarker('{player_id}', 0, 0);
		"""
		self.web_view.page().runJavaScript(script)
		self.players[player_id] = (0, 0)
		
	def remove_player_marker(self, player_id: str):
		"""Remove a player marker from the map"""
		if player_id in self.players:
			script = f"""
			removePlayerMarker('{player_id}');
			"""
			self.web_view.page().runJavaScript(script)
			del self.players[player_id]
			
	def update_player_position(self, player_id: str, position: Dict[str, float]):
		"""Update player marker position on the map"""
		if player_id in self.players:
			# Convert GTA5 coordinates to map coordinates
			x = self._convert_x_coordinate(position['x'])
			y = self._convert_y_coordinate(position['y'])
			
			script = f"""
			updatePlayerPosition('{player_id}', {x}, {y});
			"""
			self.web_view.page().runJavaScript(script)
			self.players[player_id] = (x, y)
			
	def _convert_x_coordinate(self, x: float) -> float:
		"""Convert GTA5 X coordinate to map coordinate"""
		# GTA5 map boundaries (approximate)
		GTA_MIN_X = -4000
		GTA_MAX_X = 4000
		
		# Normalize to 0-1 range
		normalized = (x - GTA_MIN_X) / (GTA_MAX_X - GTA_MIN_X)
		return normalized * 100  # Convert to percentage
		
	def _convert_y_coordinate(self, y: float) -> float:
		"""Convert GTA5 Y coordinate to map coordinate"""
		# GTA5 map boundaries (approximate)
		GTA_MIN_Y = -4000
		GTA_MAX_Y = 4000
		
		# Normalize to 0-1 range and invert (GTA5 Y is inverted)
		normalized = 1 - ((y - GTA_MIN_Y) / (GTA_MAX_Y - GTA_MIN_Y))
		return normalized * 100  # Convert to percentage