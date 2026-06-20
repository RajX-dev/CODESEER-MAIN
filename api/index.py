import sys
import os

# Ensure the n3mo module is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from n3mo.api_server import app

# Vercel requires the FastAPI app to be exposed in the entry point
# We just need to import it here.
