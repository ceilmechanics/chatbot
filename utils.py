# util.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import Optional
import requests

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection string from environment variables
MONGO_URI = os.environ.get("MONGO_URI")

def get_mongodb_connection() -> Optional[MongoClient]:
    """
    Create and return a MongoDB client connection.
    
    Returns:
        MongoClient or None: MongoDB client if connection successful, None otherwise
    """
    try:
        # Create a MongoDB client
        client = MongoClient(MONGO_URI)
        
        # Ping the server to check if connection is successful
        client.admin.command('ping')
        print("Connected successfully to MongoDB")
        return client
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None

def get_collection(database_name: str, collection_name: str):
    """
    Get a specific collection from MongoDB.
    
    Args:
        database_name (str): Name of the database
        collection_name (str): Name of the collection
        
    Returns:
        Collection or None: MongoDB collection if connection successful, None otherwise
    """
    client = get_mongodb_connection()
    if client:
        return client[database_name][collection_name]
    return None

# Example of a function to close the connection
def close_mongodb_connection(client: MongoClient):
    """
    Close the MongoDB client connection.
    
    Args:
        client (MongoClient): MongoDB client to close
    """
    if client:
        client.close()
        print("MongoDB connection closed")


# def forward_human_response(rc_payload, user_profile):
#     url = "https://chat.genaiconnect.net/api/v1/chat.postMessage" #URL of RocketChat server, keep the same

#     # Headers with authentication tokens
#     headers = {
#         "Content-Type": "application/json",
#         "X-Auth-Token": os.environ.get("RC_token"), #Replace with your bot token for local testing or keep it and store secrets in Koyeb
#         "X-User-Id": os.environ.get("RC_userId")#Replace with your bot user id for local testing or keep it and store secrets in Koyeb
#     }

#     # Sending the POST request
#     rc_payload["text"] = (
#         "🚨 Escalation Alert 🚨\n"
#         f"User {user_profile.user_name} needs assistance!\n\n"
#         f"**Message:** {rc_payload["text"]}"
#     )
    
#     response = requests.post(url, json=rc_payload, headers=headers)
#     return response

#     # processing the response with LLM and send back to client

# def extract_user_id(message):
#     """
#     Extract user ID from a human response message.
#     """
#     # Look for ID pattern in escalation message
#     id_match = re.search(r"User .+ \(ID: ([^\)]+)\)", message)
#     if id_match:
#         return id_match.group(1)
    
#     # Look for "Responding to" pattern
#     resp_match = re.search(r"Responding to ([\w\.\-]+):", message)
#     if resp_match:
#         return resp_match.group(1)
        
#     return None

# def send_human_response(user_id, message):
#     """
#     Sends a human advisor's response back to the original user.
#     """
#     url = "https://chat.genaiconnect.net/api/v1/chat.postMessage"
    
#     headers = {
#         "Content-Type": "application/json",
#         "X-Auth-Token": os.environ.get("RC_token"),
#         "X-User-Id": os.environ.get("RC_userId")
#     }
    
#     # Clean the message if it contains a response prefix
#     cleaned_message = re.sub(r"^Responding to [\w\.\-]+:\s*", "", message).strip()
    
#     payload = {
#         "channel": f"@{user_id}",
#         "text": f"👤 Human Advisor: {cleaned_message}"
#     }
    
#     response = requests.post(url, json=payload, headers=headers)
#     return response.json()
