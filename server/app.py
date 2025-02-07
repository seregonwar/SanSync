import eventlet
eventlet.monkey_patch()

import logging
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Set, Optional
import time
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SanSync')

# Load environment variables
load_dotenv()

# Configure logging level from environment
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logger.setLevel(getattr(logging, log_level))

logger.info("Initializing SanSync server...")
logger.info(f"WebSocket enabled on port {os.getenv('WEBSOCKET_PORT', '5001')}")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gta5-coop-secret!')
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

# Configure Socket.IO with proper CORS and error handling
socketio = SocketIO(
	app,
	cors_allowed_origins="*",
	logger=True,
	engineio_logger=True,
	async_mode='eventlet',
	ping_timeout=int(os.getenv('PING_TIMEOUT', '60')),
	ping_interval=int(os.getenv('PING_INTERVAL', '25')),
	max_http_buffer_size=1e8,
	manage_session=False,
	always_connect=True,
	async_handlers=True,
	message_queue=None,
	path='socket.io'
)

# Configure logging level from environment
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logger.setLevel(getattr(logging, log_level))

logger.info("Initializing SanSync server...")
logger.info(f"Server running on http://{os.getenv('SERVER_HOST', '127.0.0.1')}:{os.getenv('SERVER_PORT', '5000')}")
logger.info("WebSocket transport enabled")




@app.before_request
def before_request():
	"""Log all requests"""
	logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

# Error handling for Socket.IO events
@socketio.on_error()
def error_handler(e):
	logger.error(f"SocketIO error: {e}")
	return {"status": "error", "message": str(e)}

@socketio.on_error_default
def default_error_handler(e):
	logger.error(f"SocketIO default error: {e}")
	return {"status": "error", "message": str(e)}

# Create main namespace
main_namespace = '/'

@dataclass
class Session:
	id: str
	host_id: str
	players: Set[str]
	created_at: float
	game_state: Dict = None

	def to_dict(self):
		return {
			'id': self.id,
			'host_id': self.host_id,
			'player_count': len(self.players),
			'created_at': self.created_at
		}

# Global state
sessions: Dict[str, Session] = {}
player_sessions: Dict[str, str] = {}  # Maps player_id to session_id

@socketio.on('connect')
def handle_connect():
	"""Handle client connection"""
	logger.info(f"Client connected: {request.sid} from {request.remote_addr}")
	# Initialize player state
	if request.sid not in player_sessions:
		player_sessions[request.sid] = None
	return {"status": "connected", "sid": request.sid}

@socketio.on('disconnect')
def handle_disconnect():
	"""Handle client disconnection"""
	logger.info(f"Client disconnected: {request.sid}")
	player_id = request.sid
	if player_id in player_sessions:
		session_id = player_sessions[player_id]
		if session_id:
			handle_leave_session({'session_id': session_id})
		del player_sessions[player_id]

@socketio.on('create_session')
def handle_create_session(data):
	"""Create a new session"""
	try:
		player_id = request.sid
		session = Session(
			id=str(uuid.uuid4()),
			host_id=player_id,
			players={player_id},
			created_at=time.time()
		)
		sessions[session.id] = session
		player_sessions[player_id] = session.id
		join_room(session.id)
		logger.info(f"Created session {session.id} for player {player_id}")
		return {'status': 'created', 'session_id': session.id}
	except Exception as e:
		logger.error(f"Error creating session: {e}")
		return {'status': 'error', 'error': str(e)}

@socketio.on('join_session')
def handle_join_session(data):
	"""Join an existing session"""
	try:
		session_id = data.get('session_id')
		player_id = request.sid
		
		if not session_id:
			logger.warning(f"Join session attempt without session ID from {player_id}")
			return {'status': 'error', 'error': 'Session ID not provided'}
			
		if session_id not in sessions:
			logger.warning(f"Attempt to join non-existent session {session_id} by {player_id}")
			return {'status': 'error', 'error': 'Session not found'}
			
		session = sessions[session_id]
		session.players.add(player_id)
		player_sessions[player_id] = session_id
		join_room(session_id)
		
		# Notify other players
		emit('player_joined', {'player_id': player_id}, room=session_id)
		logger.info(f"Player {player_id} joined session {session_id}")
		return {'status': 'joined'}
	except Exception as e:
		logger.error(f"Error joining session: {e}")
		return {'status': 'error', 'error': str(e)}

@socketio.on('leave_session')
def handle_leave_session(data):
	"""Leave the current session"""
	try:
		session_id = data.get('session_id')
		player_id = request.sid
		
		if not session_id or session_id not in sessions:
			logger.warning(f"Invalid leave session attempt from {player_id} for session {session_id}")
			return {'status': 'error', 'error': 'Invalid session'}
			
		session = sessions[session_id]
		if player_id in session.players:
			session.players.remove(player_id)
			
			# Clean up session if empty
			if len(session.players) == 0:
				logger.info(f"Removing empty session {session_id}")
				del sessions[session_id]
			else:
				# If host left, assign new host
				if player_id == session.host_id:
					new_host = next(iter(session.players))
					session.host_id = new_host
					logger.info(f"New host {new_host} assigned for session {session_id}")
				emit('player_left', {'player_id': player_id}, room=session_id)
				
			leave_room(session_id)
			if player_id in player_sessions:
				del player_sessions[player_id]
			logger.info(f"Player {player_id} left session {session_id}")
			return {'status': 'success'}
	except Exception as e:
		logger.error(f"Error leaving session: {e}")
		return {'status': 'error', 'error': str(e)}

@socketio.on('player_update')
def handle_player_update(data):
	"""Handle player state updates"""
	try:
		player_id = request.sid
		if not player_id:
			logger.error("No player ID found in request")
			return {'status': 'error', 'error': 'No player ID'}
			
		if player_id not in player_sessions:
			logger.warning(f"Player {player_id} not in any session")
			return {'status': 'error', 'error': 'Not in session'}
			
		session_id = player_sessions[player_id]
		if session_id not in sessions:
			logger.error(f"Invalid session {session_id} for player {player_id}")
			return {'status': 'error', 'error': 'Invalid session'}
			
		session = sessions[session_id]
		
		# Update game state
		if not session.game_state:
			session.game_state = {}
		session.game_state[player_id] = data
		
		# Broadcast update to other players in session
		data['player_id'] = player_id
		emit('sync_update', data, room=session_id, include_self=False)
		return {'status': 'success'}
		
	except Exception as e:
		logger.error(f"Error handling player update: {e}")
		return {'status': 'error', 'error': str(e)}

@socketio.on('get_sessions')
def handle_get_sessions():
	"""Get list of available sessions"""
	try:
		active_sessions = [session.to_dict() for session in sessions.values()]
		logger.info(f"Returning {len(active_sessions)} active sessions")
		return active_sessions
	except Exception as e:
		logger.error(f"Error getting sessions: {e}")
		return []

if __name__ == '__main__':
	host = os.getenv('SERVER_HOST', '0.0.0.0')
	port = int(os.getenv('SERVER_PORT', 5000))
	debug = os.getenv('DEBUG', 'False').lower() == 'true'
	
	logger.info(f"Starting server on {host}:{port}")
	logger.info(f"Debug mode: {'enabled' if debug else 'disabled'}")
	socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)