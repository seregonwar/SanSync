import time
import json
import ctypes
import sys
import os
from client.game_interface import GTAInterface

def is_admin():
	try:
		return ctypes.windll.shell32.IsUserAnAdmin()
	except:
		return False

def run_as_admin():
	if is_admin():
		return True
		
	# Re-run the program with admin rights
	try:
		script = os.path.abspath(__file__)
		args = ' '.join(sys.argv[1:])
		ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {args}', None, 1)
		if ret > 32:  # Success
			return True
	except Exception as e:
		print(f"Error elevating privileges: {e}")
	return False

def main():
	if not run_as_admin():
		print("Failed to get admin privileges. Please run as administrator.")
		return

	print("Running with admin privileges")
	
	# Create game interface
	game = GTAInterface()
	
	print("Initializing game interface...")
	if not game.initialize():
		print("Failed to initialize game interface")
		return

	
	try:
		# Test sending commands
		print("\nTesting command sending...")
		test_command = {
			'type': 'test',
			'message': 'Hello from Python!',
			'timestamp': time.time()
		}
		game.shared_mem.write_command(test_command)
		print("Test command sent")
		
		# Wait a bit and check for state updates
		print("\nWaiting for state updates...")
		for _ in range(10):
			state = game.get_player_state()
			if state:
				print(f"Received state: {json.dumps(state, indent=2)}")
			time.sleep(1)
			
	except KeyboardInterrupt:
		print("\nTest interrupted by user")
	finally:
		print("\nCleaning up...")
		game.close()
		print("Test completed")

if __name__ == '__main__':
	main()