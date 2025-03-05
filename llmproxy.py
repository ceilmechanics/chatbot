import os
import json
import requests
from typing import Tuple
from dotenv import load_dotenv

load_dotenv()

# Read proxy config from environment
end_point = os.environ.get("endPoint")
api_key = os.environ.get("apiKey")

def generate(
	model: str,
	system: str,
	query: str,
	temperature: float | None = None,
	lastk: int | None = None,
	session_id: str | None = None,
    rag_threshold: float | None = 0.5,
    rag_usage: bool | None = False,
    rag_k: int | None = 0
	):
	
    headers = {
        'x-api-key': api_key
    }

    request = {
        'model': model,
        'system': system,
        'query': query,
        'temperature': temperature,
        'lastk': lastk,
        'session_id': session_id,
        'rag_threshold': rag_threshold,
        'rag_usage': rag_usage,
        'rag_k': rag_k
    }
    msg = None
    try:
        response = requests.post(end_point, headers=headers, json=request)
        if response.status_code == 200:
            res = json.loads(response.text)
            msg = {'response':res['result'],'rag_context':res['rag_context']}
        else:
            msg = f"Error: Received response code {response.status_code}"
    except requests.exceptions.RequestException as e:
        msg = f"An error occurred: {e}"
    return msg

def upload(multipart_form_data):
    headers = {
        'x-api-key': api_key
    }

    msg = None
    try:
        response = requests.post(end_point, headers=headers, files=multipart_form_data)
        
        if response.status_code == 200:
            msg = "Successfully uploaded. It may take a short while for the document to be added to your context"
        else:
            msg = f"Error: Received response code {response.status_code}"
    except requests.exceptions.RequestException as e:
        msg = f"An error occurred: {e}"
    
    return msg


def pdf_upload(
    path: str,    
    strategy: str | None = None,
    description: str | None = None,
    session_id: str | None = None
    ):
    
    params = {
        'description': description,
        'session_id': session_id,
        'strategy': strategy
    }

    multipart_form_data = {
        'params': (None, json.dumps(params), 'application/json'),
        'file': (None, open(path, 'rb'), "application/pdf")
    }

    response = upload(multipart_form_data)
    return response

# def text_upload(
#     text: str,    
#     strategy: str | None = None,
#     description: str | None = None,
#     session_id: str | None = None
#     ):
    
#     params = {
#         'description': description,
#         'session_id': session_id,
#         'strategy': strategy
#     }


#     multipart_form_data = {
#         'params': (None, json.dumps(params), 'application/json'),
#         'text': (None, text, "application/text")
#     }


#     response = upload(multipart_form_data)
#     return response


class RAGParameterInference:
    def __init__(self):
        self.session_id = 'rag-parameter-inference'
        self.inference_prompt = '''You are determining RAG parameters for a CS graduate student advising chatbot at Tufts School of Engineering.

        Consider the following patterns when suggesting RAG parameters:

        High Precision Needed (higher threshold ~0.8, lower k ~3):
        - Questions about specific course requirements
        - Questions about thesis/project deadlines
        - Specific visa/international student policies
        - Department-specific deadlines
        
        Balanced Context (medium threshold ~0.7, medium k ~5):
        - Questions about course selection
        - Academic standing policies
        - Research opportunities
        - Transfer credit policies
        
        Broader Context (lower threshold ~0.6, higher k ~7):
        - General program planning
        - Career development questions
        - Lab/research group information
        - Campus resources

        Return only a JSON string in this exact format:
        {
            "rag_usage": <true/false>,
            "rag_threshold": <0.0-1.0>,
            "rag_k": <1-10>,
            "reasoning": "<brief explanation of why these parameters were chosen>"
        }'''

    def infer_rag_params(self, query: str) -> Tuple[bool, float, int]:
        try:
            llm_response = generate(
                model='4o-mini',
                system=self.inference_prompt,
                query=f"Determine appropriate RAG parameters for this graduate student query: {query}",
                temperature=0.0,
                lastk=0,
                session_id=self.session_id,
                rag_usage=False
            )
            
            if isinstance(llm_response, dict) and 'response' in llm_response:
                response_str = llm_response['response']
            else:
                response_str = llm_response
                
            try:
                result = json.loads(response_str)
                return (
                    result['rag_usage'],
                    result['rag_threshold'],
                    result['rag_k']
                )
            except json.JSONDecodeError:
                return True, 0.7, 5
                
        except Exception as e:
            return True, 0.7, 5

