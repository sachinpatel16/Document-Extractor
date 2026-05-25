from typing import Dict, Any, List, Optional
from supabase import create_client, Client
import config

# Global Supabase client instance
_supabase: Optional[Client] = None

def get_supabase_client() -> Client:
    """Initializes and returns the Supabase client."""
    global _supabase
    if _supabase is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be set in environment variables or Streamlit secrets.")
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabase

# --- PROFILE CRUD ---

def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Gets the profile of a user by user_id."""
    try:
        client = get_supabase_client()
        response = client.table("profiles").select("*").eq("id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None

def update_profile(user_id: str, username: str, full_name: str) -> bool:
    """Updates profile details for a user."""
    try:
        client = get_supabase_client()
        data = {
            "id": user_id,
            "username": username,
            "full_name": full_name
        }
        # Upsert profiles (handles case where handle_new_user trigger hasn't fired or failed)
        client.table("profiles").upsert(data).execute()
        return True
    except Exception as e:
        print(f"Error updating profile: {e}")
        return False

# --- SETTINGS CRUD ---

def get_user_settings(user_id: str) -> Dict[str, Any]:
    """Retrieves user settings including API keys and selected models. 
    Returns default settings if none exist yet."""
    default_settings = {
        "user_id": user_id,
        "openai_api_key": "",
        "anthropic_api_key": "",
        "gemini_api_key": "",
        "selected_provider": "openai",
        "selected_model": "gpt-4o-mini"
    }
    try:
        client = get_supabase_client()
        response = client.table("user_settings").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            # Merge database values over defaults to handle any missing keys
            return {**default_settings, **response.data[0]}
        return default_settings
    except Exception as e:
        print(f"Error fetching user settings: {e}")
        return default_settings

def save_user_settings(
    user_id: str,
    openai_key: str,
    anthropic_key: str,
    gemini_key: str,
    provider: str,
    model: str
) -> bool:
    """Saves or updates user settings."""
    try:
        client = get_supabase_client()
        data = {
            "user_id": user_id,
            "openai_api_key": openai_key,
            "anthropic_api_key": anthropic_key,
            "gemini_api_key": gemini_key,
            "selected_provider": provider,
            "selected_model": model
        }
        client.table("user_settings").upsert(data).execute()
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

# --- DYNAMIC PROMPTS CRUD ---

def get_prompts(user_id: str) -> List[Dict[str, Any]]:
    """Gets all prompts created by a user."""
    try:
        client = get_supabase_client()
        response = client.table("prompts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching prompts: {e}")
        return []

def create_prompt(user_id: str, name: str, prompt_template: str) -> Optional[Dict[str, Any]]:
    """Creates a new dynamic prompt template."""
    try:
        client = get_supabase_client()
        data = {
            "user_id": user_id,
            "name": name,
            "prompt_template": prompt_template
        }
        response = client.table("prompts").insert(data).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error creating prompt: {e}")
        return None

def update_prompt(prompt_id: str, user_id: str, name: str, prompt_template: str) -> bool:
    """Updates an existing dynamic prompt template."""
    try:
        client = get_supabase_client()
        data = {
            "name": name,
            "prompt_template": prompt_template
        }
        client.table("prompts").update(data).eq("id", prompt_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error updating prompt: {e}")
        return False

def delete_prompt(prompt_id: str, user_id: str) -> bool:
    """Deletes a dynamic prompt template."""
    try:
        client = get_supabase_client()
        client.table("prompts").delete().eq("id", prompt_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting prompt: {e}")
        return False

# --- EXTRACTED DOCUMENTS CRUD ---

def get_extracted_documents(user_id: str) -> List[Dict[str, Any]]:
    """Gets all document extraction histories for a user."""
    try:
        client = get_supabase_client()
        # Fetching documents with a left join to include prompt names
        response = client.table("extracted_documents").select(
            "id, filename, prompt_id, extracted_data, raw_content_summary, created_at, prompts(name)"
        ).eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching extraction history: {e}")
        return []

def create_extracted_document(
    user_id: str,
    filename: str,
    prompt_id: Optional[str],
    extracted_data: Dict[str, Any],
    raw_content_summary: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Saves a document extraction record."""
    try:
        client = get_supabase_client()
        data = {
            "user_id": user_id,
            "filename": filename,
            "prompt_id": prompt_id,
            "extracted_data": extracted_data,
            "raw_content_summary": raw_content_summary
        }
        response = client.table("extracted_documents").insert(data).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error saving document extraction: {e}")
        return None

def delete_extracted_document(doc_id: str, user_id: str) -> bool:
    """Deletes a document extraction record."""
    try:
        client = get_supabase_client()
        client.table("extracted_documents").delete().eq("id", doc_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting extraction record: {e}")
        return False
