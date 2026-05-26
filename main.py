import streamlit as st
import config
import database
import auth
import utiles
import servies
import time
import json

# Page Config
st.set_page_config(
    page_title="DocuExtract POC",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Set light theme
st.markdown("""
<style>
.stApp {
    background-color: #fafafa;
}
[data-testid="stAppViewBlockContainer"] {
    background-color: #fafafa;
    padding-top: 0 !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] {
    background-color: #f1f5f9;
}
[data-testid="stSidebarContent"] {
    background-color: #f1f5f9;
}
[data-testid="stMainBlockContainer"] {
    background-color: #fafafa;
    padding-top: 0 !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stVerticalBlock"] {
    background-color: #fafafa;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stBlock"] {
    background-color: #fafafa;
    border: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

# Inject custom CSS for light theme
# st.markdown(utiles.get_custom_css(), unsafe_allow_html=True)

# 1. Configuration Validation
if not config.is_config_valid():
    if config.show_errors():
        st.error("Configuration Required")
    st.warning("Supabase credentials are not configured in your environment variables or Streamlit secrets.")
    st.info("Create a .env file in the project root with:\nSUPABASE_URL=your-supabase-url\nSUPABASE_KEY=your-supabase-key")
    st.info("Please restart the server after creating the file.")
    st.stop()

# Initialize Auth State
auth.init_auth_state()

# 2. Routing Logic
if st.session_state["user"] is None:
    auth.render_auth_ui()
else:
    user = st.session_state["user"]
    profile = st.session_state["profile"]
    
    # Top Navigation Bar
    st.markdown("""
    <style>
    .navbar-container {
        background: transparent;
        border: none;
        border-radius: 0;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        margin-top: 0;
        box-shadow: none;
    }
    [data-testid="stCode"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        max-height: 500px !important;
        overflow-y: auto !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="navbar-container">', unsafe_allow_html=True)
    col_logo, col_nav, col_user = st.columns([2, 5, 2])
    
    with col_logo:
        st.markdown("### DocuExtract")
    
    with col_nav:
        page = st.radio(
            "Navigation",
            ["Document Extractor", "Manage Prompts", "API Settings", "Profile"],
            index=0,
            horizontal=True,
            label_visibility="collapsed"
        )
    
    with col_user:
        if profile and profile.get('full_name'):
            st.caption(profile.get('full_name', 'User'))
        if st.button("Log Out", use_container_width=True):
            auth.sign_out()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- PAGE: DOCUMENT EXTRACTOR ---
    if page == "Document Extractor":
        # Fetch user's settings and prompts
        settings = database.get_user_settings(user.id)
        prompts = database.get_prompts(user.id)
        
        if not prompts:
            st.warning("You don't have any prompt templates yet. Please head over to the **Manage Prompts** tab to create one.")
            st.stop()
            
        # Two-column layout: Table on left, Results on right
        col_left, col_right = st.columns([1, 1], gap="large")
        
        # Initialize session state for selected document
        if "selected_doc_id" not in st.session_state:
            st.session_state["selected_doc_id"] = None
        
        with col_left:
            st.markdown("### Auto Extract")
            
            # Select prompt
            prompt_options = {p["id"]: p for p in prompts}
            auto_prompt_id = st.selectbox(
                "Choose Prompt",
                options=list(prompt_options.keys()),
                format_func=lambda x: prompt_options[x]["name"],
                key="auto_prompt_select"
            )
            
            auto_prompt = prompt_options[auto_prompt_id]
            
            # File Uploader for auto extract
            auto_uploaded_file = st.file_uploader(
                "Upload Document",
                type=["pdf", "docx", "txt"],
                key="auto_file_uploader"
            )
            
            # Auto-extract when file is uploaded
            if auto_uploaded_file is not None:
                st.success(f"File uploaded: {auto_uploaded_file.name}")
                
                # Extract text
                try:
                    with st.spinner("Reading document..."):
                        auto_extracted_text = utiles.extract_text(auto_uploaded_file)
                    
                    # Determine provider and model
                    if config.is_ollama_enabled():
                        auto_provider = "ollama"
                        auto_model = "gpt-oss:120b-cloud"
                    else:
                        auto_provider = settings.get("selected_provider", "openai")
                        auto_model = settings.get("selected_model", "gpt-4o-mini")
                    
                    # Auto-trigger extraction
                    with st.spinner(f"Auto-analyzing with {auto_provider.upper()} ({auto_model})..."):
                        try:
                            auto_result = servies.extract_document_details(
                                document_text=auto_extracted_text,
                                prompt_template=auto_prompt["prompt_template"],
                                user_settings=settings
                            )
                            
                            st.session_state["auto_extracted_data"] = auto_result
                            st.success("Analysis completed!")
                            
                        except Exception as e:
                            if config.show_errors():
                                st.error(f"Analysis failed: {e}")
                            st.session_state["auto_extracted_data"] = None
                            
                except Exception as e:
                    if config.show_errors():
                        st.error(f"Error reading file: {e}")
                    st.session_state["auto_extracted_data"] = None
        
        with col_right:
            st.markdown("### Results")
            
            # Show auto-extracted data
            if "auto_extracted_data" in st.session_state and st.session_state["auto_extracted_data"]:
                json_str = json.dumps(st.session_state["auto_extracted_data"], indent=2)
                st.code(json_str, language="json")
                if st.button("Clear Results", key="clear_auto_res", use_container_width=True):
                    st.session_state["auto_extracted_data"] = None
                    st.rerun()
            else:
                st.info("Upload a document to view results.")

    # --- PAGE: MANAGE PROMPTS ---
    elif page == "Manage Prompts":
        # Use tabs to organize content without scrolling
        tab_create, tab_list = st.tabs(["Create New Prompt", "Your Templates"])
        
        with tab_create:
            # Form to add new prompt
            st.subheader("Create New Prompt Template")
            with st.form("new_prompt_form"):
                p_name = st.text_input("Template Name", placeholder="e.g. Invoice Extractor, Resume Parser")
                p_template = st.text_area(
                    "Extraction Instructions (Template)", 
                    placeholder="e.g. Extract the invoice number, date, vendor name, line items, tax, and total amount."
                )
                submit_prompt = st.form_submit_button("Save Prompt Template", use_container_width=True)
                
                if submit_prompt:
                    if not p_name or not p_template:
                        st.warning("Please fill in both name and instructions.")
                    else:
                        with st.spinner("Saving template..."):
                            if database.create_prompt(user.id, p_name, p_template):
                                st.success(f"Prompt '{p_name}' created successfully!")
                                time.sleep(0.5)
                                st.rerun()
        
        with tab_list:
            st.subheader("Your Custom Templates")
            prompts = database.get_prompts(user.id)
            
            if not prompts:
                st.info("You haven't created any custom prompts yet.")
            else:
                # Create table data
                import pandas as pd
                table_data = []
                for p in prompts:
                    table_data.append({
                        "Name": p['name'],
                        "Created": p['created_at'][:10],
                        "Instructions": p['prompt_template'][:100] + "..." if len(p['prompt_template']) > 100 else p['prompt_template'],
                        "ID": p['id']
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Edit and Delete actions below table
                st.markdown("---")
                st.subheader("Edit or Delete Template")
                selected_prompt_id = st.selectbox(
                    "Select Template to Edit/Delete",
                    options=[p['id'] for p in prompts],
                    format_func=lambda x: next(p['name'] for p in prompts if p['id'] == x)
                )
                
                selected_prompt = next(p for p in prompts if p['id'] == selected_prompt_id)
                
                col_edit, col_del = st.columns(2)
                with col_edit:
                    with st.popover("Edit", use_container_width=True):
                        with st.form(f"edit_form_{selected_prompt_id}"):
                            edit_name = st.text_input("Template Name", value=selected_prompt["name"])
                            edit_template = st.text_area("Instructions (Template)", value=selected_prompt["prompt_template"], height=150)
                            save_edit = st.form_submit_button("Save Changes", use_container_width=True)
                            if save_edit:
                                if database.update_prompt(selected_prompt_id, user.id, edit_name, edit_template):
                                    st.success("Prompt updated!")
                                    time.sleep(0.5)
                                    st.rerun()
                with col_del:
                    if st.button("Delete", key=f"del_p_{selected_prompt_id}", use_container_width=True, help="Delete Prompt"):
                        if database.delete_prompt(selected_prompt_id, user.id):
                            st.toast("Prompt template deleted.")
                            time.sleep(0.5)
                            st.rerun()

    # --- PAGE: API SETTINGS ---
    elif page == "API Settings":
        if config.is_ollama_enabled():
            st.info("Ollama Override Active: Local execution is enabled in .env with model gpt-oss:120b-cloud. Changes to the settings below will not affect extraction until Ollama is disabled in .env.")
            
        # Load user's current settings
        settings = database.get_user_settings(user.id)
        
        # Use tabs to organize content without scrolling
        tab_status, tab_config = st.tabs(["API Key Status", "Configure Settings"])
        
        with tab_status:
            st.subheader("API Keys Status")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                has_openai = bool(settings.get("openai_api_key"))
                st.metric("OpenAI", "Configured" if has_openai else "Not Configured")
            with col_s2:
                has_anthropic = bool(settings.get("anthropic_api_key"))
                st.metric("Anthropic", "Configured" if has_anthropic else "Not Configured")
            with col_s3:
                has_gemini = bool(settings.get("gemini_api_key"))
                st.metric("Gemini", "Configured" if has_gemini else "Not Configured")
        
        with tab_config:
            # Form to configure settings
            with st.form("api_settings_form"):
                col_conf_model, col_conf_keys = st.columns([1, 1], gap="large")
                
                with col_conf_model:
                    st.subheader("LLM Preferences")
                    st.caption("Select your active LLM provider and default model.")
                    
                    provider_models = {
                        "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
                        "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
                        "gemini": ["gemini-1.5-flash", "gemini-1.5-pro"]
                    }
                    
                    # Selected Provider dropdown
                    current_provider = settings.get("selected_provider", "openai")
                    provider_index = 0
                    if current_provider in ["openai", "anthropic", "gemini"]:
                        provider_index = ["openai", "anthropic", "gemini"].index(current_provider)
                        
                    selected_provider = st.selectbox(
                        "Default Provider",
                        ["openai", "anthropic", "gemini"],
                        index=provider_index
                    )
                    
                    # Dynamically fetch model list
                    available_models = provider_models.get(selected_provider, [])
                    
                    current_model = settings.get("selected_model", "")
                    model_index = 0
                    if current_model in available_models:
                        model_index = available_models.index(current_model)
                        
                    selected_model = st.selectbox(
                        "Default Model",
                        available_models,
                        index=model_index
                    )
                    
                with col_conf_keys:
                    st.subheader("Set API Keys")
                    st.caption("Provide or update keys for the models you want to use. Keys are securely stored.")
                    
                    openai_key = st.text_input(
                        "OpenAI API Key",
                        value=settings.get("openai_api_key", ""),
                        type="password",
                        placeholder="sk-..."
                    )
                    
                    anthropic_key = st.text_input(
                        "Anthropic API Key",
                        value=settings.get("anthropic_api_key", ""),
                        type="password",
                        placeholder="sk-ant-..."
                    )
                    
                    gemini_key = st.text_input(
                        "Gemini (Google) API Key",
                        value=settings.get("gemini_api_key", ""),
                        type="password",
                        placeholder="AIzaSy..."
                    )
                    
                submit_settings = st.form_submit_button("Save Configurations", use_container_width=True)
                
                if submit_settings:
                    with st.spinner("Saving API configurations..."):
                        success = database.save_user_settings(
                            user_id=user.id,
                            openai_key=openai_key,
                            anthropic_key=anthropic_key,
                            gemini_key=gemini_key,
                            provider=selected_provider,
                            model=selected_model
                        )
                        if success:
                            st.success("API keys and model configuration saved successfully!")
                            time.sleep(0.5)
                            st.rerun()

    # --- PAGE: PROFILE ---
    elif page == "Profile":
        # Load stats
        history = database.get_extracted_documents(user.id)
        prompts = database.get_prompts(user.id)
        settings = database.get_user_settings(user.id)
        
        total_docs = len(history)
        total_prompts = len(prompts)
        
        # Use tabs to organize content without scrolling
        tab_info, tab_edit = st.tabs(["Profile Info", "Edit Profile"])
        
        with tab_info:
            # Profile Card Header
            with st.container():
                col_avatar, col_info = st.columns([1, 3])
                with col_avatar:
                    # Initials for avatar
                    initials = ""
                    name_parts = profile.get('full_name', '').split() if profile else []
                    if name_parts:
                        initials = "".join([part[0].upper() for part in name_parts[:2]])
                    else:
                        initials = user.email[:2].upper()
                        
                    st.write(initials)
                with col_info:
                    st.write(f"**Name:** {profile.get('full_name', 'User') if profile else 'User'}")
                    st.write(f"**Username:** @{profile.get('username', 'user') if profile else 'user'}")
                    st.write(f"**Email:** {user.email}")
                    
            # Stats Grid
            st.subheader("Account Statistics")
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Extracted Docs", total_docs)
            with col_stat2:
                st.metric("Saved Templates", total_prompts)
            with col_stat3:
                st.metric("Default LLM", settings.get('selected_provider', 'openai').upper())
        
        with tab_edit:
            # Form to edit profile details
            st.subheader("Update Profile Details")
            with st.form("profile_form"):
                username = st.text_input("Username", value=profile.get("username", "") if profile else "")
                fullname = st.text_input("Full Name", value=profile.get("full_name", "") if profile else "")
                
                submit_profile = st.form_submit_button("Save Profile Changes", use_container_width=True)
                
                if submit_profile:
                    if not username or not fullname:
                        st.warning("All profile fields must be filled.")
                    else:
                        with st.spinner("Updating profile..."):
                            if database.update_profile(user.id, username, fullname):
                                # Reload profile in state
                                st.session_state["profile"] = database.get_profile(user.id)
                                st.success("Profile updated successfully!")
                                time.sleep(0.5)
                                st.rerun()
