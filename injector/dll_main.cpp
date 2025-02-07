#include "sansync.h"
#include <windows.h>
#include <iostream>
#include <string>
#include <memory>
#include <mutex>
#include <aclapi.h>
#include <sddl.h>

// Global variables
namespace {
	HANDLE g_SharedMemory = NULL;
	void* g_MappedMemory = NULL;
	std::mutex g_Mutex;
	bool g_Initialized = false;
	HANDLE g_CommandThread = NULL;
}

// Implementation of exported functions
extern "C" {
	SANSYNC_API bool Initialize() {
		try {
			std::lock_guard<std::mutex> lock(g_Mutex);
			
			if (g_Initialized) {
				std::cout << "Already initialized" << std::endl;
				return true;
			}

			DWORD error = 0;
			std::cout << "Initializing shared memory..." << std::endl;
			if (!SanSync::CreateSharedMemory()) {
				error = GetLastError();
				std::cout << "Failed to create shared memory. Error: " << error << std::endl;
				return false;
			}

			std::cout << "Starting command thread..." << std::endl;
			g_CommandThread = CreateThread(NULL, 0, 
				(LPTHREAD_START_ROUTINE)SanSync::ProcessCommands, 
				NULL, 0, NULL);

			if (!g_CommandThread) {
				error = GetLastError();
				std::cout << "Failed to create command thread. Error: " << error << std::endl;
				SanSync::CloseSharedMemory();
				return false;
			}

			std::cout << "Injecting hooks..." << std::endl;
			if (!SanSync::InjectHooks()) {
				std::cout << "Failed to inject hooks" << std::endl;
				SanSync::CloseSharedMemory();
				return false;
			}

			g_Initialized = true;
			std::cout << "Initialization completed successfully" << std::endl;
			return true;
		}
		catch (const std::exception& e) {
			std::cout << "Exception during initialization: " << e.what() << std::endl;
			return false;
		}
	}

	SANSYNC_API void Cleanup() {
		std::lock_guard<std::mutex> lock(g_Mutex);
		
		if (!g_Initialized) {
			return;
		}

		SanSync::RemoveHooks();
		
		if (g_CommandThread) {
			TerminateThread(g_CommandThread, 0);
			CloseHandle(g_CommandThread);
			g_CommandThread = NULL;
		}

		SanSync::CloseSharedMemory();
		g_Initialized = false;
	}

	SANSYNC_API bool WriteCommand(const char* command, size_t length) {
		if (!g_Initialized || !g_MappedMemory || !command || length == 0) {
			return false;
		}

		std::lock_guard<std::mutex> lock(g_Mutex);
		
		if (length > SharedMemoryLayout::COMMAND_BUFFER_SIZE) {
			return false;
		}

		char* cmdBuffer = static_cast<char*>(g_MappedMemory) + SharedMemoryLayout::HEADER_SIZE;
		memcpy(cmdBuffer, command, length);
		cmdBuffer[length] = '\0';
		return true;
	}

	SANSYNC_API bool ReadState(char* buffer, size_t bufferSize, size_t* bytesRead) {
		if (!g_Initialized || !g_MappedMemory || !buffer || !bytesRead) {
			return false;
		}

		std::lock_guard<std::mutex> lock(g_Mutex);
		
		char* stateBuffer = static_cast<char*>(g_MappedMemory) + 
			SharedMemoryLayout::HEADER_SIZE + 
			SharedMemoryLayout::COMMAND_BUFFER_SIZE;

		size_t stateLength = strlen(stateBuffer);
		if (stateLength == 0) {
			*bytesRead = 0;
			return true;
		}

		if (bufferSize < stateLength + 1) {
			return false;
		}

		memcpy(buffer, stateBuffer, stateLength);
		buffer[stateLength] = '\0';
		*bytesRead = stateLength;
		return true;
	}
}

