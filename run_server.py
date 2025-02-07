import os
import eventlet
eventlet.monkey_patch()

import logging
from server.app import socketio, app
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SanSync')

# Load environment variables
load_dotenv()

if __name__ == '__main__':
	try:
		host = os.getenv('SERVER_HOST', '127.0.0.1')
		port = int(os.getenv('SERVER_PORT', 5000))
		debug = os.getenv('DEBUG', 'False').lower() == 'true'
		
		logger.info(f"Starting server on {host}:{port}")
		logger.info(f"Debug mode: {'enabled' if debug else 'disabled'}")
		
		# Start the server with WebSocket support
		socketio.run(
			app,
			host=host,
			port=port,
			debug=debug,
			use_reloader=False,
			log_output=True,
			allow_unsafe_werkzeug=True
		)
	except Exception as e:
		logger.error(f"Failed to start server: {e}")
		raise
