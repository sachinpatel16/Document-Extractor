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
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global styles for premium look
st.markdown(utiles.get_custom_css(), unsafe_allow_html=True)

# 1. Configuration Validation
if not config.is_config_valid():
    st.markdown(utiles.get_custom_css(), unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 16px;
                padding: 2.5rem;
                margin-top: 4rem;
                box-shadow: 0 8px 32px rgba(239, 68, 68, 0.05);
                text-align: center;
            '>
                <h1 style='font-size: 3rem; margin: 0;'>⚙️</h1>
                <h2 style='
                    background: linear-gradient(135deg, #ef4444, #f87171);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    font-weight: 700;
                    margin-top: 1rem;
                '>Configuration Required</h2>
                <p style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6; margin-top: 1rem;'>
                    Supabase credentials are not configured in your environment variables or Streamlit secrets.
                </p>
                <div style='
                    text-align: left; 
                    background: #0f111a; 
                    padding: 1.25rem; 
                    border-radius: 8px; 
                    border: 1px solid rgba(255,255,255,0.06); 
                    margin: 1.5rem 0;
                '>
                    <p style='margin: 0 0 0.5rem 0; font-size: 0.8rem; color: #94a3b8;'>Create a <code>.env</code> file in the project root:</p>
                    <pre style='margin: 0; color: #f87171; font-family: monospace; font-size: 0.9rem;'>SUPABASE_URL=your-supabase-url&#10;SUPABASE_KEY=your-supabase-key</pre>
                </div>
                <p style='color: #64748b; font-size: 0.85rem;'>
                    Please restart the server after creating the file.
                </p>
            </div>
        """, unsafe_allow_html=True)
    st.stop()

# Initialize Auth State
auth.init_auth_state()

# 2. Routing Logic
if st.session_state["user"] is None:
    auth.render_auth_ui()
else:
    user = st.session_state["user"]
    profile = st.session_state["profile"]
    
    # Sidebar Navigation UI
    with st.sidebar:
        # Generate initials for avatar
        initials = "U"
        if profile and profile.get('full_name'):
            parts = profile.get('full_name', '').split()
            initials = "".join([p[0].upper() for p in parts[:2]])
        elif user and user.email:
            initials = user.email[:2].upper()
            
        st.markdown(f"""
            <div class='sidebar-user'>
                <div style='display: flex; align-items: center; gap: 0.75rem;'>
                    <div style='
                        width: 42px; 
                        height: 42px; 
                        border-radius: 50%; 
                        background: linear-gradient(135deg, #8b5cf6, #d946ef); 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        font-weight: 700; 
                        color: white;
                        font-size: 0.95rem;
                        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.25);
                    '>
                        {initials}
                    </div>
                    <div style='flex: 1; min-width: 0;'>
                        <p style='margin: 0; font-size: 0.75rem; color: #94a3b8;'>Logged in as</p>
                        <h5 style='margin: 0; font-size: 0.9rem; font-weight: 600; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                            {profile.get('full_name', 'User') if profile else user.email}
                        </h5>
                        <div style='display: flex; align-items: center; gap: 0.25rem; margin-top: 0.1rem;'>
                            <span style='width: 6px; height: 6px; border-radius: 50%; background-color: #34d399; box-shadow: 0 0 8px #34d399;'></span>
                            <span style='font-size: 0.7rem; color: #34d399; font-weight: 600;'>Online</span>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Navigation Options
        page = st.radio(
            "Navigation",
            ["📄 Document Extractor", "📝 Manage Prompts", "⚙️ API Settings", "👤 Profile"],
            index=0
        )
        
        st.markdown("---")
        
        # Sign Out button at the bottom
        if st.sidebar.button("🚪 Log Out", use_container_width=True):
            auth.sign_out()
            
      # --- PAGE: DOCUMENT EXTRACTOR ---
    if page == "📄 Document Extractor":
        st.markdown("## <span class='gradient-text'>📄 Document Extractor</span>", unsafe_allow_html=True)
        st.caption("Upload a document, choose a dynamic prompt template, and extract structured data using LLMs.")
        
        # Fetch user's settings and prompts
        settings = database.get_user_settings(user.id)
        prompts = database.get_prompts(user.id)
        
        if not prompts:
            st.warning("⚠️ You don't have any prompt templates yet. Please head over to the **Manage Prompts** tab to create one.")
            st.stop()
            
        # UI layout with columns
        col_input, col_result = st.columns([1, 1], gap="large")
        
        extracted_data_key = "current_extracted_data"
        if extracted_data_key not in st.session_state:
            st.session_state[extracted_data_key] = None
            
        if "doc_uploader_val" not in st.session_state:
            st.session_state["doc_uploader_val"] = 0
            
        with col_input:
            st.markdown("### 1. Configure Extraction")
            
            # Select prompt
            prompt_options = {p["id"]: p for p in prompts}
            selected_prompt_id = st.selectbox(
                "Select Prompt Template",
                options=list(prompt_options.keys()),
                format_func=lambda x: prompt_options[x]["name"]
            )
            
            selected_prompt = prompt_options[selected_prompt_id]
            st.markdown(f"""
                <div style='background: rgba(99, 102, 241, 0.05); border-left: 4px solid #6366f1; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;'>
                    <span style='font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #a5b4fc; font-weight: 600;'>Extraction Blueprint</span>
                    <p style='margin: 0.5rem 0 0 0; color: #e2e8f0; font-size: 0.92rem; line-height: 1.5;'>{selected_prompt['prompt_template']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # File Uploader
            uploaded_file = st.file_uploader(
                "Upload Document (.pdf, .docx, .txt)",
                type=["pdf", "docx", "txt"],
                key=f"doc_uploader_{st.session_state['doc_uploader_val']}"
            )
            
            extracted_text = ""
            if uploaded_file is not None:
                st.success(f"📂 {uploaded_file.name} uploaded successfully!")
                
                # Try parsing the document
                try:
                    with st.spinner("Reading file contents..."):
                        extracted_text = utiles.extract_text(uploaded_file)
                    
                    with st.expander("👁️ Show Raw Document Text Preview", expanded=False):
                        st.markdown(f"""
                            <div class="document-preview-container">
                                <pre class="document-preview-text">{extracted_text}</pre>
                            </div>
                        """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error reading file: {e}")
            
            # Extraction trigger
            st.markdown("---")
            
            # Model indicator
            if config.is_ollama_enabled():
                provider = "ollama"
                model = "gpt-oss:120b-cloud"
                has_api_key = True
                st.info("🔌 **Ollama local execution active** (configured via env). No API key required.")
            else:
                provider = settings.get("selected_provider", "openai")
                model = settings.get("selected_model", "gpt-4o-mini")
                
                # Check API key presence for current provider
                api_key_field = f"{provider}_api_key"
                has_api_key = bool(settings.get(api_key_field))
                
                if not has_api_key:
                    st.warning(f"⚠️ No API key set for {provider.upper()}. Please configure it in **API Settings** first.")
            
            st.caption(f"Current LLM config: **{provider.upper()} ({model})**")
                
            trigger_extraction = st.button(
                "⚡ Extract Structured Details",
                use_container_width=True,
                type="primary",
                disabled=(uploaded_file is None or not has_api_key)
            )
            
            if trigger_extraction and extracted_text:
                loading_placeholder = st.empty()
                with loading_placeholder.container():
                    st.markdown(f"""
                        <div class="extraction-loader">
                            <div class="loader-spinner"></div>
                            <h4 class="loader-title">Analyzing & Extracting Details</h4>
                            <p class="loader-desc">Please wait while the AI parses your document and converts it to JSON format using {provider.upper()} ({model})...</p>
                        </div>
                    """, unsafe_allow_html=True)
                try:
                    result_json = servies.extract_document_details(
                        document_text=extracted_text,
                        prompt_template=selected_prompt["prompt_template"],
                        user_settings=settings
                    )
                    
                    st.session_state[extracted_data_key] = result_json
                    # Programmatically clear the file uploader widget
                    st.session_state["doc_uploader_val"] += 1
                    st.toast("Extraction completed successfully!", icon="🚀")
                    
                except Exception as e:
                    st.error(f"Extraction failed: {e}")
                finally:
                    loading_placeholder.empty()
                    st.rerun()
                        
        with col_result:
            st.markdown("### 2. Extracted Results")
            
            if st.session_state[extracted_data_key]:
                result = st.session_state[extracted_data_key]
                st.success("JSON extracted successfully!")
                
                # Tabbed results representation
                res_tab_pretty, res_tab_raw = st.tabs(["📊 Structured Fields", "💻 Raw JSON"])
                
                with res_tab_pretty:
                    st.markdown(utiles.render_smart_extracted_data(result), unsafe_allow_html=True)
                        
                with res_tab_raw:
                    st.code(json.dumps(result, indent=2), language="json")
                    
                st.write("")
                if st.button("🗑️ Clear Active Result", key="clear_active_res", use_container_width=True):
                    st.session_state[extracted_data_key] = None
                    st.rerun()
            else:
                st.markdown("""
                    <div class="empty-state-container">
                        <div class="empty-state-icon">📥</div>
                        <h4 style='color: #cbd5e1; font-weight: 600; margin-bottom: 0.5rem;'>Extracted details will appear here</h4>
                        <p style='color: #94a3b8; font-size: 0.9rem; max-width: 80%; margin: 0 auto;'>Upload a document and click "Extract Structured Details" to initiate the extraction process.</p>
                    </div>
                """, unsafe_allow_html=True)
                
        # Extraction History section
        st.markdown("---")
        st.markdown("### 📜 Extraction History")
        
        history = database.get_extracted_documents(user.id)
        if not history:
            st.info("No document extractions yet.")
        else:
            for doc in history:
                prompt_name = doc.get("prompts", {}).get("name", "Unknown Prompt") if doc.get("prompts") else "Deleted Prompt"
                created_str = doc["created_at"][:16].replace("T", " ")
                
                with st.container(border=True):
                    col_meta, col_btn_view, col_btn_del = st.columns([7, 1.5, 1.5], gap="small")
                    with col_meta:
                        st.markdown(f"""
                            <div style='display: flex; flex-direction: column;'>
                                <span style='font-size: 1.05rem; font-weight: 600; color: #f1f5f9; display: flex; align-items: center; gap: 0.5rem;'>
                                    📁 {doc['filename']}
                                </span>
                                <span style='font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem;'>
                                    Template: <strong style="color: #c084fc;">{prompt_name}</strong> &nbsp;|&nbsp; 🕰️ {created_str}
                                </span>
                            </div>
                        """, unsafe_allow_html=True)
                    with col_btn_view:
                        with st.popover("👁️ View", use_container_width=True):
                            st.markdown(f"#### 📊 Extracted Results")
                            st.markdown(f"**File:** `{doc['filename']}`")
                            st.markdown(f"**Template:** `{prompt_name}` | `{created_str}`")
                            st.markdown("---")
                            
                            # Render the saved JSON neatly
                            data = doc["extracted_data"]
                            st.markdown(utiles.render_smart_extracted_data(data), unsafe_allow_html=True)
                                
                            st.markdown("##### 💻 Raw JSON")
                            st.code(json.dumps(data, indent=2), language="json")
                            
                    with col_btn_del:
                        if st.button("🗑️", key=f"del_{doc['id']}", use_container_width=True, help="Delete record"):
                            if database.delete_extracted_document(doc["id"], user.id):
                                st.toast("Extraction record deleted.", icon="🗑️")
                                time.sleep(0.5)
                                st.rerun()

    # --- PAGE: MANAGE PROMPTS ---
    elif page == "📝 Manage Prompts":
        st.markdown("## <span class='gradient-text'>📝 Manage Prompts</span>", unsafe_allow_html=True)
        st.caption("Create and customize dynamic extraction prompts. These prompts instruct the LLM on which details to extract.")
        
        # Form to add new prompt
        with st.expander("➕ Create New Prompt Template", expanded=True):
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
                                
        st.markdown("### Your Custom Templates")
        prompts = database.get_prompts(user.id)
        
        if not prompts:
            st.info("You haven't created any custom prompts yet.")
        else:
            for p in prompts:
                with st.container(border=True):
                    col_p_info, col_p_actions = st.columns([7, 3])
                    with col_p_info:
                        st.markdown(f"""
                            <div style='display: flex; flex-direction: column;'>
                                <h4 style='margin: 0; color: #f1f5f9; font-weight: 600;'>📝 {p['name']}</h4>
                                <p style='margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.4;'>
                                    Created on: {p['created_at'][:10]}
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        with st.expander("👁️ View Instructions"):
                            st.code(p['prompt_template'], language="text")
                    with col_p_actions:
                        st.write("") # Spacer
                        c_edit, c_del = st.columns(2)
                        with c_edit:
                            with st.popover("✏️ Edit", use_container_width=True):
                                with st.form(f"edit_form_{p['id']}"):
                                    edit_name = st.text_input("Template Name", value=p["name"])
                                    edit_template = st.text_area("Instructions (Template)", value=p["prompt_template"], height=150)
                                    save_edit = st.form_submit_button("Save Changes", use_container_width=True)
                                    if save_edit:
                                        if database.update_prompt(p["id"], user.id, edit_name, edit_template):
                                            st.success("Prompt updated!")
                                            time.sleep(0.5)
                                            st.rerun()
                        with c_del:
                            if st.button("🗑️", key=f"del_p_{p['id']}", use_container_width=True, help="Delete Prompt"):
                                if database.delete_prompt(p["id"], user.id):
                                    st.toast("Prompt template deleted.", icon="🗑️")
                                    time.sleep(0.5)
                                    st.rerun()

    # --- PAGE: API SETTINGS ---
    elif page == "⚙️ API Settings":
        st.markdown("## <span class='gradient-text'>⚙️ API Settings</span>", unsafe_allow_html=True)
        st.caption("Manage LLM keys and choose your default provider and extraction models.")
        
        if config.is_ollama_enabled():
            st.info("🔌 **Ollama Override Active:** Local execution is enabled in `.env` with model `gpt-oss:120b-cloud`. Changes to the settings below will not affect extraction until Ollama is disabled in `.env`.")
            
        # Load user's current settings
        settings = database.get_user_settings(user.id)
        
        # API Key Status Indicators
        st.markdown("### 🔌 API Keys Status")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            has_openai = bool(settings.get("openai_api_key"))
            status_html = "<span style='color: #4ade80; font-weight: 600;'>● Configured</span>" if has_openai else "<span style='color: #94a3b8;'>○ Not Configured</span>"
            st.markdown(f"""
                <div style='background: rgba(255, 255, 255, 0.02); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); text-align: center;'>
                    <p style='margin: 0; font-size: 0.85rem; color: #94a3b8; font-weight: 600;'>OpenAI</p>
                    <h5 style='margin: 0.5rem 0 0 0;'>{status_html}</h5>
                </div>
            """, unsafe_allow_html=True)
        with col_s2:
            has_anthropic = bool(settings.get("anthropic_api_key"))
            status_html = "<span style='color: #4ade80; font-weight: 600;'>● Configured</span>" if has_anthropic else "<span style='color: #94a3b8;'>○ Not Configured</span>"
            st.markdown(f"""
                <div style='background: rgba(255, 255, 255, 0.02); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); text-align: center;'>
                    <p style='margin: 0; font-size: 0.85rem; color: #94a3b8; font-weight: 600;'>Anthropic</p>
                    <h5 style='margin: 0.5rem 0 0 0;'>{status_html}</h5>
                </div>
            """, unsafe_allow_html=True)
        with col_s3:
            has_gemini = bool(settings.get("gemini_api_key"))
            status_html = "<span style='color: #4ade80; font-weight: 600;'>● Configured</span>" if has_gemini else "<span style='color: #94a3b8;'>○ Not Configured</span>"
            st.markdown(f"""
                <div style='background: rgba(255, 255, 255, 0.02); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); text-align: center;'>
                    <p style='margin: 0; font-size: 0.85rem; color: #94a3b8; font-weight: 600;'>Gemini</p>
                    <h5 style='margin: 0.5rem 0 0 0;'>{status_html}</h5>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        
        # Form to configure settings
        with st.form("api_settings_form"):
            col_conf_model, col_conf_keys = st.columns([1, 1], gap="large")
            
            with col_conf_model:
                st.markdown("#### ⚙️ LLM Preferences")
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
                st.markdown("#### 🔑 Set API Keys")
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
                
            submit_settings = st.form_submit_button("⚡ Save Configurations", use_container_width=True)
            
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
    elif page == "👤 Profile":
        st.markdown("## <span class='gradient-text'>👤 User Profile</span>", unsafe_allow_html=True)
        st.caption("Manage your profile details and view your account statistics.")
        
        # Load stats
        history = database.get_extracted_documents(user.id)
        prompts = database.get_prompts(user.id)
        settings = database.get_user_settings(user.id)
        
        total_docs = len(history)
        total_prompts = len(prompts)
        
        # Profile Card Header
        with st.container(border=True):
            col_avatar, col_info = st.columns([1, 3])
            with col_avatar:
                # Initials for avatar
                initials = ""
                name_parts = profile.get('full_name', '').split() if profile else []
                if name_parts:
                    initials = "".join([part[0].upper() for part in name_parts[:2]])
                else:
                    initials = user.email[:2].upper()
                    
                st.markdown(f"""
                    <div style='
                        width: 100px; 
                        height: 100px; 
                        border-radius: 50%; 
                        background: linear-gradient(135deg, #6366f1, #a855f7); 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        font-size: 2.2rem; 
                        font-weight: 700; 
                        color: white; 
                        box-shadow: 0 8px 24px rgba(168, 85, 247, 0.25);
                        margin: auto;
                    '>
                        {initials}
                    </div>
                """, unsafe_allow_html=True)
            with col_info:
                st.markdown(f"""
                    <h3 style='margin: 0; font-weight: 700; color: #f1f5f9;'>{profile.get('full_name', 'User') if profile else 'User'}</h3>
                    <p style='margin: 0.2rem 0; font-size: 1rem; color: #a855f7;'>@{profile.get('username', 'user') if profile else 'user'}</p>
                    <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #94a3b8;'>✉️ {user.email}</p>
                """, unsafe_allow_html=True)
                
        # Stats Grid
        st.markdown("### 📊 Account Statistics")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon">📄</div>
                    <div class="metric-value">{total_docs}</div>
                    <div class="metric-label">Extracted Docs</div>
                </div>
            """, unsafe_allow_html=True)
        with col_stat2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon">📝</div>
                    <div class="metric-value">{total_prompts}</div>
                    <div class="metric-label">Saved Templates</div>
                </div>
            """, unsafe_allow_html=True)
        with col_stat3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon">⚙️</div>
                    <div class="metric-value" style="font-size: 1.15rem; padding: 0.6rem 0; color: #a855f7; font-weight: 600;">
                        {settings.get('selected_provider', 'openai').upper()}
                    </div>
                    <div class="metric-label">Default LLM</div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        
        # Form to edit profile details
        with st.expander("✏️ Update Profile Details", expanded=False):
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
