import requests
from flask import Flask, request, jsonify
from advisor import TuftsCSAdvisor
import os
from utils.mongo_config import get_mongodb_connection, close_mongodb_connection
import json
from threading import Lock
import re
from utils.log_config import setup_logging
import logging

app = Flask(__name__)

# log
setup_logging()
logger = logging.getLogger(__name__)

ROCKETCHAT_URL = "https://chat.genaiconnect.net/api/v1/chat.postMessage"

HEADERS = {
    "Content-Type": "application/json",
    "X-Auth-Token": os.environ.get("RC_token"), #Replace with your bot token for local testing or keep it and store secrets in Koyeb
    "X-User-Id": os.environ.get("RC_userId") #Replace with your bot user id for local testing or keep it and store secrets in Koyeb
}

HUMAN_OPERATOR = "@wendan.jiang" 

def send_to_human(user, message, tmid=None):
    """
    Sends a message to a human operator via RocketChat when AI escalation is needed.
    """
    # with lock: 
    # human_mode_users[user] = HUMAN_OPERATOR
    # print(f'DEBUG: Added {user} to human_mode_users: {human_mode_users}')

    payload = {}
    if not tmid:
        payload = {
            "channel": HUMAN_OPERATOR,
            "text": f"\U0001F6A8 *Escalation Alert* \U0001F6A8\nUser {user} has requested help. Please respond in the thread. \n\n{message}"
        }
    else:
        payload = {
            "channel": HUMAN_OPERATOR,
            "text": {message},
            "smid": tmid,
            "tmshow": True
        }

    response = requests.post(ROCKETCHAT_URL, json=payload, headers=HEADERS)
    return response.json()  # Return API response for debugging


# def start_human_response_thread(user, message, tmid):
#     payload = {
#         "channel": f"@{user}"
#         "text"

#     }

def send_human_response(user, message, tmid):
    """
    Sends a response from a human operator back to the original user via RocketChat.
    """
    # with lock:
    payload = {
        "channel": f"@{user}",  # Send directly to the original user
        "text": f"👤 *{HUMAN_OPERATOR} (Human Agent):* {message}",
        "tmid": tmid,
        "tmshow": True
    }
    logger.info(f"DEBUG: Sending cleaned human response from {HUMAN_OPERATOR} to {user}: {message}")
    
    response = requests.post(ROCKETCHAT_URL, json=payload, headers=HEADERS)
    logger.info(f"DEBUG: RocketChat API Response: {response.status_code} - {response.text}")
    return response.json()

# def extract_original_user(bot_message):
#     """
#     Extracts the original user who requested human help from the bot's escalation message.
#     Example bot message:
#     "🚨 Escalation Alert 🚨\nUser wendan.jiang needs assistance!\n\n**Message:** talk to a live representative"
#     """
#     match = re.search(r"User ([\w\.\-]+) needs assistance!", bot_message)
#     if match:
#         return match.group(1)  # Extracts the username (e.g., "wendan.jiang")

#     # Case 2: Human Response Format ("Responding to XYZ")
#     match = re.search(r"Responding to ([\w\.\-]+)", bot_message)
#     if match:
#         return match.group(1)  # Extracts the username
        
#     return None


# # key: message_id sent to bot, value: message_id bot should forward to
# message_threads = {}
# # key: human -> bot
# human_reply_threads = {}

@app.route('/query', methods=['POST'])
def main():
    data = request.get_json() 

    # Extract relevant information
    channel_id = data.get("channel_id")
    user_id = data.get("user_id")
    user_name = data.get("user_name", "Unknown")
    user = user_name
    message = data.get("text", "")
    message_id = data.get("message_id")
    tmid = data.get("tmid", None)

    logger.info("hitting /query endpoint, request data: ")
    logger.info(data)
    logger.info(f"Message in channel {channel_id} sent by {user_name} : {message}")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})
    
    mongo_client = None
    try:
        mongo_client = get_mongodb_connection()
        if not mongo_client:
            return jsonify({"text": "Error connecting to database"}), 500
        
        # checking if it is a thread_message
        if tmid:
            thread_collection = mongo_client["Users"]["threads"]
            target_thread = thread_collection.find_one({"thread_id": tmid})

            if not target_thread:
                logger.error("no thread found")
                return jsonify({"text": f"Error: unable to find a matched thread"}), 500

            print("target thread: ", target_thread)

            # print("message_threads: ", message_threads)
            # print("human_reply_threads: ", human_reply_threads)
            
            forward_human = target_thread.get("forward_human")
            if forward_human == True:
                logger.info("forward a message to human advising")
                forward_thread_id = target_thread.get("forward_thread_id")
                send_to_human(user, message, forward_thread_id)
            else:
                forward_username = target_thread.get("forward_username")
                forward_thread_id = target_thread.get("forward_thread_id")
                send_human_response(forward_username, message, forward_thread_id)
    
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
        lastk = user_profile.get("last_k", 0)
        user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_k": lastk + 1}}
            )
        
        # Get response from advisor
        advisor = TuftsCSAdvisor(user_profile)
        
        faq_response = advisor.get_faq_response(query=message, lastk=lastk)
        print(">>>>>>>>>>> faq >>>>>>>>>>>", faq_response)

        try:
            if faq_response:
                response_data = json.loads(faq_response)
                if not response_data.get("response"):
                    advisor_response = advisor.get_response(query=message, lastk=lastk)
                    response_data = json.loads(advisor_response)
            else:
                advisor_response = advisor.get_response(query=message, lastk=lastk)
                response_data = json.loads(advisor_response)

            print("LINE 188", response_data)

            response_text = response_data["response"]
            suggested_questions = response_data.get("suggestedQuestions", [])
            rc_payload = response_data.get("rocketChatPayload") 
            
            if rc_payload:
                print("THIS is a request requires human help...")
                
                # Extract the payload components
                original_question = rc_payload["originalQuestion"]
                llm_answer = rc_payload.get("llmAnswer")
        
                # Format according to requirements
                formatted_string = ""
                if llm_answer:
                    formatted_string = f"\n❓ Student Question: {original_question}\n\n🤖 AI-Generated Answer: {llm_answer}\n\n🔍 Can you please review this answer for accuracy and completeness?"
                else:
                    formatted_string = f"\n❓ Student Question: {original_question}"

                forward_res = send_to_human(user, formatted_string)
                
                # message_id that starts a new thread on human advisor side
                advisor_messsage_id = forward_res["message"]["_id"]
                print("advisor_message_id: ", advisor_messsage_id)

                thread_item = [{
                    "thread_id": message_id,
                    "forward_thread_id": advisor_messsage_id,
                    "forward_human": True
                }, 
                {
                    "thread_id": advisor_messsage_id,
                    "forward_thread_id": message_id,
                    "forward_human": False,
                    "forward_username": user_name

                }]
                thread_collection.insert_many(thread_item)

                # message_threads[message_id] = advisor_messsage_id

                # human_reply_threads[advisor_messsage_id] = {
                #     "message_id": message_id,
                #     "user_name": user_name
                # }

                # print("LINE 256")
                # print("message_threads: ", message_threads)
                # print("human_reply_threads: ", human_reply_threads)

                # print("LINE 84", forward_res)
                
                return jsonify({
                    "text": response_text,
                    "tmid": message_id,
                    "tmshow": True
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