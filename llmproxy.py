import os
import json
import requests
from typing import Tuple

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
    def __init__(self, pdf_path='soe-grad-handbook.pdf'):
        self.session_id = 'Tufts-CS-Advisor-wendanj-0219'
        self.parameter_inference = RAGParameterInference()  # Fixed to use correct class
        
        print("\n📚 Loading handbook...")
        try:
            upload_response = pdf_upload(
                path=pdf_path,
                session_id=self.session_id,
                strategy='smart'
            )
            print("✅ Handbook loaded successfully")
        except Exception as e:
            print(f"❌ Error loading handbook: {str(e)}")

    def get_response(self, query: str) -> str:
        """
        Get response using inferred RAG parameters
        """
        use_rag, threshold, k = self.parameter_inference.infer_rag_params(query)
        print(use_rag, threshold, k)
        
        response = generate(
            model='4o-mini',
            system=self.get_system_prompt(),
            query=query,
            temperature=0.1,
            lastk=0,
            session_id=self.session_id,
            rag_usage=use_rag,
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
        return '''You are a knowledgeable Tufts CS graduate advisor for the School of Engineering. 
                 Provide accurate information based on the available context from the graduate handbook 
                 and department policies. When specific information isn't available in the context, 
                 be clear about what might need verification with the department. Consider the graduate 
                 student perspective and provide guidance that's relevant to their academic journey.'''
    