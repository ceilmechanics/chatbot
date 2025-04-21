# Standard library imports
import os
import json
import logging
import traceback

# Third-party imports
import requests
from bson.objectid import ObjectId
from flask import Flask, request, jsonify, redirect, render_template

# Local application imports
from advisor import TuftsCSAdvisor
from utils.mongo_config import get_collection, get_mongodb_connection
from utils.log_config import setup_logging
from utils.emails import send_notification_email

app = Flask(__name__)

# log
setup_logging()
logger = logging.getLogger(__name__)

# global variables
RC_BASE_URL = "https://chat.genaiconnect.net/api/v1"

HEADERS = {
    "Content-Type": "application/json",
    "X-Auth-Token": os.environ.get("RC_token"),
    "X-User-Id": os.environ.get("RC_userId")
}

HUMAN_OPERATOR = "@wendan.jiang" 

def is_json_object(json_string):
    try:
        parsed = json.loads(json_string)
        if isinstance(parsed, dict):
            return parsed
        return None
    except json.JSONDecodeError:
        return None

def send_to_human(user, original_question, llm_answer=None, tmid=None, trigger_msg_id=None, uncertain_areas=None):
    """
    Sends a message to a human operator via RocketChat when AI escalation is needed.

    This function handles two scenarios:
    1. Initial escalation: Creates a new message in the human operator channel with alert emoji
    2. Thread continuation: Forwards subsequent user messages to an existing thread
    """

    # initial message sent to human advisor (without thread created)
    payload = {}
    if not tmid and not trigger_msg_id:
        formatted_string = f"🚨 *Escalation Alert* 🚨\n Student {user} has requested help. \n"
        formatted_string += f"\n💬 Student Question: {original_question}"
        formatted_string += f"\n\n Please click on *View Thread* to view the AI-generated response designed to help you address student questions.\n"
        
        # Format payload with the modified button
        payload = {
            "channel": HUMAN_OPERATOR,
            "text": formatted_string,
        }

    # follow-up message that starts a new thread on the initial message
    # to display AI-generated answer with copy button
    elif trigger_msg_id:
        formatted_string = "I've generated a response to help you address student questions based on available information. If you find this AI-generated answer helpful, *click ✏️ Copy to chat button* to paste it to your chatbox. \n\n"
        formatted_string += f"🤖 AI-Generated Answer: {llm_answer}\n\n"
        formatted_string += f"🤔 Reason for uncertainty: {uncertain_areas}"
        payload = {
            "channel": HUMAN_OPERATOR,
            "text": formatted_string,
            "attachments": [
                {
                    "title": "AI response looks good?",
                    "actions": [
                        {
                            "type": "button",
                            "text": "✏️ Copy to chat",
                            "msg": llm_answer,
                            "msg_in_chat_window": True,
                            "msg_processing_type": "respondWithMessage"
                        }
                    ]
                }
            ],
            "tmid": trigger_msg_id
        }

        # TODO: collect feedback from Johnny to see what is his preference
        # for now, only forward initial escalation message to human advisor
        # send_notification_email(user, original_question, llm_answer, True)
    
    # forwarding message
    else:
        payload = {
            "channel": HUMAN_OPERATOR,
            "text": f"🐘 *{user} (student):* {original_question}",
            "tmid": tmid
        }
        logger.info("forwarding to thread: " + tmid)

    response = requests.post(f"{RC_BASE_URL}/chat.postMessage", json=payload, headers=HEADERS)

    logger.info("successfully forward message to human")
    logger.info(f"DEBUG: RocketChat API Response: {response.status_code} - {response.text}")
    return response.json()

def send_human_response(room_id, message, tmid):
    """
    Sends a response from a human operator back to the original user via RocketChat.
    """
    payload = {
        "roomId": room_id,  # Send directly to the original user
        "text": f"👤 *{HUMAN_OPERATOR} (Human Advisor):* {message}",
        "tmid": tmid
    }

    response = requests.post(f"{RC_BASE_URL}/chat.postMessage", json=payload, headers=HEADERS)
    logger.info(f"DEBUG: RocketChat API Response: {response.status_code} - {response.text}")
    return response.json()

def send_loading_response(room_id):
    payload = {
        "roomId": room_id,
        "text": f" :everything_fine_parrot: Processing your inquiry. One moment please..."
    }

    response = requests.post(f"{RC_BASE_URL}/chat.postMessage", json=payload, headers=HEADERS)
    logger.info(f"DEBUG: RocketChat API Response: {response.status_code} - {response.text}")

    if response.status_code == 200:
        json_res = response.json()
        return json_res["message"]["rid"], json_res["message"]["_id"]
    else:
        raise Exception("fail to send loading message")
    
