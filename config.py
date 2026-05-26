import os
import streamlit as st
from dotenv import load_dotenv

# Load env variables from a local .env file if it exists
load_dotenv()

# Helper to get configuration values safely from environment variables or Streamlit secrets
def get_env_var(key: str, default: str = "") -> str:
    # 1. Try streamlit secrets
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    
    # 2. Try OS environment variables (or .env file)
    return os.getenv(key, default)

SUPABASE_URL = get_env_var("SUPABASE_URL")
SUPABASE_KEY = get_env_var("SUPABASE_KEY")

# Basic check to warn in Streamlit UI if config is missing
def is_config_valid() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)

def is_ollama_enabled() -> bool:
    val = get_env_var("ollama").strip().lower()
    return val in ["true", "ture", "1", "yes"]

def show_errors() -> bool:
    val = get_env_var("SHOW_ERRORS", "false").strip().lower()
    return val in ["true", "ture", "1", "yes"]
