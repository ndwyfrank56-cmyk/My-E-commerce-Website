import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import app

def handler(event, context):
    """
    Netlify function handler for Flask app
    """
    try:
        # Import the serverless WSGI handler
        from serverless_wsgi import handle_request
        return handle_request(app, event, context)
    except ImportError:
        # Fallback if serverless_wsgi is not available
        return {
            'statusCode': 500,
            'body': 'serverless_wsgi not installed. Please add it to requirements.txt'
        }
