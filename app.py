import streamlit as st
import os
import json
import smtplib
import google.generativeai as genai
import imaplib
import email
from email.header import decode_header
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

# --- Configuration Management ---
CONFIG_FILE = "user_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

config = load_config()

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'api_key' not in st.session_state:
    st.session_state.api_key = config.get('api_key', os.getenv("GOOGLE_API_KEY", ""))
if 'sender_email' not in st.session_state:
    st.session_state.sender_email = config.get('sender_email', "")
if 'sender_password' not in st.session_state:
    st.session_state.sender_password = config.get('sender_password', "")
if 'dept_emails' not in st.session_state:
    st.session_state.dept_emails = config.get('dept_emails', {
        "Finance": "",
        "HR": "",
        "IT Support": "",
        "Sales": "",
        "Marketing": "",
        "Legal": "",
        "Operations": "",
        "Executive": ""
    })

# --- Helper Functions ---

def fetch_emails(username, password, limit=5):
    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        mail.select("inbox")

        # Search for recent emails
        _, search_data = mail.search(None, "ALL")
        mail_ids = search_data[0].split()
        
        # Get last 'limit' emails
        latest_email_ids = mail_ids[-limit:]
        emails = []

        for e_id in reversed(latest_email_ids):
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode Subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    # Get Body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                        
                    emails.append({"subject": subject, "body": body})
        
        mail.logout()
        return True, emails
    except Exception as e:
        return False, str(e)

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
                    # List only Gemini models that support generateContent
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and m.name.startswith('models/gemini-')]
                    # Ensure at least a default model is available
                    if not models:
                        models = ["models/gemini-1.5-flash"]
                    st.session_state.model_name = st.selectbox("Select Model", models, index=0)
                except Exception as e:
                    st.error(f"Failed to list models: {e}")
                    st.session_state.model_name = "models/gemini-1.5-flash"

        with st.expander("🏢 Department Setup", expanded=True):
            st.markdown("Map departments to email addresses for auto-forwarding.")
            for dept in st.session_state.dept_emails.keys():
                st.session_state.dept_emails[dept] = st.text_input(f"{dept} Email", value=st.session_state.dept_emails[dept], placeholder=f"{dept.lower().replace(' ', '')}@company.com")

        st.markdown("---")
        if st.button("💾 Save Settings"):
            config_data = {
                "api_key": st.session_state.api_key,
                "sender_email": st.session_state.sender_email,
                "sender_password": st.session_state.sender_password,
                "dept_emails": st.session_state.dept_emails
            }
            save_config(config_data)
            st.success("Settings saved to user_config.json!")

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
        
        # Tabs for Source
        tab1, tab2 = st.tabs(["📂 Examples", "🔴 Live Gmail"])
        
        with tab1:
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

        with tab2:
            st.markdown("Fetch recent emails from your Inbox.")
            if st.button("🔄 Fetch Recent Emails"):
                if not (st.session_state.sender_email and st.session_state.sender_password):
                    st.error("Configure Gmail credentials in sidebar first!")
                else:
                    with st.spinner("Connecting to Gmail..."):
                        success, fetched_emails = fetch_emails(st.session_state.sender_email, st.session_state.sender_password)
                        if success:
                            st.session_state.fetched_emails = fetched_emails
                            st.success(f"Fetched {len(fetched_emails)} emails.")
                        else:
                            st.error(f"Failed: {fetched_emails}")
            
            if 'fetched_emails' in st.session_state:
                email_options = {f"{i+1}. {e['subject'][:40]}...": i for i, e in enumerate(st.session_state.fetched_emails)}
                selected_live = st.selectbox("Select Email", list(email_options.keys()))
                if selected_live:
                    idx = email_options[selected_live]
                    default_sub = st.session_state.fetched_emails[idx]['subject']
                    default_body = st.session_state.fetched_emails[idx]['body']

        with st.container():
            st.markdown('<div class="email-card">', unsafe_allow_html=True)
            # Use session state to persist manual edits if needed, but overwrite on selection
            if 'current_subject' not in st.session_state: st.session_state.current_subject = ""
            if 'current_body' not in st.session_state: st.session_state.current_body = ""
            
            # Update if defaults changed (from selection)
            if default_sub: st.session_state.current_subject = default_sub
            if default_body: st.session_state.current_body = default_body

            subject = st.text_input("Subject", value=st.session_state.current_subject)
            body = st.text_area("Body", value=st.session_state.current_body, height=250)
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
                        elif "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
                            st.error("🚨 Invalid API Key!")
                            st.warning("Please check your Google Gemini API Key in the sidebar settings. Ensure there are no extra spaces.")
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
                    if not (st.session_state.sender_email and st.session_state.sender_password):
                        st.error("Please configure your Gmail credentials in the sidebar first.")
                    else:
                        with st.spinner(f"Sending to {target_email}..."):
                            success, msg = send_email(st.session_state.sender_email, st.session_state.sender_password, target_email, st.session_state.last_subject, st.session_state.last_body)
                            if success: 
                                st.success(msg)
                            else:
                                if "535" in msg:
                                    st.error("🚨 Gmail Authentication Failed (Error 535)")
                                    st.warning("This usually means you are using your **Login Password** instead of an **App Password**.")
                                    st.markdown("👉 [Click here for the App Password Guide](https://support.google.com/accounts/answer/185833)")
                                else:
                                    st.error(msg)
            else:
                st.warning(f"⚠️ No email configured for **{target_dept}**.")
                st.markdown("👉 Please add an email address for this department in the **Department Setup** sidebar.")

# --- Router ---
if st.session_state.logged_in:
    main_app()
else:
    login_page()
