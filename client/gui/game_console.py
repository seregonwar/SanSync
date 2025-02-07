from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QColor, QPalette
import keyboard
import os
from dotenv import load_dotenv

class GameConsole(QWidget):
	command_executed = pyqtSignal(str)  # Signal emitted when a command is executed

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
		load_dotenv()
		self.setup_ui()
		self.commands = {
			'help': self.cmd_help,
			'clear': self.cmd_clear,
			'exit': self.hide
		}
		self.history = []
		self.history_index = 0
		self.current_hotkey = None
		self.register_hotkey()


	def setup_ui(self):
		self.setStyleSheet("""
			QWidget {
				background-color: rgba(0, 0, 0, 180);
				color: #ffffff;
				border: 1px solid #444444;
			}
			QTextEdit, QLineEdit {
				background-color: transparent;
				border: none;
				font-family: 'Consolas', monospace;
				font-size: 12px;
			}
		""")
		
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 5, 5)
		
		# Output area
		self.output = QTextEdit()
		self.output.setReadOnly(True)
		self.output.setFixedHeight(200)
		layout.addWidget(self.output)
		
		# Input line
		self.input = QLineEdit()
		self.input.returnPressed.connect(self.execute_command)
		layout.addWidget(self.input)
		
		self.print_message("Welcome to SanSync Console. Type 'help' for commands.")

	def register_hotkey(self):
		"""Register or update the console hotkey"""
		try:
			# Remove existing hotkey if any
			if self.current_hotkey:
				try:
					keyboard.remove_hotkey(self.current_hotkey)
				except:
					pass
				self.current_hotkey = None
			
			# Get hotkey from environment or use default
			hotkey = os.getenv('CONSOLE_HOTKEY', 'f12').lower()
			
			# Register the hotkey with error handling
			try:
				keyboard.unhook_all()  # Clear any existing hooks
				self.current_hotkey = keyboard.on_press_key(hotkey, lambda _: self.toggle_console())
				print(f"Console hotkey registered: {hotkey}")
				return True
			except Exception as e:
				print(f"Failed to register primary hotkey: {e}")
				# Try fallback to F12
				try:
					self.current_hotkey = keyboard.on_press_key('f12', lambda _: self.toggle_console())
					print("Using fallback hotkey: F12")
					return True
				except Exception as e:
					print(f"Failed to register fallback hotkey: {e}")
					return False
					
		except Exception as e:
			print(f"Error in hotkey registration: {e}")
			return False


	def closeEvent(self, event):
		"""Clean up keyboard hooks when closing"""
		if self.current_hotkey:
			try:
				keyboard.remove_hotkey(self.current_hotkey)
			except:
				pass
		super().closeEvent(event)



	def toggle_console(self):
		if self.isVisible():
			self.hide()
		else:
			self.show()
			self.input.setFocus()

	def print_message(self, message, color='white'):
		self.output.setTextColor(QColor(color))
		self.output.append(message)

	def execute_command(self):
		command = self.input.text().strip()
		if not command:
			return

		self.history.append(command)
		self.history_index = len(self.history)
		
		self.print_message(f"> {command}", "#aaaaaa")
		
		cmd_parts = command.split()
		cmd_name = cmd_parts[0].lower()
		args = cmd_parts[1:]

		if cmd_name in self.commands:
			try:
				self.commands[cmd_name](*args)
			except Exception as e:
				self.print_message(f"Error: {str(e)}", "red")
		else:
			self.command_executed.emit(command)
			
		self.input.clear()

	def keyPressEvent(self, event: QKeyEvent):
		if event.key() == Qt.Key.Key_Escape:
			self.hide()
		elif event.key() == Qt.Key.Key_Up:
			self.history_up()
		elif event.key() == Qt.Key.Key_Down:
			self.history_down()
		else:
			super().keyPressEvent(event)

	def history_up(self):
		if self.history and self.history_index > 0:
			self.history_index -= 1
			self.input.setText(self.history[self.history_index])

	def history_down(self):
		if self.history_index < len(self.history) - 1:
			self.history_index += 1
			self.input.setText(self.history[self.history_index])
		elif self.history_index == len(self.history) - 1:
			self.history_index = len(self.history)
			self.input.clear()

	def cmd_help(self):
		help_text = """
Available Commands:
------------------
Console Commands:
  help   - Show this help message
  clear  - Clear console output
  exit   - Hide console

Game Commands:
  tp [x y z]      - Teleport to coordinates or waypoint if no coords given
  vehicle <model> - Spawn a vehicle with the given model name
  car <model>     - Alias for vehicle command
  heal            - Restore player health to maximum
  repair          - Fix current vehicle
"""
		self.print_message(help_text)

	def cmd_clear(self):
		self.output.clear()
		self.print_message("Console cleared.")
		
	def close(self):
		"""Clean up resources"""
		try:
			# Remove keyboard hook
			if self.current_hotkey:
				try:
					keyboard.remove_hotkey(self.current_hotkey)
					print("Keyboard hotkey removed")
				except Exception as e:
					print(f"Warning: Failed to remove keyboard hotkey: {e}")
				finally:
					self.current_hotkey = None
			
			# Clear console history
			self.history.clear()
			self.history_index = 0
			
			# Clear console output
			if self.output:
				self.output.clear()
			
			print("Game console cleanup completed")
			
		except Exception as e:
			print(f"Error during game console cleanup: {e}")
		finally:
			# Ensure window is hidden
			self.hide()