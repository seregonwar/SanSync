-- ScriptHookV initialization
local SharedMemory = require('shared_memory')
local json = require('json')
local natives = require('natives-1.58')

-- Global variables for state management
local playerStates = {}
local vehicles = {}
local isSessionActive = false
local localPlayerId = nil
local sharedMem = nil
local currentPid = nil

-- Wait for game to be ready before initializing
local function WaitForGame()
	while not natives.IsPlayerPlaying(natives.PlayerId()) do
		natives.Wait(100)
	end
	return true
end

local function HandleCommand(command)
	if not command or not currentPid then
		return
	end

	if command.type == "start_session" then
		isSessionActive = true
		print("Session started for PID: " .. tostring(currentPid))
	elseif command.type == "stop_session" then
		isSessionActive = false
		print("Session stopped for PID: " .. tostring(currentPid))
	elseif command.type == "initialize" then
		if command.pid == currentPid then
			localPlayerId = command.pid
			isSessionActive = true
			print("Initialized with PID: " .. tostring(localPlayerId))
		end
	elseif command.type == "cleanup" then
		if command.pid == currentPid then
			isSessionActive = false
			localPlayerId = nil
			print("Cleanup received for PID: " .. tostring(currentPid))
		end
	elseif command.type == "toggle_console" then
		print("Console toggle requested")
	end
end

local function GetCurrentGameState()
	if not currentPid then
		return nil
	end

	local ped = natives.GetPlayerPed(-1)
	local pos = natives.GetEntityCoords(ped)
	local health = natives.GetEntityHealth(ped)
	
	local state = {
		pid = currentPid,
		position = {x = pos.x, y = pos.y, z = pos.z},
		health = health,
		timestamp = natives.GetGameTimer()
	}
	
	local vehicle = natives.GetVehiclePedIsIn(ped, false)
	if vehicle ~= 0 then
		state.vehicle = {
			health = natives.GetVehicleEngineHealth(vehicle),
			type = natives.GetDisplayNameFromVehicleModel(natives.GetEntityModel(vehicle))
		}
	end
	
	return state
end

local function Initialize()
	print("Initializing SanSync...")
	
	-- Wait for game to be ready
	if not WaitForGame() then
		print("Failed to initialize: Game not ready")
		return
	end
	
	-- Get current process ID
	currentPid = natives.GetCurrentProcessId()
	if not currentPid then
		print("Failed to get process ID")
		return
	end
	print("Current process ID: " .. tostring(currentPid))
	
	-- Initialize shared memory
	local success, result = pcall(function()
		sharedMem = SharedMemory:new()
		if not sharedMem then
			error("Failed to create shared memory interface")
		end
		print("Shared memory interface created successfully")
		
		-- Send initial state
		local initialState = {
			pid = currentPid,
			initialized = true,
			timestamp = natives.GetGameTimer()
		}
		if not sharedMem:write_state(initialState) then
			error("Failed to write initial state")
		end
	end)

	if not success then
		print("Error initializing shared memory: " .. tostring(result))
		return
	end
	
	-- Start command handling loop
	natives.CreateThread(function()
		while true do
			if sharedMem then
				local success, command = pcall(sharedMem.read_command, sharedMem)
				if success and command then
					pcall(HandleCommand, command)
				end
			end
			natives.Wait(50)  -- Check commands every 50ms
		end
	end)
	
	-- Start state update loop
	natives.CreateThread(function()
		while true do
			if sharedMem and isSessionActive then
				local state = GetCurrentGameState()
				if state then
					pcall(sharedMem.write_state, sharedMem, state)
				end
			end
			natives.Wait(100)  -- Update every 100ms
		end
	end)
	
	print("SanSync initialized successfully")
end

-- Register script with ScriptHookV
return {
	name = "SanSync",
	init = Initialize,
	run = function() end,  -- Empty run function since we use threads
	unload = function()
		if sharedMem then
			sharedMem:close()
		end
	end
}
