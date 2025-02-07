-- GTA V Natives Implementation
local natives = {}

-- Player functions
function natives.GetPlayerPed()
	return GetPlayerPed(-1)
end

function natives.GetPlayerCoords()
	local ped = natives.GetPlayerPed()
	return GetEntityCoords(ped)
end

function natives.GetCurrentProcessId()
	return GetCurrentProcessId()
end

-- Entity functions
function natives.GetEntityCoords(entity)
	return GetEntityCoords(entity)
end

function natives.GetEntityHealth(entity)
	return GetEntityHealth(entity)
end

-- Vehicle functions
function natives.GetVehicle()
	local ped = natives.GetPlayerPed()
	return GetVehiclePedIsIn(ped, false)
end

function natives.IsInVehicle()
	return natives.GetVehicle() ~= 0
end

function natives.GetVehicleHealth()
	local vehicle = natives.GetVehicle()
	if vehicle ~= 0 then
		return GetVehicleEngineHealth(vehicle)
	end
	return 0
end

function natives.GetEntityModel(entity)
	return GetEntityModel(entity)
end

-- ScriptHookV functions
function natives.CreateThread(callback)
	return CreateThread(callback)
end

function natives.Wait(ms)
	return Wait(ms)
end

function natives.GetGameTimer()
	return GetGameTimer()
end

function natives.IsPlayerPlaying(playerId)
	return IsPlayerPlaying(playerId)
end

function natives.PlayerId()
	return PlayerId()
end

return natives

