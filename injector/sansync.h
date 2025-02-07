#pragma once

#include <windows.h>
#include <cstdint>

// Export macro
#ifdef SANSYNC_EXPORTS
#define SANSYNC_API __declspec(dllexport)
#else
#define SANSYNC_API __declspec(dllimport)
#endif

// Version info
#define SANSYNC_VERSION_MAJOR 1
#define SANSYNC_VERSION_MINOR 0

// Memory layout
struct SharedMemoryLayout {
	static const size_t HEADER_SIZE = 128;
	static const size_t COMMAND_BUFFER_SIZE = 4096;
	static const size_t STATE_BUFFER_SIZE = 8192;
	static const size_t TOTAL_SIZE = HEADER_SIZE + COMMAND_BUFFER_SIZE + STATE_BUFFER_SIZE;
};

// Function declarations
extern "C" {
	SANSYNC_API bool Initialize();
	SANSYNC_API void Cleanup();
	SANSYNC_API bool WriteCommand(const char* command, size_t length);
	SANSYNC_API bool ReadState(char* buffer, size_t bufferSize, size_t* bytesRead);
}

// Internal functions
namespace SanSync {
	bool CreateSharedMemory();
	void CloseSharedMemory();
	void ProcessCommands();
	bool InjectHooks();
	void RemoveHooks();
}