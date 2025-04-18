from llmproxy import generate
from utils.uploads import handbook_upload
from prompt import get_system_prompt
import time

class TuftsCSAdvisor:
    def __init__(self, user_profile):
        self.user_profile = user_profile
        self.user_id = user_profile["user_id"]
        self.last_k = user_profile["last_k"]
        if user_profile["last_k"] == 0:
            handbook_upload(self.user_id)
            time.sleep(2)

    def get_faq_response(self, faq_formatted, query: str):
        print(f"user {self.user_id} has lastk {self.last_k}")

        rag_response = generate(
            model='4o-mini',
            system=get_system_prompt(self.user_profile),
            query=query,
            temperature=0.1,
            lastk=self.last_k,
            session_id='cs-advising-handbooks-v5-' + self.user_id,      # prev v5
            rag_usage=True,
            rag_threshold=0.5,  # Lower threshold
            rag_k=5  # Retrieve more documents
        )

        print("\nResponse:", rag_response.get('response') if isinstance(rag_response, dict) else rag_response)
        print("\nRAG Context:", rag_response.get('rag_context') if isinstance(rag_response, dict) else "No context available")

        if isinstance(rag_response, dict) and 'response' in rag_response:
            return rag_response['response']
        
        return rag_response