// Implementation of internal functions
namespace SanSync {
	bool CreateSharedMemory() {
		// Create security attributes with explicit permissions for all users
		SECURITY_ATTRIBUTES sa;
		SECURITY_DESCRIPTOR sd;
		PSECURITY_DESCRIPTOR pSD = NULL;
		PACL pACL = NULL;
		EXPLICIT_ACCESS ea;
		PSID pEveryoneSID = NULL;
		SID_IDENTIFIER_AUTHORITY SIDAuthWorld = SECURITY_WORLD_SID_AUTHORITY;
		
		// Create a well-known SID for the Everyone group
		if(!AllocateAndInitializeSid(&SIDAuthWorld, 1,
									SECURITY_WORLD_RID,
									0, 0, 0, 0, 0, 0, 0,
									&pEveryoneSID)) {
			return false;
		}
		
		// Initialize an EXPLICIT_ACCESS structure for an ACE
		ZeroMemory(&ea, sizeof(EXPLICIT_ACCESS));
		ea.grfAccessPermissions = GENERIC_ALL;
		ea.grfAccessMode = SET_ACCESS;
		ea.grfInheritance = NO_INHERITANCE;
		ea.Trustee.TrusteeForm = TRUSTEE_IS_SID;
		ea.Trustee.TrusteeType = TRUSTEE_IS_WELL_KNOWN_GROUP;
		ea.Trustee.ptstrName = (LPTSTR)pEveryoneSID;
		
		// Create a new ACL that contains the new ACEs
		DWORD dwRes = SetEntriesInAcl(1, &ea, NULL, &pACL);
		if (ERROR_SUCCESS != dwRes) {
			FreeSid(pEveryoneSID);
			return false;
		}
		
		// Initialize a security descriptor
		pSD = (PSECURITY_DESCRIPTOR)LocalAlloc(LPTR, SECURITY_DESCRIPTOR_MIN_LENGTH);
		if (NULL == pSD) {
			FreeSid(pEveryoneSID);
			LocalFree(pACL);
			return false;
		}
		
		if (!InitializeSecurityDescriptor(pSD, SECURITY_DESCRIPTOR_REVISION)) {
			FreeSid(pEveryoneSID);
			LocalFree(pACL);
			LocalFree(pSD);
			return false;
		}
		
		// Add the ACL to the security descriptor
		if (!SetSecurityDescriptorDacl(pSD, TRUE, pACL, FALSE)) {
			FreeSid(pEveryoneSID);
			LocalFree(pACL);
			LocalFree(pSD);
			return false;
		}
		
		sa.nLength = sizeof(SECURITY_ATTRIBUTES);
		sa.lpSecurityDescriptor = pSD;
		sa.bInheritHandle = FALSE;
		
		// Create the shared memory with the security attributes
		g_SharedMemory = CreateFileMappingA(
			INVALID_HANDLE_VALUE,
			&sa,
			PAGE_READWRITE,
			0,
			SharedMemoryLayout::TOTAL_SIZE,
			"GTAVCoopSharedMem"
		);
		
		// Cleanup security descriptor resources
		FreeSid(pEveryoneSID);
		LocalFree(pACL);
		LocalFree(pSD);
		
		if (!g_SharedMemory) {
			DWORD error = GetLastError();
			std::cout << "Failed to create shared memory mapping. Error: " << error << std::endl;
			return false;
		}
		
		g_MappedMemory = MapViewOfFile(
			g_SharedMemory,
			FILE_MAP_ALL_ACCESS,
			0,
			0,
			SharedMemoryLayout::TOTAL_SIZE
		);
		
		if (!g_MappedMemory) {
			DWORD error = GetLastError();
			std::cout << "Failed to map view of file. Error: " << error << std::endl;
			CloseHandle(g_SharedMemory);
			g_SharedMemory = NULL;
			return false;
		}
		
		// Initialize memory
		memset(g_MappedMemory, 0, SharedMemoryLayout::TOTAL_SIZE);
		return true;
	}

	void CloseSharedMemory() {
		if (g_MappedMemory) {
			UnmapViewOfFile(g_MappedMemory);
			g_MappedMemory = NULL;
		}

		if (g_SharedMemory) {
			CloseHandle(g_SharedMemory);
			g_SharedMemory = NULL;
		}
	}

	void ProcessCommands() {
		while (g_Initialized) {
			Sleep(50);  // Reduce CPU usage
			
			if (!g_MappedMemory) {
				continue;
			}

			std::lock_guard<std::mutex> lock(g_Mutex);
			
			char* cmdBuffer = static_cast<char*>(g_MappedMemory) + SharedMemoryLayout::HEADER_SIZE;
			if (cmdBuffer[0] != '\0') {
				// Process command here
				// For now, just clear the command buffer
				memset(cmdBuffer, 0, SharedMemoryLayout::COMMAND_BUFFER_SIZE);
			}
		}
	}

	bool InjectHooks() {
		// TODO: Implement game-specific hooks
		return true;
	}

	void RemoveHooks() {
		// TODO: Implement hook cleanup
	}
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
	switch (reason) {
		case DLL_PROCESS_ATTACH:
			try {
				AllocConsole();
				FILE* f;
				freopen_s(&f, "CONOUT$", "w", stdout);
				std::cout << "SanSync DLL injected successfully" << std::endl;
				
				// Initialize immediately
				if (!Initialize()) {
					std::cout << "Failed to initialize DLL" << std::endl;
					return FALSE;
				}
				std::cout << "DLL initialized successfully" << std::endl;
			}
			catch (const std::exception& e) {
				if (GetConsoleWindow()) {
					std::cout << "Exception in DLL_PROCESS_ATTACH: " << e.what() << std::endl;
				}
				return FALSE;
			}
			break;
			
		case DLL_PROCESS_DETACH:
			try {
				if (g_Initialized) {
					Cleanup();
				}
			}
			catch (...) {
				// Ignore cleanup errors on detach
			}
			break;
	}
	return TRUE;
}
