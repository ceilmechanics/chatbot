# util.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import Optional

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