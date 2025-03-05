# util.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from typing import Optional
import requests
from llmproxy import generate


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

def semantic_similarity_check(query):

    system = f"""
    Determine if the user's question is semantically similar to any pre-stored questions. If a semantic match exists, return the matching pre-stored question.

    Return response in JSON format:
    {{"found": true/false, "cachedQuestion": "matched pre-stored question or empty string if not found"}}

    Example:
    User query: "what are classes I need to take to have a CS major?"
    Response: {{"found": true, "cachedQuestion": "What courses are required for the Computer Science major?"}}

    Below are all pre-stored questions:
    1. What courses are required for the Computer Science major?
    2. What are the residency requirements for master's and PhD programs?
    3. What happens if a graduate student fails to maintain continuous enrollment?
    4. What is the time limit for completing a master's degree?
    5. What is the policy for withdrawing from a graduate course?
    6. What are the conditions for receiving financial aid as a graduate student?
    7. What is the policy for parental accommodation for PhD students?
    8. What is the policy for academic dismissal from the graduate program?
    9. How many courses can be transferred for graduate credit?
    10. What are the minimum academic standing requirements for graduate students?
    11. Can international students take a leave of absence?
    """

    response = generate(model = '4o-mini',
        system = system,
        query = query,
        temperature=0.7,
        lastk=0,
        session_id='semantic_similarity_check',
    )

    print("\n>>>>>>>>>>>>>>>>>>>>>>>>> semantic_similarity_check >>>>>>>>>>>>>>>>>>>>")
    print(response["response"])
    print("\n\n")

    return response["response"]
