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
            
            # Create a more visually appealing response with cards for suggested questions
            suggested_questions_blocks = []

            # Group questions into pairs for a two-column layout when possible
            for i in range(0, len(suggested_questions), 2):
                # Create buttons for this row
                row_buttons = []
                
                # Add first button in pair
                row_buttons.append({
                    "type": "button",
                    "text": suggested_questions[i],
                    "style": "primary",  # Blue, prominent styling
                    "msg": suggested_questions[i],  # Use the actual question text
                    "msg_in_chat_window": True,
                    "msg_processing_type": "sendMessage"
                })
                
                # Add second button if available
                if i + 1 < len(suggested_questions):
                    row_buttons.append({
                        "type": "button",
                        "text": suggested_questions[i + 1],
                        "style": "default",  # Standard styling
                        "msg": suggested_questions[i + 1],  # Use the actual question text
                        "msg_in_chat_window": True,
                        "msg_processing_type": "sendMessage"
                    })
                
                # Add this row as a section
                suggested_questions_blocks.append({
                    "type": "actions",
                    "elements": row_buttons
                })

            # Construct the enhanced response
            response = {
                "text": response_text,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response_text
                        }
                    }
                ]
            }

            # Add divider and heading for suggested questions if available
            if suggested_questions_blocks:
                response["blocks"].extend([
                    {
                        "type": "divider"
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "💡 You might also want to know:",
                            "emoji": True
                        }
                    }
                ])
                
                # Add all question blocks
                response["blocks"].extend(suggested_questions_blocks)
            
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