class TuftsCSAdvisor:
    def __init__(self, pdf_path='soe-grad-handbook.pdf', session_id=None):
        self.session_id = session_id or 'Tufts-CS-Advisor-default'
        # self.parameter_inference = RAGParameterInference()

        # print("\n>>>>>>>>>>>>>>>>>>>>>>>>> RAG inference results >>>>>>>>>>>>>>>>>>>>> \n")
        # print(RAGParameterInference)
        # print("\n\n")

        # use_rag = self.parameter_inference.infer_rag_params(query)
        
        
        # print(f"\n📚 Loading handbook for session {self.session_id}...")
        # try:
        #     upload_response = pdf_upload(
        #         path=pdf_path,
        #         session_id=self.session_id,
        #         strategy='smart'
        #     )
        #     print("✅ Handbook loaded successfully")
        # except Exception as e:
        #     print(f"❌ Error loading handbook: {str(e)}")

    def get_response(self, query: str, lastk: int = 0) -> str:
        """
        Get response using inferred RAG parameters
        
        Args:
            query: User's question
            lastk: Number of previous exchanges to include for context
        """
        rag_usage, threshold, k = self.parameter_inference.infer_rag_params(query)
        print("\n>>>>>>>>>>>>>>>>>>>>>>>>> RAG inference results >>>>>>>>>>>>>>>>>>>>> \n")
        print(RAGParameterInference)
        print(f"\nSession {self.session_id} - RAG params: rag_usage={rag_usage}, threshold={threshold}, k={k}, lastk={lastk}")
        print("\n\n")

        if lastk == 0 and rag_usage is True:
            # print(f"\n📚 Loading handbook for session {self.session_id}...")
            try:
                upload_response = pdf_upload(
                    path='soe-grad-handbook.pdf',
                    session_id=self.session_id,
                    strategy='smart'
                )
                print("✅ Handbook loaded successfully")
            except Exception as e:
                print(f"❌ Error loading handbook: {str(e)}")

        response = generate(
            model='4o-mini',
            system=self.get_system_prompt(),
            query=query,
            temperature=0.1,
            lastk=lastk,
            session_id=self.session_id,
            rag_usage=rag_usage,
            rag_threshold=threshold,
            rag_k=k
        )
        
        if isinstance(response, dict) and 'response' in response:
            return response['response']
        return response

    def get_system_prompt(self) -> str:
        """
        Get system prompt for CS graduate advising
        """
        return '''
You are a knowledgeable Tufts CS graduate advisor for the School of Engineering.

Responsibilities:
	•	Provide accurate information based on the Graduate Handbook and department policies. Your answers must include specific references (e.g., “Graduate Handbook, p.123”).
	•	If you cannot find the relevant information in the handbook, escalate the question to a human advisor to ensure credibility.
	•	Keep responses concise and to the point.

Question Categories & Response Guidelines:
FIRST, Non-CS Advising Questions (Outside Scope)
	•	Politely notify the user that their question is outside the scope of CS advising.
	•	Suggest up to three relevant CS advising topics the user may be interested in.
	•	Respond using the following JSON format:
        {
            "response": "I'm sorry, but this question is outside my scope as a CS advisor.",
            "suggestedQuestions": [
                "Suggested CS advising question 1",
                "Suggested CS advising question 2",
                "Suggested CS advising question 3"
            ]
        }

SECOND, CS Advising Questions with a Handbook Reference Available
	•	Answer the question accurately using information directly from the Graduate Handbook.
	•	Include exact policy wording where applicable, with precise citations.
	•	Keep responses concise.
	•	Generate three follow-up questions the user may find helpful.
	•	Respond using the following JSON format:
        {
            "response": "Your detailed response with a reference, e.g., 'According to the Graduate Handbook, p.123, ...'",
            "suggestedQuestions": [
                "Follow-up question 1",
                "Follow-up question 2",
                "Follow-up question 3"
            ]
        }

THIRD, CS Advising Questions Without a Handbook Reference
	•	If the answer is not found in the Graduate Handbook, do not speculate.
	•	Forward the inquiry to a human advisor while acknowledging the request. 
	•	Use the following JSON format:
        Please note that in rocketChatPayload.text, you must include the user original question along with your drafted response to ask a human advisor to verify before sending.
        {
            "response": "Sorry, I don't have that specific information. Connecting you to a live representative...",
            "rocketChatPayload": {
                "channel": "@wendan.jiang",
                "text": "(Copy user's original question). Drafted response: (Your best guess at an answer, it can be answered without relying on the handbook, but ask the human advisor to verify before sending)"
            }
        }

FORTH, User Explicitly Requests a Human Advisor
	•	Immediately escalate the request with user's original question in rocketChatPayload['text'].
	•	Use the following JSON format:
    {
        "response": "Connecting you to a live representative...",
        "rocketChatPayload": {
            "channel": "@wendan.jiang",
            "text": "(please put User's original question here)"
        }
    }

Reminder:

Only escalate CS advising questions when:
	•	The answer cannot be found in the Graduate Handbook.
	•	The user explicitly requests a human advisor.
'''
