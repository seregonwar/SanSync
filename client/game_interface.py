import psutil
from typing import Dict, Tuple, Optional
import time
import ctypes
import sys
import os
from .shared_memory import SharedMemoryInterface
from .dll_injector import DLLInjector


class GTAInterface:
	def __init__(self):
		self.dll_injector = DLLInjector()
		self.shared_mem = None
		self.current_pid = None
		self.is_initialized = False
		self.last_error = None

	def initialize(self) -> bool:
		"""Initialize connection to GTA5 process"""
		try:
			# Reset last error
			self.last_error = None
			
			# Check admin rights first
			if not self._is_admin():
				self._request_admin()
				return False
			
			# Find GTA5 process
			pid = self._find_gta_process()
			if not pid:
				self.last_error = "GTA5 process not found"
				print(self.last_error)
				return False

			# Store current PID
			self.current_pid = pid
			print(f"Found GTA5 process with PID: {pid}")

			# Clean up any existing resources
			self.close()

			# Inject DLL
			if not self.dll_injector.inject(pid):
				self.last_error = "Failed to inject DLL"
				print(self.last_error)
				return False

			# Initialize shared memory
			try:
				self.shared_mem = SharedMemoryInterface()
				print("Shared memory interface initialized")
			except Exception as e:
				self.last_error = f"Failed to initialize shared memory: {e}"
				print(self.last_error)
				return False

			# Send initial command
			try:
				success = self.shared_mem.write_command({
					'type': 'initialize',
					'timestamp': time.time(),
					'pid': pid
				})
				if not success:
					print("Warning: Failed to send initial command")
			except Exception as e:
				print(f"Warning: Failed to send initial command: {e}")

			self.is_initialized = True
			print("\n" + "=" * 50)
			print("Game interface successfully initialized!")
			print("=" * 50 + "\n")
			return True

		except Exception as e:
			self.last_error = f"Failed to initialize GTA interface: {e}"
			print(self.last_error)
			self.close()
			return False

	def _find_gta_process(self) -> Optional[int]:
		"""Find GTA5 process ID"""
		try:
			for proc in psutil.process_iter(['pid', 'name', 'status']):
				if proc.info['name'] == 'GTA5.exe' and proc.info['status'] == psutil.STATUS_RUNNING:
					return proc.info['pid']
			return None
		except Exception as e:
			print(f"Error searching for GTA5 process: {e}")
			return None

	def get_player_state(self) -> Dict:
		"""Get player state from shared memory"""
		if not self.is_initialized or not self.shared_mem:
			return {}
		return self.shared_mem.read_game_state() or {}

	def update_remote_player(self, player_id: str, position: Tuple[float, float, float],
						   health: float, vehicle_data: Optional[Dict] = None):
		"""Update remote player state through shared memory"""
		if not self.is_initialized or not self.shared_mem:
			return

		command = {
			'type': 'update_player',
			'player_id': player_id,
			'state': {
				'position': {
					'x': position[0],
					'y': position[1],
					'z': position[2]
				},
				'health': health
			}
		}
		
		if vehicle_data:
			command['state']['vehicle'] = vehicle_data
			
		self.shared_mem.write_command(command)

	def _is_admin(self):
		"""Check if running with admin privileges"""
		try:
			return ctypes.windll.shell32.IsUserAnAdmin()
		except:
			return False

	def _request_admin(self):
		"""Request elevation to admin privileges"""
		script = os.path.abspath(sys.argv[0])
		params = ' '.join(sys.argv[1:])
		ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

	def close(self):
		"""Clean up resources"""
		if self.shared_mem:
			try:
				if self.current_pid:
					self.shared_mem.write_command({
						'type': 'cleanup',
						'timestamp': time.time(),
						'pid': self.current_pid
					})
			except Exception as e:
				print(f"Warning: Failed to send cleanup command: {e}")
			
			try:
				self.shared_mem.close()
			except Exception as e:
				print(f"Warning: Failed to close shared memory: {e}")
			finally:
				self.shared_mem = None

		if self.dll_injector:
			self.dll_injector.cleanup()

		self.current_pid = None
		self.is_initialized = False
		print("Game interface cleanup completed")

