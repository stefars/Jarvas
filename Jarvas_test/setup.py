import os
from dotenv import load_dotenv

load_dotenv()

# Access the variables using os.getenv
API_KEY = os.getenv("API_KEY")
WORKING_DIR = os.getenv("WORKING_DIR")

