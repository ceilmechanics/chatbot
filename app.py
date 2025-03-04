import requests
from flask import Flask, request, jsonify
from llmproxy import generate, TuftsCSAdvisor
import uuid
from datetime import datetime
import os
from utils import get_mongodb_connection, get_collection, close_mongodb_connection
import json


app = Flask(__name__)

@app.route('/')
def hello_world():
   return jsonify({"text": 'Hello from Koyeb - you reached the main page!'})

@app.route('/query', methods=['POST'])
def main():
    data = request.get_json() 

    # Extract relevant information
    channel_id = data.get("channel_id")
    user_id = data.get("user_id")
    user_name = data.get("user_name", "Unknown")
    message = data.get("text", "")

    print(f"Received request: {data}")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})

    print(f"Message in channel {channel_id} sent by {user_name} : {message}")

    # Get MongoDB connection once for the entire request
    mongo_client = None
    try:
        mongo_client = get_mongodb_connection()
        if not mongo_client:
            return jsonify({"text": "Error connecting to database"}), 500

        # Handle suggested question button clicks
        if message.startswith("suggested_question_"):
            parts = message.split("_")
            if len(parts) >= 4:  # Format: suggested_question_user_id_index
                button_user_id = parts[2]  # User ID is the 3rd part (index 2)
                question_index = int(parts[3])  # Index is the 4th part (index 3)
                
                # Get the original question from MongoDB
                questions_collection = mongo_client["Users"]["suggested_questions"]
                stored_questions = questions_collection.find_one({"user_id": button_user_id})
                
                if stored_questions and "questions" in stored_questions and len(stored_questions["questions"]) > question_index:
                    message = stored_questions["questions"][question_index]
                else:
                    return jsonify({"text": "Sorry, I couldn't find that question."})

        # Get or create user profile
        user_collection = mongo_client["Users"]["user"]
        user_profile = user_collection.find_one({"user_id": user_id})

        if not user_profile:
            user_profile = {
                "user_id": user_id,
                "username": user_name,
                "last_k": 0,
                "program": "",
                "major": ""
            }
            user_collection.insert_one(user_profile)
        
        # Get response from advisor
        advisor = TuftsCSAdvisor(session_id=f"cs-advising-session-{channel_id}")
        lastk = user_profile.get("last_k", 0)
        advisor_response = advisor.get_response(query=message, lastk=lastk)
    
        # Parse the response
        try:
            # The TuftsCSAdvisor returns JSON with response and suggestedQuestions
            response_data = json.loads(advisor_response)
            response_text = response_data["response"]
            suggested_questions = response_data.get("suggestedQuestions", [])
            
            # Store suggested questions for later retrieval
            if suggested_questions:
                questions_collection = mongo_client["Users"]["suggested_questions"]
                questions_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"questions": suggested_questions}},
                    upsert=True
                )
            
            # Create buttons for each suggested question
            question_buttons = []
            for i, question in enumerate(suggested_questions):
                question_buttons.append({
                    "type": "button",
                    "text": question,
                    "msg": f"suggested_question_{user_id}_{i}",
                    "msg_in_chat_window": True,
                    "msg_processing_type": "sendMessage"
                })
            
            # Construct response with text and suggested question buttons
            response = {
                "text": response_text
            }
            
            # Add suggested questions as buttons if available
            if question_buttons:
                response["attachments"] = [
                    {
                        "title": "You may also be interested in:",
                        "actions": question_buttons
                    }
                ]
            
            return jsonify(response)
            
        except (json.JSONDecodeError, TypeError):
            # If response is not valid JSON, return it as is
            return jsonify({"text": advisor_response})

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"text": f"Error: {str(e)}"}), 500
    
    finally:
        # Always close MongoDB connection
        if mongo_client:
            close_mongodb_connection(mongo_client)

@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5999)