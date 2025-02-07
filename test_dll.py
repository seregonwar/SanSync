import ctypes
import os

def test_dll():
	try:
		dll_path = os.path.abspath(os.path.join('injector', 'bin', 'Release', 'SanSync.dll'))
		print(f"Loading DLL from: {dll_path}")
		
		if not os.path.exists(dll_path):
			print("DLL file not found!")
			return False
			
		dll = ctypes.WinDLL(dll_path)
		print("DLL loaded successfully")
		
		# Try to get Initialize function
		initialize_func = getattr(dll, "Initialize", None)
		if initialize_func:
			print("Found Initialize function")
			result = initialize_func()
			print(f"Initialize result: {result}")
		else:
			print("Initialize function not found")
			
		return True
	except Exception as e:
		print(f"Error loading DLL: {e}")
		return False

if __name__ == "__main__":
	test_dll()