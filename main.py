
# Main application entry point
# main.py
import uvicorn
import logging
from api import app
from scheduler import AlertScheduler
from config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("alert_system.log")
    ]
)

if __name__ == "__main__":
    # Start the scheduler
    settings = Settings()
    scheduler = AlertScheduler(settings)
    scheduler.start()
    
    # Start the API server
    uvicorn.run(app, host="0.0.0.0", port=8000)