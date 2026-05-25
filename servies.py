import json
import re
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from database import get_user_settings

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Cleans the output text of the LLM and parses it into a JSON dict."""
    cleaned = text.strip()
    
    # Remove markdown code block fences if present (e.g. ```json ... ```)
    if cleaned.startswith("```"):
        match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
            
    # Try direct parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # If it fails, attempt to locate the first outer JSON object bounds
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(cleaned[start_idx:end_idx+1])
            except json.JSONDecodeError:
                pass
        raise ValueError(
            "The model did not return a valid JSON object. "
            f"Raw response was: \n{text}"
        )

def get_llm(provider: str, model_name: str, api_key: str):
    """Initializes and returns the LangChain Chat Model based on selected provider."""
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model_name,
                temperature=0.0
            )
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOllama as CommunityChatOllama
                return CommunityChatOllama(
                    model=model_name,
                    base_url="http://localhost:11434",
                    temperature=0.0
                )
            except ImportError:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model_name,
                    base_url="http://localhost:11434/v1",
                    api_key="ollama",
                    temperature=0.0
                )

    if not api_key:
        raise ValueError(f"API Key for provider '{provider}' is missing. Please set it in Settings.")
        
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=0.0
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            api_key=api_key,
            temperature=0.0
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.0
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def extract_document_details(
    document_text: str,
    prompt_template: str,
    user_settings: Dict[str, Any]
) -> Dict[str, Any]:
    """Runs LangChain to extract JSON structured details from document_text using prompt_template."""
    import config
    
    if config.is_ollama_enabled():
        provider = "ollama"
        model_name = "gpt-oss:120b-cloud"
        api_key = "ollama"
    else:
        provider = user_settings.get("selected_provider", "openai")
        model_name = user_settings.get("selected_model")
        
        # Retrieve the appropriate key from settings
        key_mapping = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "gemini": "gemini_api_key"
        }
        api_key_field = key_mapping.get(provider)
        api_key = user_settings.get(api_key_field) if api_key_field else None
        
        if not api_key:
            raise ValueError(f"No API key configured for {provider.upper()}. Please set it in Settings.")
            
        # Standardize model names if they are empty
        if not model_name:
            default_models = {
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3-5-sonnet-20240620",
                "gemini": "gemini-1.5-flash"
            }
            model_name = default_models.get(provider, "")

    # Initialize the LLM
    llm = get_llm(provider, model_name, api_key)

    # Set up prompt template
    system_message = (
        "You are an expert document extraction system. "
        "Your task is to analyze the document text and extract details as instructed by the user.\n\n"
        "CRITICAL REQUIREMENT: You MUST output your response as a single, valid JSON object representing the extracted fields. "
        "Do not include any chat preamble, markdown code blocks (like ```json), or explanations outside of the JSON. "
        "Only return the raw JSON object string."
    )
    
    human_message = (
        "EXTRACTION INSTRUCTIONS:\n"
        "{instructions}\n\n"
        "DOCUMENT CONTENT:\n"
        "\"\"\"\n"
        "{content}\n"
        "\"\"\""
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message)
    ])
    
    # Run Chain
    chain = prompt | llm
    
    # Truncate content to avoid excessive prompt lengths in POC (approx 60k characters)
    max_chars = 60000
    truncated_content = document_text[:max_chars]
    if len(document_text) > max_chars:
        truncated_content += "\n[Content truncated due to size limits]"
        
    response = chain.invoke({
        "instructions": prompt_template,
        "content": truncated_content
    })
    
    raw_response = response.content
    if not isinstance(raw_response, str):
        # Handle cases where response might be a list or other types depending on model
        raw_response = str(raw_response)
        
    # Clean and parse JSON
    return clean_and_parse_json(raw_response)
