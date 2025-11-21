import streamlit as st
import os
import json
import smtplib
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Email Action Bot",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .email-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    .result-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("GOOGLE_API_KEY", "")
if 'dept_emails' not in st.session_state:
    st.session_state.dept_emails = {
        "Finance": "",
        "HR": "",
        "IT Support": "",
        "Sales": "",
        "Marketing": "",
        "Legal": "",
        "Operations": "",
        "Executive": ""
    }

# --- Helper Functions ---

def send_email(sender_email, sender_password, recipient_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"FWD: {subject}"
        msg.attach(MIMEText(f"Original Email Body:\n\n{body}", 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        return True, f"Email forwarded successfully to {recipient_email}!"
    except Exception as e:
        return False, str(e)

# --- Login Screen ---
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 Login</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Email Action Bot</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                if username == "admin" and password == "admin":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials (try admin/admin)")

# --- Main Application ---
def main_app():
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")
        
        with st.expander("🔑 API Keys", expanded=True):
            api_key_input = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password")
            if api_key_input:
                st.session_state.api_key = api_key_input
                genai.configure(api_key=st.session_state.api_key)
                
                try:
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    gemini_models = [m for m in models if 'gemini' in m]
                    if not gemini_models: gemini_models = ["models/gemini-1.5-flash"]
                    st.session_state.model_name = st.selectbox("Select Model", gemini_models, index=0)
                except:
                    st.session_state.model_name = "models/gemini-1.5-flash"

        with st.expander("📧 Gmail Integration", expanded=True):
            st.info("👉 **Note:** Use a **Google App Password**. [Guide here](https://support.google.com/accounts/answer/185833)")
            sender_email = st.text_input("Your Gmail Address")
            sender_password = st.text_input("App Password (16 chars)", type="password")

        with st.expander("🏢 Department Setup", expanded=True):
            st.markdown("Map departments to email addresses for auto-forwarding.")
            for dept in st.session_state.dept_emails.keys():
                st.session_state.dept_emails[dept] = st.text_input(f"{dept} Email", value=st.session_state.dept_emails[dept], placeholder=f"{dept.lower().replace(' ', '')}@company.com")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # Header
    st.title("📧 Email Understanding & Action Bot")
    st.markdown("Classify emails and route them to the correct department automatically.")
    st.divider()

    # Layout
    col_left, col_right = st.columns([5, 4])

    with col_left:
        st.subheader("📥 Incoming Email")
        
        # 10 Examples
        examples = {
            "Select an example...": {"subject": "", "body": ""},
            "1. Invoice (Finance)": {
                "subject": "Invoice #2024-99 for Design Services", 
                "body": "Please find attached the invoice for $2,000. Payment due in 15 days."
            },
            "2. Sick Leave (HR)": {
                "subject": "Sick Leave - John Doe", 
                "body": "I am feeling unwell and will be taking a sick day today. I'll check emails periodically."
            },
            "3. Laptop Issue (IT)": {
                "subject": "Blue Screen Error", 
                "body": "My laptop keeps crashing with a blue screen. I cannot work. Please assist ASAP."
            },
            "4. Sales Lead (Sales)": {
                "subject": "Inquiry about Enterprise Plan", 
                "body": "We are interested in purchasing 500 licenses for your software. Can we get a quote?"
            },
            "5. Partnership (Marketing)": {
                "subject": "Collaboration Opportunity", 
                "body": "We would like to feature your product in our upcoming tech conference. Let's discuss sponsorship."
            },
            "6. Contract Review (Legal)": {
                "subject": "NDA for Project X", 
                "body": "Attached is the NDA for the new vendor. Please review and sign by EOD."
            },
            "7. Office Supplies (Operations)": {
                "subject": "Printer Paper Low", 
                "body": "We are out of A4 paper in the 2nd floor copy room. Please restock."
            },
            "8. Quarterly Report (Executive)": {
                "subject": "Q3 Financial Results", 
                "body": "Here is the summary of Q3 performance. Revenue is up 20%. Board meeting is next week."
            },
            "9. Job Application (HR)": {
                "subject": "Application: Senior Dev - Alice", 
                "body": "I am applying for the Senior Developer role. My resume is attached."
            },
            "10. Refund Request (Finance)": {
                "subject": "Refund for Order #12345", 
                "body": "I was charged twice for my order. Please refund the duplicate charge of $50."
            }
        }
        
        selected_example = st.selectbox("Load Example", list(examples.keys()))
        
        if selected_example != "Select an example...":
            default_sub = examples[selected_example]["subject"]
            default_body = examples[selected_example]["body"]
        else:
            default_sub = ""
            default_body = ""

        with st.container():
            st.markdown('<div class="email-card">', unsafe_allow_html=True)
            subject = st.text_input("Subject", value=default_sub)
            body = st.text_area("Body", value=default_body, height=250)
            st.markdown('</div>', unsafe_allow_html=True)
            
        analyze_btn = st.button("🔍 Analyze Email", type="primary")

    with col_right:
        st.subheader("🤖 Analysis & Routing")
        
        if analyze_btn and body:
            if not st.session_state.api_key:
                st.error("Please configure Gemini API Key in sidebar.")
            else:
                with st.spinner("Processing..."):
                    try:
                        model = genai.GenerativeModel(st.session_state.get('model_name', 'models/gemini-1.5-flash'))
                        
                        # Dynamic list of departments for the prompt
                        dept_list = ", ".join(st.session_state.dept_emails.keys())
                        
                        prompt = f"""
                        Analyze this email and route it to the correct department.
                        
                        Available Departments: [{dept_list}]
                        
                        Email Subject: {subject}
                        Email Body: {body}
                        
                        Return JSON:
                        {{
                            "classification": "Short summary of intent (e.g. Invoice, Leave Request)",
                            "department": "One of the Available Departments strictly",
                            "justification": "Why this department is the correct choice",
                            "suggested_action": "Specific action (e.g. Forward to Finance)"
                        }}
                        """
                        
                        response = model.generate_content(prompt)
                        text = response.text.strip()
                        if text.startswith("```json"): text = text[7:-3]
                        result = json.loads(text)
                        
                        # Display Results
                        st.markdown(f"""
                            <div class="result-card" style="border-left: 5px solid #4CAF50;">
                                <h3>🏷️ {result['classification']}</h3>
                                <p><strong>Department:</strong> <span class="status-badge" style="background:#e8f0fe; color:#1a73e8;">{result['department']}</span></p>
                                <hr>
                                <p><strong>Reason:</strong> {result['justification']}</p>
                                <p><strong>Action:</strong> {result['suggested_action']}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Store result
                        st.session_state.last_result = result
                        st.session_state.last_subject = subject
                        st.session_state.last_body = body
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Quota exceeded" in error_msg:
                            st.error("🚨 Quota Exceeded! Try a different model.")
                        else:
                            st.error(f"Error: {error_msg}")

        # Action Execution Section
        if 'last_result' in st.session_state:
            st.markdown("### ⚡ Execute Action")
            result = st.session_state.last_result
            target_dept = result.get('department')
            target_email = st.session_state.dept_emails.get(target_dept)
            
            if target_email:
                st.info(f"Ready to forward to **{target_dept}** ({target_email})")
                if st.button(f"📧 Forward to {target_dept}"):
                    if not (sender_email and sender_password):
                        st.error("Please configure your Gmail credentials in the sidebar first.")
                    else:
                        with st.spinner(f"Sending to {target_email}..."):
                            success, msg = send_email(sender_email, sender_password, target_email, st.session_state.last_subject, st.session_state.last_body)
                            if success: st.success(msg)
                            else: st.error(msg)
            else:
                st.warning(f"⚠️ No email configured for **{target_dept}**.")
                st.markdown("👉 Please add an email address for this department in the **Department Setup** sidebar.")

# --- Router ---
if st.session_state.logged_in:
    main_app()
else:
    login_page()
