-- Shared memory interface for GTA5 script
local ffi = require("ffi")
local json = require("json")
local natives = require('natives-1.58')


-- Error handling wrapper
local function try_json_encode(data)
	local success, result = pcall(json.encode, data)
	if not success then
		error("JSON encode error: " .. tostring(result))
	end
	return result
end

local function try_json_decode(str)
	local success, result = pcall(json.decode, str)
	if not success then
		error("JSON decode error: " .. tostring(result))
	end
	return result
end

local SharedMemory = {
	MEMORY_NAME = "GTAVCoopSharedMem",
	MEMORY_SIZE = 1024 * 1024,  -- 1MB
	HEADER_SIZE = 128,  -- Updated to match Python implementation
	COMMAND_BUFFER_SIZE = 4096,
	STATE_BUFFER_SIZE = 8192
}

-- FFI definitions for Windows API
ffi.cdef[[
	void* OpenFileMappingA(uint32_t dwDesiredAccess, int bInheritHandle, const char* lpName);
	void* MapViewOfFile(void* hFileMappingObject, uint32_t dwDesiredAccess, 
					   uint32_t dwFileOffsetHigh, uint32_t dwFileOffsetLow, size_t dwNumberOfBytesToMap);
	int UnmapViewOfFile(void* lpBaseAddress);
	int CloseHandle(void* hObject);
]]

function SharedMemory:new()
	local instance = {}
	setmetatable(instance, self)
	self.__index = self
	
	-- Initialize shared memory
	instance:initialize()
	return instance
end

function SharedMemory:initialize()
	-- Constants for Windows API
	local FILE_MAP_ALL_ACCESS = 0xF001F
	
	-- Open shared memory mapping
	self.mapping = ffi.C.OpenFileMappingA(FILE_MAP_ALL_ACCESS, 0, self.MEMORY_NAME)
	if self.mapping == nil then
		error(string.format("Failed to open shared memory mapping: %s", self.MEMORY_NAME))
	end
	
	-- Map view of shared memory
	self.memory = ffi.C.MapViewOfFile(self.mapping, FILE_MAP_ALL_ACCESS, 0, 0, self.MEMORY_SIZE)
	if self.memory == nil then
		ffi.C.CloseHandle(self.mapping)
		error(string.format("Failed to map view of shared memory: %s", self.MEMORY_NAME))
	end
	
	-- Initialize header
	local header = {
		version = 1,
		command_offset = self.HEADER_SIZE,
		state_offset = self.HEADER_SIZE + self.COMMAND_BUFFER_SIZE,
		initialized = true,
		pid = natives.GetCurrentProcessId()  -- Add PID to header
	}
	
	-- Encode header with error handling
	local success, header_json = pcall(json.encode, header)
	if not success then
		error(string.format("Failed to encode header: %s", header_json))
	end
	
	header_json = header_json .. "|"
	if #header_json > self.HEADER_SIZE then
		error(string.format("Header data too large: %d bytes (max %d)", #header_json, self.HEADER_SIZE))
	end
	
	-- Clear memory and write header
	ffi.fill(self.memory, self.MEMORY_SIZE, 0)
	ffi.copy(self.memory, header_json)
	
	print(string.format("Shared memory initialized with header (%d bytes)", #header_json))
	return true
end

function SharedMemory:verify_header()
	if not self.memory then 
		print("Memory not initialized")
		return false 
	end
	
	local header_data = ffi.string(self.memory, self.HEADER_SIZE)
	if not header_data then
		print("Failed to read header data")
		return false
	end
	
	local terminator_pos = header_data:find("|")
	if not terminator_pos then
		print("No terminator found in header")
		return false
	end
	
	local header_json = header_data:sub(1, terminator_pos - 1)
	if header_json:len() == 0 then
		print("Empty header data")
		return false
	end
	
	local success, header = pcall(json.decode, header_json)
	if not success then
		print(string.format("Failed to decode header: %s", header))
		return false
	end
	
	if not header.initialized then
		print("Header not properly initialized")
		return false
	end
	
	return true
end

function SharedMemory:read_command()
	if not self.memory then
		print("Memory not initialized")
		return nil
	end
	
	local command_ptr = ffi.cast("char*", self.memory) + self.HEADER_SIZE
	local command_data = ffi.string(command_ptr, self.COMMAND_BUFFER_SIZE)
	
	if command_data:len() == 0 then
		return nil
	end
	
	local terminator_pos = command_data:find("|")
	if not terminator_pos then
		return nil
	end
	
	local command_json = command_data:sub(1, terminator_pos - 1)
	if command_json:len() == 0 then
		return nil
	end
	
	-- Clear command buffer after reading
	ffi.fill(command_ptr, self.COMMAND_BUFFER_SIZE, 0)
	
	-- Decode command
	local success, command = pcall(json.decode, command_json)
	if not success then
		print("Failed to decode command: " .. tostring(command))
		return nil
	end
	
	return command
end

function SharedMemory:write_state(state)
	if not self.memory then
		print("Memory not initialized")
		return false
	end
	
	-- Add timestamp if not present
	if not state.timestamp then
		state.timestamp = natives.GetGameTimer()
	end
	
	-- Encode state with error handling
	local success, state_json = pcall(json.encode, state)
	if not success then
		print("Failed to encode state: " .. tostring(state_json))
		return false
	end
	
	state_json = state_json .. "|"
	if #state_json > self.STATE_BUFFER_SIZE then
		print("State data too large: " .. #state_json .. " bytes (max " .. self.STATE_BUFFER_SIZE .. ")")
		return false
	end
	
	local state_ptr = ffi.cast("char*", self.memory) + self.HEADER_SIZE + self.COMMAND_BUFFER_SIZE
	ffi.fill(state_ptr, self.STATE_BUFFER_SIZE, 0)
	ffi.copy(state_ptr, state_json)
	
	return true
end

function SharedMemory:close()
	if self.memory then
		ffi.C.UnmapViewOfFile(self.memory)
		self.memory = nil
	end
	if self.mapping then
		ffi.C.CloseHandle(self.mapping)
		self.mapping = nil
	end
	print("Shared memory closed")
end

return SharedMemory
