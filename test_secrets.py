import streamlit as st

# Test reading secrets
try:
    jira_url = st.secrets["JIRA_URL"]
    google_key = st.secrets["GOOGLE_API_KEY"]
    secret_key = st.secrets["SECRET_KEY"]
    
    st.write("✅ Secrets loaded successfully!")
    st.write(f"Jira URL: {jira_url}")
    st.write("Google API Key: [HIDDEN]")
    st.write("Secret Key: [HIDDEN]")
    
except Exception as e:
    st.error(f"❌ Error loading secrets: {e}")