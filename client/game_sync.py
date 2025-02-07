from typing import Dict, Any, Tuple
import json
import os
import time


class GameState:
	def __init__(self):
		self.player_states = {}
		self.vehicles = {}
		self.missions = {}
		
	def update_player_state(self, player_id: str, state: Dict[str, Any]):
		self.player_states[player_id] = state
		
	def remove_player(self, player_id: str):
		if player_id in self.player_states:
			del self.player_states[player_id]
			
	def get_player_position(self, player_id: str) -> Tuple[float, float, float]:
		if player_id in self.player_states:
			pos = self.player_states[player_id].get('position', {})
			return (pos.get('x', 0.0), pos.get('y', 0.0), pos.get('z', 0.0))
		return (0.0, 0.0, 0.0)

class GameSyncManager:
	def __init__(self):
		self.game_state = GameState()
		self.local_player_id = None
		self.current_pid = os.getpid()  # Store current process ID
		
	def set_local_player(self, player_id: str):
		self.local_player_id = player_id
		
	def update_local_state(self, position: Tuple[float, float, float], health: int, 
						  vehicle_data: Dict[str, Any] = None) -> Dict[str, Any]:
		state = {
			'pid': self.current_pid,
			'position': {
				'x': position[0],
				'y': position[1],
				'z': position[2]
			},
			'health': health,
			'timestamp': time.time()
		}
		
		if vehicle_data:
			state['vehicle'] = vehicle_data
			
		if self.local_player_id:
			self.game_state.update_player_state(self.local_player_id, state)
			
		return state
		
	def handle_remote_update(self, player_id: str, state_data: Dict[str, Any]):
		if player_id != self.local_player_id and state_data.get('pid') != self.current_pid:
			self.game_state.update_player_state(player_id, state_data)
			# Here we would trigger ScriptHookV to update the remote player's position/state
			
	def handle_player_disconnect(self, player_id: str):
		self.game_state.remove_player(player_id)
		# Here we would trigger ScriptHookV to remove the player model

	def get_nearby_players(self, radius: float = 100.0) -> Dict[str, Dict[str, Any]]:
		if not self.local_player_id:
			return {}
			
		local_pos = self.game_state.get_player_position(self.local_player_id)
		nearby = {}
		
		for pid, state in self.game_state.player_states.items():
			if pid == self.local_player_id:
				continue
				
			pos = self.game_state.get_player_position(pid)
			# Simple distance check (can be improved with actual GTA5 world coordinates)
			dist = ((pos[0] - local_pos[0])**2 + 
				   (pos[1] - local_pos[1])**2 + 
				   (pos[2] - local_pos[2])**2)**0.5
				   
			if dist <= radius:
				nearby[pid] = state
				
		return nearby