def update_loading_message(room_id, loading_msg_id, text=" :kirby_hi: Ta-da! Your answer is ready!"):
    requests.post(f"{RC_BASE_URL}/chat.update",
                  json={
                      "roomId": room_id,
                      "msgId": loading_msg_id,
                      "text": text
                  },
                  headers=HEADERS)

def format_response_with_buttons(response_text, suggested_questions, category_id):
    question_buttons = []
    if category_id == "2":
        for i, question in enumerate(suggested_questions, 1):  # Start numbering from 1
            question_buttons.append({
                "type": "button",
                "text": f"{i}",  # Just show the number
                "msg": question,  # Send the full question when clicked
                "msg_in_chat_window": True,
                "msg_processing_type": "sendMessage",
            })

        question_buttons.append({
            "type": "button",
            "text": f"🚀 Human support",
            "msg": "Talk to a human advisor",
            "msg_in_chat_window": True,
            "msg_processing_type": "sendMessage",
        })   

        # Construct response with numbered questions in text and numbered buttons
        numbered_questions = "\n".join([f"{i}. {question}" for i, question in enumerate(suggested_questions, 1)])       
        response = {
            "text": response_text + "\n\n :kirby: You might also want to know:\n" + numbered_questions,
            "attachments": [
                {
                    "title": "Pick a question, or connect with a human",
                    "actions": question_buttons
                }
            ]
        }
        return response
    else:
        question_buttons.append({
            "type": "button",
            "text": f"🚀 Connect",  # Just show the number
            "msg": "Talk to a human advisor",  # Send the full question when clicked
            "msg_in_chat_window": True,
            "msg_processing_type": "sendMessage",
        })

        return {
            "text": response_text,
                "attachments": [
                    {
                        "title": "Connecting to a human advisor?",
                        "actions": question_buttons
                    }
                ]
        }

def format_summary_confirmation(original_question):
    """
    Format a message with the summary of the student's situation and ask for confirmation
    before escalating to a human advisor.
    """

    summary = "Before I forward your request, please confirm if this is the question you'd like to ask a human advisor.\n"
    summary += "If it looks good, click the **Correct & Send** button, and I'll pass it along. Need to make edits? Just click **Modify my question**.\n\n"    
    summary += f"🤔 Student Question: {original_question} \n\n"
    summary += "😊 To help the advisor better assist you, if you haven't shared your academic information with us yet, you're welcome to complete it using [this link]. No pressure though — it's **totally optional**!"

    return {
        "text": summary,
        "attachments": [
            {
                "actions": [
                    {
                        "type": "button",
                        "text": "✅ Correct & Send",
                        # "msg": " :coll_doge_gif: Successfully forwarded your question to a human advisor. \n📬 To begin your conversation with your human advisor, please click the \"**View Thread**\" button.",
                        "msg": original_question,
                        "msg_in_chat_window": True
                    },
                    {
                        "type": "button",
                        "text": "✏️ Modify my question", 
                        "msg": original_question,
                        "msg_processing_type": "respondWithMessage",
                        "msg_in_chat_window": True
                    }
                ]
            }
        ]
    }

def build_bidirectional_threads(user, original_question, llm_answer, message_id, uncertain_areas):
    # Forward to human advisor and get the response
    forward_res = send_to_human(user, original_question)

    # message_id starts a new thread on human advisor side
    # send a thread message that contains AI-generated response
    advisor_messsage_id = forward_res["message"]["_id"]
    send_to_human(user, original_question, llm_answer, trigger_msg_id=advisor_messsage_id, uncertain_areas=uncertain_areas)

    # Create bidirectional thread mapping for ongoing conversation
    thread_item = [{
        "thread_id": message_id,
        "forward_thread_id": advisor_messsage_id,
        "forward_human": True
    }, 
    {
        "thread_id": advisor_messsage_id,
        "forward_thread_id": message_id,
        "forward_human": False,
        "forward_username": user

    }]
    thread_collection = get_collection("Users", "threads")
    thread_collection.insert_many(thread_item)


