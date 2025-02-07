-- SanSync Script Manifest
name = "SanSync"
author = "SanSync Team"
version = "1.0.0"

dependencies = {
	"ScriptHookV",
	"ScriptHookVDotNet"
}

files = {
	"natives-1.58.lua",
	"json.lua",           -- Add json.lua before scripts that depend on it
	"shared_memory.lua",
	"game_hooks.lua",
	"mission_system.lua"
}

init_script = "game_hooks.lua"