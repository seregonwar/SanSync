import socketio
import json
import os
from typing import Dict, Any, Callable
from dotenv import load_dotenv

load_dotenv()

class GTACoopClient:
	def __init__(self, server_url: str = None):
		# Get server URL from environment or use default
		if server_url is None:
			host = os.getenv('SERVER_HOST', 'localhost')
			port = os.getenv('SERVER_PORT', '5000')
			server_url = f"http://{host}:{port}"
			
		# Configure Socket.IO client
		self.sio = socketio.Client(
			logger=True,
			engineio_logger=True,
			reconnection=True,
			reconnection_attempts=3,
			reconnection_delay=1,
			reconnection_delay_max=5,
			request_timeout=10
		)
		self.server_url = server_url
		self.session_id = None
		self.player_id = None
		self.callbacks = {}
		self.is_connected = False

		
		# Register socket event handlers
		self.sio.on('connect', self._on_connect)
		self.sio.on('disconnect', self._on_disconnect)
		self.sio.on('connect_error', self._on_connect_error)
		self.sio.on('sync_update', self._on_sync_update)
		self.sio.on('player_joined', self._on_player_joined)
		self.sio.on('player_left', self._on_player_left)

	def connect(self) -> bool:
		"""Connect to the server"""
		if self.is_connected:
			return True
			
		try:
			print(f"Connecting to server at {self.server_url}")
			self.sio.connect(
				self.server_url,
				wait_timeout=10,
				transports=['websocket'],
				namespaces=['/']
			)
			return True
		except Exception as e:
			print(f"Connection failed: {e}")
			self.is_connected = False
			return False

	def _on_connect_error(self, error):
		print(f"Connection error: {error}")
		self.is_connected = False
		if 'connect_error' in self.callbacks:
			self.callbacks['connect_error'](error)

	def _on_connect(self):
		print("Connected to server")
		self.is_connected = True
		if 'connect' in self.callbacks:
			self.callbacks['connect']()

	def _on_disconnect(self):
		print("Disconnected from server")
		self.is_connected = False
		if 'disconnect' in self.callbacks:
			self.callbacks['disconnect']()

	def create_session(self, mode: str = "freeroam") -> Dict[str, Any]:
		"""Create a new session"""
		if not self.is_connected and not self.connect():
			return {'status': 'failed', 'error': 'Not connected to server'}
			
		try:
			response = self.sio.call('create_session', {'mode': mode})
			if response.get('status') == 'created':
				self.session_id = response['session_id']
			return response
		except Exception as e:
			print(f"Failed to create session: {e}")
			return {'status': 'failed', 'error': str(e)}

	def join_session(self, session_id: str) -> Dict[str, Any]:
		"""Join an existing session"""
		if not self.is_connected and not self.connect():
			return {'status': 'failed', 'error': 'Not connected to server'}
			
		try:
			response = self.sio.call('join_session', {'session_id': session_id})
			if response.get('status') == 'joined':
				self.session_id = session_id
			return response
		except Exception as e:
			print(f"Failed to join session: {e}")
			return {'status': 'failed', 'error': str(e)}

	def send_player_update(self, state_data: Dict[str, Any]):
		if self.session_id:
			self.sio.emit('player_update', state_data)

	def register_callback(self, event: str, callback: Callable):
		self.callbacks[event] = callback

	def _on_connect(self):
		print("Connected to server")
		if 'connect' in self.callbacks:
			self.callbacks['connect']()

	def _on_disconnect(self):
		print("Disconnected from server")
		if 'disconnect' in self.callbacks:
			self.callbacks['disconnect']()

	def _on_sync_update(self, data):
		if 'sync_update' in self.callbacks:
			self.callbacks['sync_update'](data)

	def _on_player_joined(self, data):
		print(f"Player joined: {data['player_id']}")
		if 'player_joined' in self.callbacks:
			self.callbacks['player_joined'](data)

	def _on_player_left(self, data):
		print(f"Player left: {data['player_id']}")
		if 'player_left' in self.callbacks:
			self.callbacks['player_left'](data)

	def disconnect(self):
		if self.sio.connected:
			self.sio.disconnect()