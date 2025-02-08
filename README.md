# SanSync - GTA5 Co-op Mod

A modern, feature-rich cooperative multiplayer mod for GTA5 with real-time player tracking and session management.

## Prerequisites

Before using SanSync, you need to install the following dependencies:

1. ScriptHookV
   - Download from: http://www.dev-c.com/gtav/scripthookv/
   - Extract ScriptHookV.dll to your GTA5 directory

2. ScriptHookVDotNet
   - Download from: https://github.com/crosire/scripthookvdotnet/releases
   - Extract the following files to your GTA5 directory:
     - ScriptHookVDotNet.asi
     - ScriptHookVDotNet2.dll
     - ScriptHookVDotNet3.dll

3. Make sure your GTA5 game is updated to the latest version

## Features

- **Automatic Game Detection**
    - Automatically detects running GTA5 process
    - Real-time player tracking on the map
    - Session management interface
    - Player list with status information

- **Session Management**
    - Host-based architecture (similar to GTA Online)
    - Create and join multiplayer sessions
    - Real-time player synchronization
    - Vehicle synchronization

- **Game Integration**
    - Real-time map with player positions
    - Cooperative missions system
    - Custom event scripting with Lua
    - ScriptHookV integration
    - In-game console (configurable hotkey, default: F12)
        - Teleport commands
        - Vehicle spawning
        - Quick heal and repair
        - Command history support

## Requirements

- GTA5 with ScriptHookV installed
- Python 3.12+ 64bit
- Required Python packages (see requirements.txt)

## Installation

1. Configure your GTA5 path in the .env file:
   - Copy `.env.template` to `.env`
   - Set the correct path to your GTA5 installation
   - Configure console hotkey (default: F12)
   - Configure network settings if needed

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application as administrator:
```bash
python main.py
```

The mod will automatically inject required Lua scripts when launched.

## Usage

1. Using the application:

     - Start GTA5 through Rockstar Games Launcher
     - The mod will automatically detect the running game
     - Create a new session or join existing one
     - Monitor players on the real-time map
     - View player information and status

3. In-Game Console Commands:
     - Press configured hotkey (default: F12) to toggle console
     - Change hotkey in Settings dialog
     - Available commands:
         - `tp [x y z]` - Teleport to coordinates or waypoint
         - `vehicle <model>` or `car <model>` - Spawn vehicle
         - `heal` - Restore health
         - `repair` - Fix current vehicle

## Project Structure

```
SanSync/
├── client/
│   ├── gui/
│   │   ├── resources/
│   │   │   ├── map.html
│   │   │   └── gta5_map.jpg
│   │   ├── main_window.py
│   │   ├── map_widget.py
│   │   ├── player_list_widget.py
│   │   └── session_widget.py
│   ├── game_sync.py
│   └── network_client.py
├── server/
│   └── app.py
├── scripts/
│   ├── game_hooks.lua
│   └── mission_system.lua
├── main.py
└── requirements.txt
```

## Network Protocol

- WebSocket for reliable session management
- UDP for position synchronization
- Host-based networking architecture
- JSON packet format for state updates

## Mission System

- Multi-stage missions
- Player synchronization
- Reward distribution
- Custom mission scripting

## Contributing

Feel free to contribute by submitting pull requests or creating issues for bugs and feature requests.
