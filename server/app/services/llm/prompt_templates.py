from typing import Dict, Any, List, Optional
from string import Template

class PromptTemplates:
    """Templates for LLM prompts with Chain-of-Thought reasoning"""
    
    @staticmethod
    def survey_system_prompt(survey_info: Dict[str, Any]) -> str:
        """Generate system prompt for survey conversations"""
        template = Template("""
You are an AI phone assistant conducting a survey on behalf of ${company_name}. Your goal is to collect feedback from customers in a professional, friendly, and conversational manner.

Survey Information:
- Title: ${survey_title}
- Purpose: ${survey_purpose}

Guidelines:
1. Be polite and respectful at all times.
2. Speak naturally as if you're having a conversation, not reading a script.
3. Listen carefully to the customer's responses and adapt accordingly.
4. If a customer asks a question outside the survey, try to answer using the knowledge base if possible.
5. If you don't know an answer, be honest about it.
6. Do not rush the customer - give them time to respond.
7. Thank the customer for their participation at the end.

Use Chain-of-Thought reasoning to:
- Interpret ambiguous or complex responses
- Determine appropriate follow-up questions
- Classify and categorize customer sentiments
- Navigate conversation paths based on the survey flow

Knowledge Base Information:
${knowledge_base_info}

Survey Flow:
${survey_flow}
""")
        
        return template.substitute(
            company_name=survey_info.get("company_name", "Our Company"),
            survey_title=survey_info.get("title", "Customer Feedback Survey"),
            survey_purpose=survey_info.get("purpose", "gather valuable feedback about our products and services"),
            knowledge_base_info=survey_info.get("knowledge_base_info", "No specific knowledge base information provided."),
            survey_flow=survey_info.get("survey_flow", "No specific survey flow provided.")
        )
    
    @staticmethod
    def survey_question_prompt(
        question: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a prompt for asking a survey question with CoT reasoning"""
        template = Template("""
Question to ask: "${question_text}"
Question Type: ${question_type}
Question ID: ${question_id}

Conversation Context:
${conversation_history}

${knowledge_section}

Your task is to:
1. First, review the conversation history to understand the context.
2. Use Chain-of-Thought reasoning to plan how to ask this question naturally.
3. Consider any relevant knowledge from the retrieved information.
4. Formulate a conversational way to ask the question that flows from the previous exchange.
5. Be prepared to clarify if the customer seems confused.

Chain-of-Thought Reasoning:
""")
        
        # Format conversation history
        history_text = ""
        for entry in conversation_history[-5:]:  # Only include the last 5 exchanges
            speaker = "AI" if entry.get("is_ai", False) else "Customer"
            history_text += f"{speaker}: {entry.get('text', '')}\n"
        
        # Format knowledge section if provided
        knowledge_text = ""
        if retrieved_knowledge:
            knowledge_text = "Retrieved Knowledge:\n"
            for item in retrieved_knowledge:
                knowledge_text += f"- {item.get('text', '')[:200]}...\n"
        
        knowledge_section = knowledge_text if knowledge_text else "No relevant knowledge retrieved for this question."
        
        return template.substitute(
            question_text=question.get("text", ""),
            question_type=question.get("type", "open_ended"),
            question_id=question.get("id", "unknown"),
            conversation_history=history_text,
            knowledge_section=knowledge_section
        )
    
    @staticmethod
    def response_analysis_prompt(
        question: Dict[str, Any],
        customer_response: str,
        conversation_history: List[Dict[str, Any]],
        retrieved_knowledge: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a prompt for analyzing customer responses with CoT reasoning"""
        template = Template("""
Customer's response to question "${question_text}": "${customer_response}"
Question Type: ${question_type}
Question ID: ${question_id}

Conversation Context:
${conversation_history}

${knowledge_section}

Your task is to:
1. Use Chain-of-Thought reasoning to analyze the customer's response.
2. Determine if the response directly answers the question.
3. Extract key information and sentiment from the response.
4. Decide whether follow-up is needed for clarification.
5. Identify any new topics or concerns the customer has introduced.
6. Classify the response according to relevant categories.

Chain-of-Thought Reasoning:
""")
        
        # Format conversation history
        history_text = ""
        for entry in conversation_history[-5:]:  # Only include the last 5 exchanges
            speaker = "AI" if entry.get("is_ai", False) else "Customer"
            history_text += f"{speaker}: {entry.get('text', '')}\n"
        
        # Format knowledge section if provided
        knowledge_text = ""
        if retrieved_knowledge:
            knowledge_text = "Retrieved Knowledge:\n"
            for item in retrieved_knowledge:
                knowledge_text += f"- {item.get('text', '')[:200]}...\n"
        
        knowledge_section = knowledge_text if knowledge_text else "No relevant knowledge retrieved for this analysis."
        
        return template.substitute(
            question_text=question.get("text", ""),
            customer_response=customer_response,
            question_type=question.get("type", "open_ended"),
            question_id=question.get("id", "unknown"),
            conversation_history=history_text,
            knowledge_section=knowledge_section
        )