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
        self.inference_prompt = '''
You are determining RAG parameters for a CS graduate student advising chatbot at Tufts School of Engineering.

Consider the following patterns when suggesting RAG parameters:

High Precision Needed (higher threshold ~0.8, lower k ~3):
- Questions about academic standing and dismissal policies
- Questions about thesis/dissertation defense procedures
- Specific information about leave policies (personal, medical, parental)
- Registration deadlines and continuous enrollment requirements
- Fifth-Year Master's double-counting policies

Balanced Context (medium threshold ~0.7, medium k ~5):
- Questions about transfer credit and extension of degree time
- Co-op program eligibility and procedures
- Academic integrity policies
- English language proficiency requirements
- Degree-only status and enrollment status

Broader Context (lower threshold ~0.6, higher k ~7):
- Campus resources (Health Services, Counseling, StAAR Center)
- Graduate Student Council information
- Professional development opportunities
- Shuttle services and transportation
- Campus facilities and libraries

Return only a JSON string in this exact format:
{
    "rag_usage": <true/false>,
    "rag_threshold": <0.0-1.0>,
    "rag_k": <1-10>,
    "reasoning": "<brief explanation of why these parameters were chosen>"
}  
'''

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
        self.parameter_inference = RAGParameterInference()

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
You will need to answer CS advising questions in following 5 categories:

For categories 1, 3, 4, and 5: Draw from your general knowledge but note when information isn't handbook-based
For category 2: Use only handbook information


1, Non-CS Advising Questions (Outside Scope)
    •   Questions that asks non-cs advising topics, such as "What is the weather today."
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

2, POLICY-RELATED CS Advising Questions with a Handbook Reference Available
    •   Questions related with a specific policy/requirement (i.e., graduation graduation, international student absence policy) must guarantee the correctness.
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

3, POLICY-RELATED CS Advising Questions WITHOUT handbook reference available.
    •   Questions related with a specific policy/requirement (i.e., graduation graduation, international student absence policy) must guarantee the correctness.
	•	If you cannot find an answer from the handbook, you MUST try your best to draft an answer with whatever resource you have.
	•	Keep responses concise.
	•   You MUST forward both the original question and your answer to a human advisor for verification before sending to the student.
    •   Use the following JSON format:
        {
            "response": "Sorry, I don't have that specific information. Connecting you to a live representative...",
            "rocketChatPayload": {
                "originalQuestion": "(Copy user's original question)",
                "llmAnswer": "(put your drafted answer here)"
            }
        }

4, NON-POLICY-RELATED CS Advising Questions Without a Handbook Reference
    •   If the answer isn't in the Graduate Handbook but relates to general CS coursework, workload, or similar topics:
    •   Provide your best answer based on general knowledge
    •   In your response, notify the user: "This information isn't referenced in the handbook. For further assistance, you can connect with a live representative."
	•	Generate three follow-up questions the user may find helpful.
    •   Use the following JSON format:
            {
                "response": "Your response",
                "suggestedQuestions": [
                    "Follow-up question 1",
                    "Follow-up question 2",
                    "Follow-up question 3"
                ]
            }

5, User Explicitly Requests a Human Advisor
	•	Immediately escalate the request with user's original question in rocketChatPayload['text'].
	•	Use the following JSON format:
        {
            "response": "Connecting you to a live representative...",
            "rocketChatPayload": {
                "originalQuestion": "(please put User's original question here)"
            }
        }

Reminder:
	Try your best to avoid involving a human, unless the user explicitly requests it or the question falls into category 3.
'''
