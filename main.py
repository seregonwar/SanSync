import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from client.gui.main_window import MainWindow
from dotenv import load_dotenv

def is_admin():
	try:
		return ctypes.windll.shell32.IsUserAnAdmin()
	except:
		return False

def setup_environment():
	# Load environment variables
	load_dotenv()
	
	# Create .env file from template if it doesn't exist
	env_path = os.path.join(os.path.dirname(__file__), '.env')
	if not os.path.exists(env_path):
		template_path = os.path.join(os.path.dirname(__file__), '.env.template')
		if os.path.exists(template_path):
			with open(template_path, 'r') as template, open(env_path, 'w') as env:
				env.write(template.read())

def main():
	# Check if running as admin
	if not is_admin():
		# Re-run the program with admin rights
		ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
		return

	# Setup environment
	setup_environment()
	
	# Create Qt application
	app = QApplication(sys.argv)
	app.setStyle('Fusion')  # Modern style
	
	# Create and show main window
	window = MainWindow()
	window.show()
	
	# Start application event loop
	sys.exit(app.exec())

if __name__ == '__main__':
	main()