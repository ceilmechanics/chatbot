import requests
from flask import Flask, request, jsonify
from advisor import TuftsCSAdvisor
import os
from utils.mongo_config import get_mongodb_connection, close_mongodb_connection
import json
from utils.log_config import setup_logging
import logging
import traceback

app = Flask(__name__)

# log
setup_logging()
logger = logging.getLogger(__name__)


# global variables
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

    This function handles two scenarios:
    1. Initial escalation: Creates a new message in the human operator channel with alert emoji
    2. Thread continuation: Forwards subsequent user messages to an existing thread
    """
    payload = {}
    if not tmid:
        payload = {
            "channel": HUMAN_OPERATOR,
            "text": f"\U0001F6A8 *Escalation Alert* \U0001F6A8\nUser {user} has requested help. Please respond in the thread. \n\n{message}"
        }
    else:
        payload = {
            "channel": HUMAN_OPERATOR,
            "text": f"🎒 *{user} (student):* {message}",
            "tmid": tmid,
            "tmshow": True
        }
        logger.info("forwarding to thread: " + tmid)

    response = requests.post(ROCKETCHAT_URL, json=payload, headers=HEADERS)

    logger.info("successfully forward message to human")
    logger.info(f"DEBUG: RocketChat API Response: {response.status_code} - {response.text}")
    return response.json()

def send_human_response(user, message, tmid):
    """
    Sends a response from a human operator back to the original user via RocketChat.
    """
    payload = {
        "channel": f"@{user}",  # Send directly to the original user
        "text": f"👤 *{HUMAN_OPERATOR} (Human Agent):* {message}",
        "tmid": tmid,
        "tmshow": True
    }

    response = requests.post(ROCKETCHAT_URL, json=payload, headers=HEADERS)
    logger.info(f"DEBUG: RocketChat API Response: {response.status_code} - {response.text}")
    return response.json()

def format_response_with_buttons(response_text, suggested_questions):
    # print("LINE 74, response_data: ", response_data)
    # response_text = response_data["question"]
    # suggested_questions = response_data.get("suggestedQuestions", [])

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
    return response

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

    logger.info("hit /query endpoint, request data: %s", json.dumps(data, indent=2))
    logger.info(f"{user_name} : {message}")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})
    
    mongo_client = None
    try:
        mongo_client = get_mongodb_connection()
        if not mongo_client:
            return jsonify({"text": "Error connecting to database"}), 500
        
        # If it is a thread message, direct forward, no LLM processing needed
        if tmid:
            thread_collection = mongo_client["Users"]["threads"]
            target_thread = thread_collection.find_one({"thread_id": tmid})

            if not target_thread:
                logger.error("thread with id %s does not exist", tmid)
                return jsonify({"text": f"Error: unable to find a matched thread"}), 500

            logger.info("target thread: %s", json.dumps(target_thread, indent=2))
            
            forward_human = target_thread.get("forward_human")
            if forward_human == True:
                forward_thread_id = target_thread.get("forward_thread_id")
                logger.info("forwarding a message from student to human advisor (forward_thread_id " + forward_thread_id + ")")
                send_to_human(user, message, forward_thread_id)
            else:
                forward_username = target_thread.get("forward_username")
                forward_thread_id = target_thread.get("forward_thread_id")
                send_human_response(forward_username, message, forward_thread_id)
            
            return jsonify({"success": True}), 200
    
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

        # Check if question exactly matches a cached question in the database
        # If found, return the cached response with suggested questions without calling the LLM
        faq_collection = mongo_client["freq_questions"]["questions"]
        faq_doc = faq_collection.find_one({"question": message})
        if faq_doc:
            return jsonify(format_response_with_buttons(faq_doc["question"], faq_doc["suggestedQuestions"]))
        
        # If not cached, try semantic checking
        else:
            faq_cursor = faq_collection.find(
                {"question": {"$exists": True}},  
                {"_id": 0, "question": 1, "question_id": 1}  # Projection to only return these fields
            )

            faq_list = []
            for doc in faq_cursor:
                faq_list.append(f"{doc['question_id']}: {doc['question']}")
            
            faq_string = "\n".join(faq_list)
            response_data = json.loads(advisor.get_faq_response(faq_string, message, lastk))
            # logger.info("LLM response: %s ", json.dumps(response_data))

            if response_data.get("cached_question_id"):
                faq_answer = faq_collection.find_one({"question_id": int(response_data["cached_question_id"])})
                response_data = {
                    "response": faq_answer["answer"],
                    "suggestedQuestions": faq_answer["suggestedQuestions"]
                }
                logger.info("cached question exists in db")
                # logger.info("faq retrieved from db %s", json.dumps(faq_answer, indent=2))
                return jsonify(format_response_with_buttons(faq_answer["answer"], faq_answer["suggestedQuestions"]))

            # No matched semantic question, proceed with LLM
            logger.info("question is cached, processed with LLM")
            response_text = response_data["response"]
            rc_payload = response_data.get("rocketChatPayload") 
            
            if rc_payload:
                logger.info("rc_payload exists")
                
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
                thread_collection = mongo_client["Users"]["threads"]
                thread_collection.insert_many(thread_item)
                
                return jsonify({
                    "text": response_text,
                    "tmid": message_id,
                    "tmshow": True
                })

            else:
                return format_response_with_buttons(response_data["response"], response_data["suggestedQuestions"])

    except Exception as e:
        traceback.print_exc()
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