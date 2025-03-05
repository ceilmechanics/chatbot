import requests
from flask import Flask, request, jsonify
from llmproxy import generate, TuftsCSAdvisor
import uuid
from datetime import datetime
import os
from utils import get_mongodb_connection, close_mongodb_connection
import json
from threading import Lock
import re

app = Flask(__name__)

human_mode_users = {} 
ROCKETCHAT_URL = "https://chat.genaiconnect.net/api/v1/chat.postMessage"

HEADERS = {
    "Content-Type": "application/json",
    "X-Auth-Token": os.environ.get("RC_token"), #Replace with your bot token for local testing or keep it and store secrets in Koyeb
    "X-User-Id": os.environ.get("RC_userId") #Replace with your bot user id for local testing or keep it and store secrets in Koyeb
}

HUMAN_OPERATOR = "@wendan.jiang" 
lock = Lock()
human_mode_users = {}

def send_to_human(user, rc_payload):
    """
    Sends a message to a human operator via RocketChat when AI escalation is needed.
    """
    with lock: 
        human_mode_users[user] = HUMAN_OPERATOR
        print(f'DEBUG: Added {user} to human_mode_users: {human_mode_users}')
        payload = {
            "channel": HUMAN_OPERATOR,  # Send as a DM to the human operator
            "text": rc_payload["text"]
        }
        response = requests.post(ROCKETCHAT_URL, json=payload, headers=HEADERS)
        return response.json()  # Return API response for debugging

def send_human_response(user, message, human_operator):
    """
    Sends a response from a human operator back to the original user via RocketChat.
    """
    with lock:
        payload = {
            "channel": f"@{user}",  # Send directly to the original user
            "text": f"👤 *{human_operator} (Human Agent):* {message}"
        }
        print(f"DEBUG: Sending cleaned human response from {human_operator} to {user}: {message}")
        
        response = requests.post(ROCKETCHAT_URL, json=payload, headers=HEADERS)
        print(f"DEBUG: RocketChat API Response: {response.status_code} - {response.text}")

        return response.json()

def extract_original_user(bot_message):
    """
    Extracts the original user who requested human help from the bot's escalation message.
    Example bot message:
    "🚨 Escalation Alert 🚨\nUser wendan.jiang needs assistance!\n\n**Message:** talk to a live representative"
    """
    match = re.search(r"User ([\w\.\-]+) needs assistance!", bot_message)
    if match:
        return match.group(1)  # Extracts the username (e.g., "wendan.jiang")

    # Case 2: Human Response Format ("Responding to XYZ")
    match = re.search(r"Responding to ([\w\.\-]+)", bot_message)
    if match:
        return match.group(1)  # Extracts the username
        
    return None

@app.route('/query', methods=['POST'])
def main():
    data = request.get_json() 

    # Extract relevant information
    channel_id = data.get("channel_id")
    user_id = data.get("user_id")
    user_name = data.get("user_name", "Unknown")
    user = user_name
    message_id = data.get("message_id")
    message = data.get("text", "")

    print(f"Received request: {data}")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})

    print(f"Message {message_id} in channel {channel_id} sent by {user_name} : {message}")

    if message.lower() == "exit" and user in human_mode_users:
        return jsonify({"text": f"{user}, you are now back in bot mode."})
        # if user in human_mode_users:
        #     del human_mode_users[user] 
        #     print(f"DEBUG: USER NOW BACK IN BOT MODE")
        #     return jsonify({"text": f"{user}, you are now back in bot mode."})
        # return jsonify({"text": f"{user}, you were not in human mode."})

    # TODO: if user_id == human_assistant_id
    if message.startswith("Responding to"):
        print("DEBUG: Detected human response from Blair. Forwarding to user.")

        # Extract original user from the message
        original_user = extract_original_user(message)

        if not original_user:
            return jsonify({"error": "No user found to respond to."}), 400
        
        human_mode_users[original_user] = user

        # Send response to the original user
        cleaned_message = re.sub(r"Responding to [\w\.\-]+:\s*", "", message).strip()
        print(f"DEBUG: Forwarding cleaned message: '{cleaned_message}' to {original_user}")

        # TODO: processing with LLM and send back
        response = send_human_response(original_user, cleaned_message, user)
        ##response = send_human_response(original_user, message.replace("Responding to", "").strip(), user)
        return jsonify(response)
    
    if user in human_mode_users:
        print(f"DEBUG: {user} is in human mode. Forwarding to human.")
        send_to_human(user, message)
        return jsonify({"text": "Your message has been sent to a human."})

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

        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ADVISOR RESPONSE >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")
        print(advisor_response)
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ADVISOR RESPONSE >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n\n")

        # Update lastk in the database
        user_collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_k": lastk + 1}}
        )
    
        # Parse the response
        try:
            # The TuftsCSAdvisor returns JSON with response and suggestedQuestions
            response_data = json.loads(advisor_response)
            response_text = response_data["response"]
            suggested_questions = response_data.get("suggestedQuestions", [])
            rc_payload = response_data.get("rocketChatPayload") 
            
            if rc_payload:
                print("LINE 81 there is rc_payload provided, response forwarded")

                forward_res = send_to_human(user, rc_payload)
                print("LINE 84", forward_res)
                
                return jsonify({
                    "text": response_text
                })

            else:
                # Create numbered buttons for suggested questions
                question_buttons = []
                for i, question in enumerate(suggested_questions, 1):  # Start numbering from 1
                    question_buttons.append({
                        "type": "button",
                        "text": f"{i}",  # Just show the number
                        "msg": question,  # Send the full question when clicked
                        "msg_in_chat_window": True,
                        "msg_processing_type": "sendMessage",
                    })
                    
                # Construct response with numbered questions in text and numbered buttons
                numbered_questions = "\n".join([f"{i}. {question}" for i, question in enumerate(suggested_questions, 1)])

                response = {
                    "text": response_text + "\n\n🤔 You might also want to know:\n" + numbered_questions,
                    "attachments": [
                        {
                            "title": "Click a number to ask that question:",
                            "actions": question_buttons
                        }
                    ]
                }

                print (response)
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

@app.route('/')
def hello_world():
   return jsonify({"text": 'Hello from Koyeb - you reached the main page!'})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5999)