-- Mission system for cooperative gameplay
if not ScriptHookV then
	error("ScriptHookV not found. Please install ScriptHookV to use SanSync.")
end

-- Load natives using absolute path
local script_dir = GetScriptPath()
local natives_path = script_dir .. "/natives-1.58.lua"
local natives = nil
local function load_natives()
	local f = assert(loadfile(natives_path))
	natives = f()
	if not natives then
		error("Failed to load natives file")
	end
	print("Mission system: Natives loaded successfully")
end

-- Try to load natives
local success, err = pcall(load_natives)
if not success then
	print("Warning: Failed to load natives - " .. tostring(err))
	print("Mission system functionality may be limited")
end

-- Wait for game to be ready
while not IsGameReady() do
	Wait(100)
end

-- Initialize mission system
local function InitializeMissionSystem()
	print("Initializing mission system...")
	-- Initialize state
	local activeMission = nil
	local missionPlayers = {}
	local checkpoints = {}

-- Mission definitions
local missions = {
	heist = {
		name = "Bank Heist",
		minPlayers = 2,
		stages = {
			{
				type = "goto",
				position = {x = -1379.6, y = -499.8, z = 33.1},
				description = "Go to the bank"
			},
			{
				type = "combat",
				enemies = 5,
				description = "Clear security"
			},
			{
				type = "collect",
				amount = 1000000,
				description = "Collect the money"
			},
			{
				type = "escape",
				position = {x = -1155.3, y = -739.4, z = 19.7},
				description = "Escape to safehouse"
			}
		}
	}
}

function StartMission(missionType, players)
	if activeMission then return false end
	
	local mission = missions[missionType]
	if not mission then return false end
	
	if #players < mission.minPlayers then
		return false, "Not enough players"
	end
	
	activeMission = {
		type = missionType,
		stage = 1,
		players = players,
		startTime = GetGameTimer()
	}
	
	SyncMissionState()
	return true
end

function UpdateMissionProgress(stage, data)
	if not activeMission then return end
	
	local mission = missions[activeMission.type]
	local currentStage = mission.stages[stage]
	
	if currentStage.type == "goto" then
		-- Check if players reached destination
		local allPlayersAtLocation = true
		for _, playerId in ipairs(activeMission.players) do
			local playerPos = GetEntityCoords(GetPlayerPed(playerId))
			local targetPos = currentStage.position
			local dist = GetDistanceBetweenCoords(playerPos.x, playerPos.y, playerPos.z,
												targetPos.x, targetPos.y, targetPos.z, true)
			if dist > 5.0 then
				allPlayersAtLocation = false
				break
			end
		end
		
		if allPlayersAtLocation then
			AdvanceMissionStage()
		end
	elseif currentStage.type == "combat" then
		-- Update enemy count and check completion
		if data.enemiesDefeated >= currentStage.enemies then
			AdvanceMissionStage()
		end
	end
end

function AdvanceMissionStage()
	if not activeMission then return end
	
	local mission = missions[activeMission.type]
	activeMission.stage = activeMission.stage + 1
	
	if activeMission.stage > #mission.stages then
		CompleteMission()
	else
		SyncMissionState()
	end
end

function CompleteMission()
	if not activeMission then return end
	
	-- Calculate rewards
	local reward = 100000 -- Base reward
	local timeBonus = math.max(0, 300000 - (GetGameTimer() - activeMission.startTime)) / 1000
	reward = reward + timeBonus
	
	-- Distribute rewards to players
	for _, playerId in ipairs(activeMission.players) do
		TriggerServerEvent('mission_reward', playerId, reward)
	end
	
	activeMission = nil
	TriggerServerEvent('mission_completed')
end

-- Exports for network integration
exports('StartCoopMission', StartMission)
exports('UpdateMissionState', UpdateMissionProgress)
exports('GetActiveMission', function()
	return activeMission
end)