@app.route('/query', methods=['POST'])
def main():
    """
    Main endpoint for handling user queries to the Tufts CS Advisor.
    """
    data = request.get_json() 

    logger.info("add a debug line to verify if the code is modified or not")

    # Extract relevant information
    user_id = data.get("user_id")
    user_name = data.get("user_name", "Unknown")
    user = user_name
    message = data.get("text", "")
    message_id = data.get("message_id")
    tmid = data.get("tmid", None)
    channel_id = data.get("channel_id")

    # Log the incoming request
    logger.info("hit /query endpoint, request data: %s", json.dumps(data, indent=2))
    logger.info(f"{user_name} : {message}")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})
    
    # Handle button message
    # parsed_msg = is_json_object(message)
    # if parsed_msg:
    #     llm_answer = parsed_msg.get("llm_answer")
    #     tmid = parsed_msg.get("tmid")
    #     user = parsed_msg.get("user")

    #     if llm_answer and tmid and user:
    #         send_human_response(channel_id, llm_answer, tmid)
    #         # delete the message
    #         response = requests.post(f"{RC_BASE_URL}/chat.delete", json={
    #                 "roomId": channel_id,
    #                 "msgId": message_id
    #             }, 
    #             headers={
    #                 "Content-Type": "application/json",
    #                 "X-Auth-Token": os.environ.get("RC_advisor_token"),
    #                 "X-User-Id": user_id
    #             })
    #         print("delete response", response)
    #         # logger.info("deleting button msg response: %s", json.dumps(response, indent=2))
    #         return jsonify({"success": True}), 200
    
    try:
        # Get MongoDB client from the connection pool
        mongo_client = get_mongodb_connection()
        if not mongo_client:
            return jsonify({"text": "Error connecting to database"}), 500
        
        user_collection = get_collection("Users", "user")
        user_profile = user_collection.find_one({"user_id": user_id})
        
        # === QUESTION SUMMARY HANDLING ===
        if user_profile and user_profile.get("pending_escalation") is True:
            _, loading_msg_id = send_loading_response(channel_id)

            advisor = TuftsCSAdvisor(user_profile)
            response_data = advisor.get_escalated_response(message)

            llm_answer = response_data.get("llmAnswer")
            uncertain_areas = response_data.get("uncertainAreas")

            # error handling
            if not llm_answer or not uncertain_areas:
                user_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"pending_escalation": False}}  # Set pending_escalation to True
                )
                update_loading_message(channel_id, loading_msg_id, "error processing your escalation request to human advisors, please try again")
                return jsonify({"success": True}), 200

            # Forward to human advisor and get the response
            build_bidirectional_threads(user_name, message, llm_answer, message_id, uncertain_areas)

            # flip pending_escalation back to false
            user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"pending_escalation": False}}  # Set pending_escalation to True
            )
            update_loading_message(channel_id, loading_msg_id, " :coll_doge_gif: Successfully forwarded your question to a human advisor. \n📬 To begin your conversation, please click the \"**View Thread**\" button.")
            return jsonify({"success": True}), 200
        
        # ==== THREAD MESSAGE HANDLING ====
        # If message is part of an existing thread, handle direct forwarding without LLM processing
        if tmid:
            logger.info("Processing thread message - direct forwarding without LLM processing")
            thread_collection = get_collection("Users", "threads")
            target_thread = thread_collection.find_one({"thread_id": tmid})

            if not target_thread:
                logger.error("thread with id %s does not exist", tmid)
                return jsonify({"text": f"Error: unable to find a matched thread"}), 500
            
            # Determine message direction (student to human advisor or vice versa)
            forward_human = target_thread.get("forward_human")
            if forward_human == True:
                forward_thread_id = target_thread.get("forward_thread_id")
                logger.info("forwarding a message from student to human advisor (forward_thread_id " + forward_thread_id + ")")
                send_to_human(user, message, tmid=forward_thread_id)
            else:
                # forward_username = target_thread.get("forward_username")
                forward_thread_id = target_thread.get("forward_thread_id")
                send_human_response(channel_id, message, forward_thread_id)
            
            return jsonify({"success": True}), 200
    
        # ==== USER PROFILE MANAGEMENT ====
        # Get or create user profile for tracking interactions
        if not user_profile:
            user_profile = {
                "user_id": user_id,
                "username": user_name,
                "last_k": 0,
                "transcript": {
                    "program": "",
                    "completed_courses": [{
                        "course_id": "CS112",
                        "grade": "A"
                    }],
                    "credits_earned": "",
                    "GPA": "",
                    "domestic": ""
                }
            }
            user_collection.insert_one(user_profile)

        # Update the interaction counter for this user
        lastk = user_profile.get("last_k", 0)
        user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_k": lastk + 1}}
            )

        # Initialize the advisor with user profile data
        advisor = TuftsCSAdvisor(user_profile)

        # ==== FAQ MATCHING - EXACT MATCH ====
        # Check if question exactly matches a cached question in the database
        # faq_collection = get_collection("freq_questions", "questions")
        # faq_doc = faq_collection.find_one({"question": message})
        # if faq_doc:
        #     logger.info("Found exact FAQ match - returning cached response")
        #     return jsonify(format_response_with_buttons(faq_doc["answer"], faq_doc["suggestedQuestions"]))
        
        # ==== FAQ MATCHING - SEMANTIC MATCH ====
        # If no exact match, try semantic matching with all FAQs
        # else:

        # Prompting loading message
        room_id, loading_msg_id = send_loading_response(channel_id)

        # faq_cursor = faq_collection.find(
        #     {"question": {"$exists": True}},  
        #     {"_id": 0, "question": 1, "question_id": 1}  # Projection to only return these fields
        # )

        # faq_list = []
        # for doc in faq_cursor:
        #     faq_list.append(f"{doc['question_id']}: {doc['question']}")
        # faq_string = "\n".join(faq_list)
        # response_data = json.loads(advisor.get_cached_response(faq_string, message))

        # Check if LLM found a semantically similar FAQ
        # if response_data.get("cached_question_id"):
        #     faq_answer = faq_collection.find_one({"question_id": int(response_data["cached_question_id"])})
        #     logger.info(f"Found semantic FAQ match with confidence score {response_data["confidence"]} - returning cached response")

        #     response_data = {
        #         "response": faq_answer["answer"],
        #         "suggestedQuestions": faq_answer["suggestedQuestions"]
        #     }
        #     update_loading_message(room_id, loading_msg_id)
        #     return jsonify(format_response_with_buttons(faq_answer["answer"], faq_answer["suggestedQuestions"]))

        # ==== LLM PROCESSING ====
        # No cached or semantic match found, process with LLM
        logger.info("No FAQ match found - processing with LLM")

        raw_res = advisor.get_faq_response(None, message)
        print(raw_res)
        
        response_data = json.loads(raw_res)
        response_text = response_data["response"]
        category_id = response_data.get("category_id")
        rc_payload = response_data.get("rocketChatPayload") 
        
        # ==== HUMAN ESCALATION ====
        # category_id=4, user explicitly wants to talk to a human advisor
        if category_id == "4":
            original_question = rc_payload["originalQuestion"]
            user_collection = get_collection("Users", "user")

            user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"pending_escalation": True}}  # Set pending_escalation to True
            )

            response = requests.post(f"{RC_BASE_URL}/chat.update", json={
                "roomId": room_id,
                "msgId": loading_msg_id,
                "text": response_text
            }, headers=HEADERS)

            return format_summary_confirmation(original_question)

        # Check if LLM determined human escalation is needed
        elif rc_payload:
            logger.info("rc_payload exists")
            
            # Extract the payload components
            original_question = rc_payload["originalQuestion"]
            llm_answer = rc_payload.get("llmAnswer")
            uncertain_areas = rc_payload.get("uncertainAreas")

            build_bidirectional_threads(user, original_question, llm_answer, message_id, uncertain_areas)

            # # Forward to human advisor and get the response
            # forward_res = send_to_human(user, original_question)

            # # message_id starts a new thread on human advisor side
            # # send a thread message that contains AI-generated response
            # advisor_messsage_id = forward_res["message"]["_id"]
            # send_to_human(user, original_question, llm_answer, trigger_msg_id=advisor_messsage_id, uncertain_areas=uncertain_areas)

            # # Create bidirectional thread mapping for ongoing conversation
            # thread_item = [{
            #     "thread_id": message_id,
            #     "forward_thread_id": advisor_messsage_id,
            #     "forward_human": True
            # }, 
            # {
            #     "thread_id": advisor_messsage_id,
            #     "forward_thread_id": message_id,
            #     "forward_human": False,
            #     "forward_username": user_name

            # }]
            # thread_collection = get_collection("Users", "threads")
            # thread_collection.insert_many(thread_item)
            
            # delete loading msg
            # response = requests.post(f"{RC_BASE_URL}/chat.update", json={
            #     "roomId": room_id,
            #     "msgId": loading_msg_id,
            #     "text": f" :coll_doge_gif: {response_text} \n📬 To begin your conversation, please click the \"**View Thread**\" button."
            # }, headers=HEADERS)
            update_loading_message(room_id, loading_msg_id, f" :coll_doge_gif: {response_text} \n📬 To begin your conversation, please click the \"**View Thread**\" button.")

            print(response.json())

            return jsonify({
                "text": response_text,
                "tmid": message_id
            })

        # ==== STANDARD LLM RESPONSE ====
        # Return LLM-generated response with suggested follow-up questions
        else:
            logger.info("Returning standard LLM response with suggested questions")
            update_loading_message(room_id, loading_msg_id)
            return format_response_with_buttons(response_data["response"], response_data.get("suggestedQuestions"), category_id)

    except Exception as e:
        traceback.print_exc()
        print(f"Error processing request: {str(e)}")
        return jsonify({"text": f"Error: {str(e)}"}), 500

