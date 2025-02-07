import mmap
import json
from json.decoder import JSONDecodeError
import threading
from typing import Dict, Optional
import time
import os
from dotenv import load_dotenv
import ctypes
from ctypes import wintypes, windll, byref, get_last_error, WinError
from ctypes.wintypes import DWORD, HANDLE, BOOL, LPVOID
import sys

# Add security descriptor structures
class SECURITY_ATTRIBUTES(ctypes.Structure):
	_fields_ = [
		("nLength", DWORD),
		("lpSecurityDescriptor", LPVOID),
		("bInheritHandle", BOOL)
	]

class SharedMemoryInterface:
	def __init__(self):
		load_dotenv()
		self.shared_mem = None
		self.mapping_handle = None
		self.lock = threading.Lock()
		
		# Check admin rights
		if not self._is_admin():
			self._request_admin()
			sys.exit(0)  # Exit current instance
			
		# Load configuration from environment
		self.MEMORY_NAME = os.getenv('SHARED_MEMORY_NAME', 'GTAVCoopSharedMem')
		self.MEMORY_SIZE = int(os.getenv('SHARED_MEMORY_SIZE', 1048576))
		
		self.HEADER_SIZE = 128
		self.COMMAND_BUFFER_SIZE = 4096
		self.STATE_BUFFER_SIZE = 8192
		
		self.kernel32 = windll.kernel32
		
		if not self._initialize():
			raise RuntimeError("Failed to initialize shared memory")
			
	def _is_admin(self):
		"""Check if the current process has admin privileges"""
		try:
			return ctypes.windll.shell32.IsUserAnAdmin()
		except:
			return False
			
	def _request_admin(self):
		"""Request elevation to admin privileges"""
		script = os.path.abspath(sys.argv[0])
		params = ' '.join(sys.argv[1:])
		ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)


		
	def _verify_header(self) -> bool:
		"""Verify header is properly initialized"""
		try:
			self.shared_mem.seek(0)
			header_bytes = self.shared_mem.read(self.HEADER_SIZE)
			if b'|' not in header_bytes:
				print("No terminator found in header")
				return False
			
			header_data = header_bytes.split(b'|')[0].decode('ascii')
			if not header_data:
				print("Empty header data")
				return False
				
			header = json.loads(header_data)
			return header.get('initialized', False)
		except JSONDecodeError as e:
			print(f"Failed to decode header JSON: {e}")
			return False
		except Exception as e:
			print(f"Failed to verify header: {e}")
			return False

	def _initialize(self) -> bool:
		try:
			# Create security attributes
			sa = SECURITY_ATTRIBUTES()
			sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
			sa.bInheritHandle = True
			sa.lpSecurityDescriptor = None  # NULL for default security

			# Create file mapping with explicit security attributes
			PAGE_READWRITE = 0x04
			self.mapping_handle = self.kernel32.CreateFileMappingW(
				HANDLE(-1),  # INVALID_HANDLE_VALUE
				byref(sa),   # Security attributes
				PAGE_READWRITE,
				0,
				self.MEMORY_SIZE,
				self.MEMORY_NAME
			)

			if not self.mapping_handle:
				raise WinError(get_last_error())

			# Map view of file
			FILE_MAP_ALL_ACCESS = 0xF001F
			ptr = self.kernel32.MapViewOfFile(
				self.mapping_handle,
				FILE_MAP_ALL_ACCESS,
				0,
				0,
				self.MEMORY_SIZE
			)

			if not ptr:
				self.kernel32.CloseHandle(self.mapping_handle)
				raise WinError(get_last_error())

			# Create mmap object from handle
			self.shared_mem = mmap.mmap(-1, self.MEMORY_SIZE, tagname=self.MEMORY_NAME)

			# Initialize header
			header = {
				'version': 1,
				'command_offset': self.HEADER_SIZE,
				'state_offset': self.HEADER_SIZE + self.COMMAND_BUFFER_SIZE,
				'initialized': True,
				'pid': os.getpid()
			}
			
			header_json = json.dumps(header, ensure_ascii=True)
			header_bytes = header_json.encode('ascii') + b'|'
			
			if len(header_bytes) > self.HEADER_SIZE:
				raise ValueError(f"Header data too large: {len(header_bytes)} bytes > {self.HEADER_SIZE}")
			
			self.shared_mem.seek(0)
			self.shared_mem.write(header_bytes.ljust(self.HEADER_SIZE, b'\0'))
			
			return True

		except Exception as e:
			print(f"[SharedMem] Critical error during initialization: {str(e)}")
			self.close()
			return False


			
	def _write_header(self, header: Dict):
		"""Write header information to shared memory"""
		if not self.shared_mem:
			raise RuntimeError("Shared memory not initialized")
			
		with self.lock:
			try:
				self.shared_mem.seek(0)
				header_data = json.dumps(header, ensure_ascii=True).encode('ascii') + b'|'
				if len(header_data) > self.HEADER_SIZE:
					raise ValueError(f"Header data too large: {len(header_data)} bytes > {self.HEADER_SIZE}")
				self.shared_mem.write(header_data.ljust(self.HEADER_SIZE, b'\0'))
			except Exception as e:
				raise RuntimeError(f"Failed to write header: {e}") from e




	def write_command(self, command: Dict):
		"""Write command to shared memory for Lua script"""
		if not self.shared_mem:
			print("Error: Shared memory not initialized")
			return False
			
		try:
			# Add timestamp and PID if not present
			if 'timestamp' not in command:
				command['timestamp'] = time.time()
			if 'pid' not in command:
				command['pid'] = os.getpid()
				
			with self.lock:
				command_data = json.dumps(command, ensure_ascii=True).encode('ascii') + b'|'
				if len(command_data) > self.COMMAND_BUFFER_SIZE:
					print(f"Error: Command data too large: {len(command_data)} bytes > {self.COMMAND_BUFFER_SIZE}")
					return False
				self.shared_mem.seek(self.HEADER_SIZE)
				self.shared_mem.write(command_data.ljust(self.COMMAND_BUFFER_SIZE, b'\0'))
				return True
		except Exception as e:
			print(f"Error: Failed to write command: {e}")
			return False


	def read_command(self) -> Optional[Dict]:
		"""Read command from shared memory"""
		if not self.shared_mem:
			print("Error: Shared memory not initialized")
			return None
			
		try:
			with self.lock:
				self.shared_mem.seek(self.HEADER_SIZE)
				command_bytes = self.shared_mem.read(self.COMMAND_BUFFER_SIZE)
				if b'|' not in command_bytes:
					print("No terminator found in command data")
					return None
					
				command_data = command_bytes.split(b'|')[0].decode('ascii')
				if not command_data:
					return None
					
				return json.loads(command_data)
		except json.JSONDecodeError as e:
			print(f"Error: Failed to decode command JSON: {e}")
			return None
		except Exception as e:
			print(f"Error: Failed to read command: {e}")
			return None

	def write_state(self, state: Dict):
		"""Write game state to shared memory"""
		if not self.shared_mem:
			print("Error: Shared memory not initialized")
			return False
			
		try:
			# Add timestamp and PID if not present
			if 'timestamp' not in state:
				state['timestamp'] = time.time()
			if 'pid' not in state:
				state['pid'] = os.getpid()
				
			with self.lock:
				state_data = json.dumps(state, ensure_ascii=True).encode('ascii') + b'|'
				if len(state_data) > self.STATE_BUFFER_SIZE:
					print(f"Error: State data too large: {len(state_data)} bytes > {self.STATE_BUFFER_SIZE}")
					return False
					
				self.shared_mem.seek(self.HEADER_SIZE + self.COMMAND_BUFFER_SIZE)
				self.shared_mem.write(state_data.ljust(self.STATE_BUFFER_SIZE, b'\0'))
				return True
		except Exception as e:
			print(f"Error: Failed to write game state: {e}")
			return False


	def read_game_state(self) -> Optional[Dict]:
		"""Read game state from shared memory"""
		if not self.shared_mem:
			return None
			
		try:
			with self.lock:
				self.shared_mem.seek(self.HEADER_SIZE + self.COMMAND_BUFFER_SIZE)
				state_bytes = self.shared_mem.read(self.STATE_BUFFER_SIZE)
				if b'|' not in state_bytes:
					return None
					
				state_data = state_bytes.split(b'|')[0].decode('ascii')
				if not state_data:
					return None
					
				return json.loads(state_data)
		except Exception:
			return None


		
	def close(self):
		try:
			if self.shared_mem:
				self.shared_mem.close()
				self.shared_mem = None
			
			if self.mapping_handle:
				self.kernel32.CloseHandle(self.mapping_handle)
				self.mapping_handle = None
				
			print("[SharedMem] Cleanup completed")
		except Exception as e:
			print(f"[SharedMem] Error during cleanup: {e}")




