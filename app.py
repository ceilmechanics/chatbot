import requests
from flask import Flask, request, jsonify
from llmproxy import generate, TuftsCSAdvisor

app = Flask(__name__)

@app.route('/')
def hello_world():
   return jsonify({"text":'Hello from Koyeb - you reached the main page!'})

@app.route('/query', methods=['POST'])
def main():
    data = request.get_json() 

    # Extract relevant information
    user = data.get("user_name", "Unknown")
    message = data.get("text", "")

    print(data)

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})

    print(f"Message from {user} : {message}")

    try:
        # Generate response using CS Advisor
        response = TuftsCSAdvisor.get_response(message)
        return jsonify({"text": response})

    except Exception as e:
        return jsonify({"text": f"Error: {str(e)}"}), 500
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    app.run()