@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

@app.route('/')
def hello_world():
   return jsonify({"text": 'Hello from Koyeb - you reached the main page!'})

@app.route('/faqs', methods=['GET', 'POST'])
def display_faqs():
    """
    Endpoint to display and edit the freq_questions database.
    """
    try:
        # Get MongoDB client from the connection pool
        mongo_client = get_mongodb_connection()
        if not mongo_client:
            return jsonify({"error": "Error connecting to database"}), 500
        
        # Focus specifically on freq_questions database
        db_name = "freq_questions"
        collection_name = "questions"
        
        # Handle form submission for updating documents
        if request.method == 'POST' and request.form.get('action') == 'update':
            doc_id = request.form.get('doc_id')
            question = request.form.get('question')
            answer = request.form.get('answer')
            question_id = request.form.get('question_id')
            
            # Get suggested questions (they come as a list)
            suggested_questions = []
            i = 0
            while True:
                sq = request.form.get(f'suggested_question_{i}')
                if sq is None:
                    break
                suggested_questions.append(sq)
                i += 1
            
            # Convert question_id to integer if it exists
            if question_id:
                try:
                    question_id = int(question_id)
                except ValueError:
                    return "Question ID must be an integer", 400
            
            # Update the document
            collection = mongo_client[db_name][collection_name]
            collection.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {
                    "question": question,
                    "answer": answer,
                    "question_id": question_id,
                    "suggestedQuestions": suggested_questions
                }}
            )
            
            # Redirect to avoid form resubmission
            return redirect('/faqs')
        
        # Handle form submission for adding new documents
        elif request.method == 'POST' and request.form.get('action') == 'add':
            question = request.form.get('question')
            answer = request.form.get('answer')
            
            # Get suggested questions
            suggested_questions = []
            i = 0
            while True:
                sq = request.form.get(f'new_suggested_question_{i}')
                if sq is None or sq == '':
                    break
                suggested_questions.append(sq)
                i += 1
            
            # Get all documents to determine highest question_id
            collection = mongo_client[db_name][collection_name]
            all_docs = list(collection.find({}, {"question_id": 1}))
            
            # Find the highest question_id
            highest_id = 0
            for doc in all_docs:
                if 'question_id' in doc and isinstance(doc['question_id'], int) and doc['question_id'] > highest_id:
                    highest_id = doc['question_id']
            
            # Use the next available ID
            next_id = highest_id + 1
            
            # Insert the new document
            collection.insert_one({
                "question": question,
                "answer": answer,
                "question_id": next_id,
                "suggestedQuestions": suggested_questions
            })
            
            # Redirect to avoid form resubmission
            return redirect('/faqs')
        
        # Handle document deletion
        elif request.method == 'POST' and request.form.get('action') == 'delete':
            doc_id = request.form.get('doc_id')
            collection = mongo_client[db_name][collection_name]
            collection.delete_one({"_id": ObjectId(doc_id)})
            return redirect('/faqs')
        
        # Get all documents from freq_questions.questions collection
        collection = mongo_client[db_name][collection_name]
        
        # Sort by question_id for better organization
        documents = list(collection.find({}).sort("question_id", 1))
        
        # Get the highest question_id for new questions
        highest_id = 0
        for doc in documents:
            if 'question_id' in doc and isinstance(doc['question_id'], int) and doc['question_id'] > highest_id:
                highest_id = doc['question_id']
        
        # Convert ObjectId to string for display
        for doc in documents:
            doc['_id'] = str(doc['_id'])
        
        # Pass data to the template and render it
        return render_template(
            'faqs.html',  # Use the combined template
            documents=documents,
            next_id=highest_id + 1,
            enumerate=enumerate
        )
    
    except Exception as e:
        logger.error(f"Error in database view: {str(e)}")
        return render_template('error.html', error_message=str(e))


if __name__ == "__main__":
    # Register shutdown handler to close MongoDB connection when app stops
    import atexit
    from utils.mongo_config import close_mongodb_connection
    atexit.register(close_mongodb_connection)
    
    app.run(debug=True, host="0.0.0.0", port=5999)