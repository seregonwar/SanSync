import ctypes
import win32process
import win32api
import win32con
import os
import time
import sys
from typing import Optional
from ctypes import wintypes, c_void_p, POINTER, c_char_p, c_size_t, byref, sizeof

class DLLInjector:
    def __init__(self):
        # Check admin rights first
        if not self._is_admin():
            self._request_admin()
            sys.exit(0)  # Exit current instance

        # Use the DLL directly from the injector's bin/Release folder
        self.dll_path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'injector', 'bin', 'Release', 'SanSync.dll'
        ))
        print(f"DLL path: {self.dll_path}")
        
        if not os.path.exists(self.dll_path):
            raise RuntimeError(f"DLL not found at: {self.dll_path}")
            
        self.process_handle = None
        self.is_injected = False

        # Define function prototypes
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        self.kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, c_char_p]
        self.kernel32.GetProcAddress.restype = c_void_p
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, c_void_p, c_size_t, wintypes.DWORD, wintypes.DWORD]
        self.kernel32.VirtualAllocEx.restype = c_void_p
        self.kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, c_void_p, c_void_p, c_size_t, POINTER(c_size_t)]
        self.kernel32.WriteProcessMemory.restype = wintypes.BOOL
        self.kernel32.CreateRemoteThread.argtypes = [wintypes.HANDLE, c_void_p, c_size_t, c_void_p, c_void_p, wintypes.DWORD, c_void_p]
        self.kernel32.CreateRemoteThread.restype = wintypes.HANDLE
        self.kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel32.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel32.GetExitCodeThread.argtypes = [wintypes.HANDLE, POINTER(wintypes.DWORD)]
        self.kernel32.GetExitCodeThread.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE, c_void_p, c_size_t, wintypes.DWORD]
        self.kernel32.VirtualFreeEx.restype = wintypes.BOOL

    def inject(self, process_id: int) -> bool:
        """Inject DLL into target process"""
        try:
            print(f"Attempting to inject DLL: {self.dll_path}")
            print(f"DLL exists: {os.path.exists(self.dll_path)}")
            print(f"DLL size: {os.path.getsize(self.dll_path)} bytes")
            
            if not os.path.exists(self.dll_path):
                print(f"DLL not found at path: {self.dll_path}")
                return False

            # Get process handle
            print(f"Opening process with ID: {process_id}")
            self.process_handle = self.kernel32.OpenProcess(
                win32con.PROCESS_ALL_ACCESS,
                False,
                process_id
            )
            
            if not self.process_handle:
                error = ctypes.get_last_error()
                print(f"Failed to open process. Error: {error}")
                return False
                
            print("Process handle obtained successfully")

            # Get LoadLibraryA address
            kernel32_handle = self.kernel32.GetModuleHandleW("kernel32")
            if not kernel32_handle:
                error = ctypes.get_last_error()
                print(f"Failed to get kernel32 handle. Error: {error}")
                return False

            load_library_addr = self.kernel32.GetProcAddress(kernel32_handle, b"LoadLibraryA")
            if not load_library_addr:
                error = ctypes.get_last_error()
                print(f"Failed to get LoadLibraryA address. Error: {error}")
                return False

            print(f"LoadLibraryA address: {hex(load_library_addr)}")

            # Allocate memory for DLL path
            dll_path_bytes = (self.dll_path.replace('\\', '\\\\')).encode('ascii') + b'\0'
            path_size = len(dll_path_bytes)
            print(f"DLL path bytes: {dll_path_bytes}")

            remote_memory = self.kernel32.VirtualAllocEx(
                self.process_handle,
                None,
                path_size,
                win32con.MEM_COMMIT | win32con.MEM_RESERVE,
                win32con.PAGE_READWRITE
            )

            if not remote_memory:
                error = ctypes.get_last_error()
                print(f"Failed to allocate memory in target process. Error: {error}")
                return False

            print(f"Allocated memory at: {hex(remote_memory)}")

            # Write DLL path to process memory
            bytes_written = c_size_t(0)
            success = self.kernel32.WriteProcessMemory(
                self.process_handle,
                remote_memory,
                dll_path_bytes,
                path_size,
                byref(bytes_written)
            )

            if not success:
                error = ctypes.get_last_error()
                print(f"Failed to write to process memory. Error: {error}")
                return False

            print(f"Successfully wrote {bytes_written.value} bytes to process memory")

            # Create remote thread to load DLL
            thread_handle = self.kernel32.CreateRemoteThread(
                self.process_handle,
                None,
                0,
                load_library_addr,
                remote_memory,
                0,
                None
            )

            if not thread_handle:
                error = ctypes.get_last_error()
                print(f"Failed to create remote thread. Error: {error}")
                return False

            print("Created remote thread, waiting for completion...")

            # Wait for thread to complete
            result = self.kernel32.WaitForSingleObject(thread_handle, 10000)  # 10 second timeout
            if result != win32con.WAIT_OBJECT_0:
                print(f"Wait for thread failed with result: {result}")
                return False

            # Get thread exit code
            exit_code = wintypes.DWORD()
            if not self.kernel32.GetExitCodeThread(thread_handle, byref(exit_code)):
                error = ctypes.get_last_error()
                print(f"Failed to get thread exit code. Error: {error}")
                return False

            print(f"LoadLibrary thread exit code: {hex(exit_code.value)}")

            # Cleanup injection resources
            self.kernel32.CloseHandle(thread_handle)
            self.kernel32.VirtualFreeEx(
                self.process_handle,
                remote_memory,
                0,
                win32con.MEM_RELEASE
            )

            if exit_code.value == 0:
                print("DLL injection failed - LoadLibrary returned 0")
                return False

            # Give the DLL time to initialize
            time.sleep(1)

            self.is_injected = True
            print("DLL injected successfully")
            return True

        except Exception as e:
            print(f"Failed to inject DLL: {e}")
            return False

    def cleanup(self):
        """Cleanup resources"""
        if self.process_handle:
            self.kernel32.CloseHandle(self.process_handle)
            self.process_handle = None
        self.is_injected = False

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



