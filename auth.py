import streamlit as st
from database import get_supabase_client, get_profile, update_profile
import time
import utiles

def init_auth_state():
    """Initializes the authentication state variables in session_state."""
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "session" not in st.session_state:
        st.session_state["session"] = None
    if "profile" not in st.session_state:
        st.session_state["profile"] = None

def sign_in(email, password) -> bool:
    """Signs in a user with email and password."""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if response.user:
            st.session_state["user"] = response.user
            st.session_state["session"] = response.session
            # Load user profile
            profile = get_profile(response.user.id)
            # If profile doesn't exist, create a skeleton profile
            if not profile:
                username = email.split('@')[0]
                update_profile(response.user.id, username, username.capitalize())
                profile = get_profile(response.user.id)
            st.session_state["profile"] = profile
            return True
        return False
    except Exception as e:
        st.error(f"Sign in failed: {str(e)}")
        return False

def sign_up(email, password, username, full_name) -> bool:
    """Registers a new user with email, password, and metadata."""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": username,
                    "full_name": full_name
                }
            }
        })
        
        # Check if email confirmation is required or if signed up directly
        if response.user:
            # If session is active (auto sign in on sign up)
            if response.session:
                st.session_state["user"] = response.user
                st.session_state["session"] = response.session
                st.session_state["profile"] = {
                    "id": response.user.id,
                    "username": username,
                    "full_name": full_name
                }
                # Sync database profiles
                update_profile(response.user.id, username, full_name)
                st.success("Account created and signed in successfully!")
            else:
                st.success("Registration successful! Please check your email to confirm registration before signing in.")
            return True
        return False
    except Exception as e:
        st.error(f"Sign up failed: {str(e)}")
        return False

def sign_out():
    """Signs out the current user and clears session state."""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except Exception as e:
        print(f"Error during Supabase signout: {e}")
    
    st.session_state["user"] = None
    st.session_state["session"] = None
    st.session_state["profile"] = None
    st.rerun()

def render_auth_ui():
    """Renders the Login / Register UI on the main screen."""
    init_auth_state()
    
    # Inject global styles
    st.markdown(utiles.get_custom_css(), unsafe_allow_html=True)
    
    # Center the login panel
    col_left, col_center, col_right = st.columns([1, 1.8, 1])
    
    with col_center:
        st.markdown("""
            <div style='text-align: center; margin-top: 3rem; margin-bottom: 2rem;'>
                <h1 style='font-size: 2.8rem; font-weight: 700; background: linear-gradient(135deg, #a78bfa, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                    DocuExtract POC
                </h1>
                <p style='color: #cbd5e1; font-size: 1rem; margin-top: 0.5rem;'>
                    Extract structured details from documents with AI
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["🔑 Sign In", "📝 Create Account"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Sign In", use_container_width=True)
                
                if submit:
                    if not email or not password:
                        st.warning("Please fill in all fields.")
                    else:
                        with st.spinner("Signing in..."):
                            if sign_in(email, password):
                                st.success("Successfully signed in!")
                                time.sleep(0.5)
                                st.rerun()
    
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("Email Address", placeholder="name@example.com")
                new_password = st.text_input("Choose Password", type="password", placeholder="At least 6 characters")
                new_username = st.text_input("Username", placeholder="johndoe")
                new_fullname = st.text_input("Full Name", placeholder="John Doe")
                
                submit_signup = st.form_submit_button("Sign Up", use_container_width=True)
                
                if submit_signup:
                    if not new_email or not new_password or not new_username or not new_fullname:
                        st.warning("All fields are required.")
                    elif len(new_password) < 6:
                        st.warning("Password must be at least 6 characters.")
                    else:
                        with st.spinner("Registering..."):
                            if sign_up(new_email, new_password, new_username, new_fullname):
                                time.sleep(1)
                                st.rerun()
