import json
import os
import re
import asyncio
import backoff
from typing import Dict, Any, List, Optional, Union

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger("services.llm.cot_engine")
settings = get_settings()

class CoTEngine:
    """
    Chain-of-Thought Engine for working with LLMs to generate step-by-step reasoning
    and enhanced responses for the phone feedback system.
    """
    
    def __init__(self):
        """Initialize the CoT engine with appropriate LLM provider based on settings"""
        self.llm_provider = settings.LLM_PROVIDER.lower()
        
        if self.llm_provider == "openai":
            self._initialize_openai()
        elif self.llm_provider == "anthropic":
            self._initialize_anthropic()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        import openai
        
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.Client()
        self.model = "gpt-4-turbo"  # Default model
    
    def _initialize_anthropic(self):
        """Initialize Anthropic client"""
        import anthropic
        
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-opus-20240229"  # Default model
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        giveup=lambda e: "invalid" in str(e).lower()
    )
    async def generate(self, prompt: str, system_message: Optional[str] = None) -> str:
        """
        Generate a response without explicit CoT reasoning
        
        Args:
            prompt: The prompt to send to the LLM
            system_message: Optional system message to set context
            
        Returns:
            str: Generated response
        """
        try:
            if self.llm_provider == "openai":
                messages = []
                
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                
                messages.append({"role": "user", "content": prompt})
                
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    temperature=0.7
                )
                
                return response.choices[0].message.content
            
            elif self.llm_provider == "anthropic":
                message_content = []
                
                if system_message:
                    message = self.client.messages.create(
                        model=self.model,
                        system=system_message,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=1024
                    )
                else:
                    message = self.client.messages.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=1024
                    )
                
                return message.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}", exc_info=True)
            raise
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        giveup=lambda e: "invalid" in str(e).lower()
    )
    async def generate_with_reasoning(self, prompt: str, system_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response with explicit Chain-of-Thought reasoning
        
        Args:
            prompt: The prompt to send to the LLM
            system_message: Optional system message to set context
            
        Returns:
            Dict: Contains 'reasoning' (the step-by-step thought process) and 'output' (the final answer)
        """
        try:
            # Modify prompt to explicitly request CoT reasoning
            cot_prompt = f"""
{prompt}

Step through your reasoning in detail before providing your final answer. 
Think step-by-step through this problem:
1. First, analyze the context and question carefully
2. Break down the problem into parts if needed
3. Explore different perspectives or approaches
4. Draw a conclusion based on your reasoning

After your reasoning, provide your final output in a format that can be directly used, labeled as FINAL OUTPUT:
"""
            
            if self.llm_provider == "openai":
                messages = []
                
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                
                messages.append({"role": "user", "content": cot_prompt})
                
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    temperature=0.7
                )
                
                full_response = response.choices[0].message.content
            
            elif self.llm_provider == "anthropic":
                if system_message:
                    message = self.client.messages.create(
                        model=self.model,
                        system=system_message,
                        messages=[{"role": "user", "content": cot_prompt}],
                        temperature=0.7,
                        max_tokens=2048
                    )
                else:
                    message = self.client.messages.create(
                        model=self.model,
                        messages=[{"role": "user", "content": cot_prompt}],
                        temperature=0.7,
                        max_tokens=2048
                    )
                
                full_response = message.content[0].text
            
            # Split reasoning from final output
            parts = re.split(r"FINAL OUTPUT:?", full_response, flags=re.IGNORECASE)
            
            if len(parts) >= 2:
                reasoning = parts[0].strip()
                output = parts[1].strip()
            else:
                # If the model didn't follow the format correctly
                reasoning = full_response
                output = full_response
            
            return {
                "reasoning": reasoning,
                "output": output
            }
            
        except Exception as e:
            logger.error(f"Error generating CoT response: {str(e)}", exc_info=True)
            raise
    
    async def generate_structured_output(
        self, 
        text: str, 
        schema: Union[str, Dict[str, Any]],
        system_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured output (JSON) with improved error handling
        
        Args:
            text: The text to analyze
            schema: JSON schema as string or dict defining the expected output structure
            system_message: Optional system message to set context
            
        Returns:
            Dict: Structured output according to the provided schema
        """
        try:
            # Handle both string and dict schemas
            if isinstance(schema, dict):
                schema_str = json.dumps(schema.get("properties", {}), indent=2)
            else:
                schema_str = str(schema)
            
            # Simplified prompt for faster response
            prompt = f"""
You must respond with ONLY a valid JSON object that matches this exact format:

{schema_str}

Analyze this text: "{text[:100]}"

Response must be valid JSON only - no explanations, no code blocks, no extra text.
Start with {{ and end with }}.
"""
            
            # Generate response with shorter content for speed
            if self.llm_provider == "openai":
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,  # Reduced for speed
                    temperature=0.1  # Lower for consistency
                )
                raw_output = response.choices[0].message.content.strip()
            else:  # anthropic
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                raw_output = response.content[0].text.strip()
            
            logger.debug(f"Raw LLM output: {raw_output}")
            
            # Clean and parse the output
            cleaned_output = self._clean_output(raw_output)
            
            try:
                result = json.loads(cleaned_output)
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {e}, trying fallback parsing")
                
                # Try to fix common JSON issues
                fixed_output = self._fix_common_json_issues(cleaned_output)
                try:
                    result = json.loads(fixed_output)
                    return result
                except json.JSONDecodeError:
                    logger.error(f"Could not parse JSON even after fixes: {fixed_output}")
                    
                    # Use fallback response
                    fallback = self._get_fallback_response(schema, text)
                    logger.info(f"Using fallback response: {fallback}")
                    return fallback
            
        except Exception as e:
            logger.error(f"Error in generate_structured_output: {e}")
            return self._get_fallback_response(schema, text)
    
    def _clean_output(self, output):
        """Clean the output by removing code blocks and extra text"""
        # Remove code blocks
        output = re.sub(r'```json\s*', '', output)
        output = re.sub(r'```\s*', '', output)
        
        # Try to find JSON object boundaries
        # Look for the first { and last }
        start_idx = output.find('{')
        end_idx = output.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            output = output[start_idx:end_idx + 1]
        
        return output.strip()
    
    def _fix_common_json_issues(self, json_str):
        """Fix common JSON formatting issues"""
        try:
            # If JSON doesn't start with {, try to add it
            if not json_str.strip().startswith('{'):
                # Look for content that looks like JSON properties
                if ':' in json_str and ('"' in json_str or "'" in json_str):
                    json_str = '{' + json_str
            
            # If JSON doesn't end with }, try to add it
            if not json_str.strip().endswith('}'):
                json_str = json_str + '}'
            
            # Fix single quotes to double quotes
            json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
            json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
            
            # Remove trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            return json_str
        except Exception:
            return json_str
    
    def _get_fallback_response(self, schema, text):
        """Generate a fallback response when JSON parsing fails"""
        try:
            # Convert schema to string if it's not already
            schema_str = str(schema) if not isinstance(schema, str) else schema
            
            # Parse the schema to understand expected structure
            if '"sentiment":' in schema_str and '"score":' in schema_str:
                # This is a sentiment analysis schema
                return {
                    "sentiment": "neutral",
                    "score": 0.0,
                    "confidence": 0.5,
                    "themes": [],
                    "nuances": "Could not analyze due to API error"
                }
            else:
                # Generic fallback
                return {
                    "result": "error",
                    "message": "Could not parse response",
                    "input": text[:50] if text else ""
                }
        except Exception:
            return {"error": "Fallback generation failed"}