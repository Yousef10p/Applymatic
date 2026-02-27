import re
import tldextract
import pdfplumber


def extract_leads_from_pdf(file_path):
    """
    Extracts raw text from a PDF, finds all emails, and infers company data.
    """
    raw_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")

    # Extract Emails, URLs, and infer Company Names
    EMAIL_RE = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    raw_emails = list(set(re.findall(EMAIL_RE, raw_text)))

    leads = []
    for email in raw_emails:
        # Parse the domain from the email
        ext = tldextract.extract(email.split('@')[1])
        domain = f"{ext.domain}.{ext.suffix}"

        # Infer company name: 'future-tech' -> 'Future Tech'
        company_name = ext.domain.replace('-', ' ').title()

        leads.append({
            "email": email.lower(),
            "website": domain,
            "company_name": company_name
        })

    return leads




























import base64
import mimetypes
from email.message import EmailMessage
from googleapiclient.discovery import build

# ... (keep your existing extract_leads_from_pdf function here) ...

def send_gmail_message(credentials, sender_email, to_email, subject, body_text, resume_pdf=None, attachments=None):
    """
    Builds a MIME message with attachments and sends it via the Gmail API.
    """
    message = EmailMessage()
    message['To'] = to_email
    message['From'] = sender_email
    message['Subject'] = subject
    message.set_content(body_text)

    # 1. Attach the Resume
    if resume_pdf:
        resume_pdf.seek(0)  # Reset file pointer just in case
        message.add_attachment(
            resume_pdf.read(),
            maintype='application',
            subtype='pdf',
            filename=resume_pdf.name
        )

    # 2. Attach Extra Files (if any)
    if attachments:
        for file in attachments:
            file.seek(0)
            ctype, _ = mimetypes.guess_type(file.name)
            if ctype is None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            message.add_attachment(
                file.read(),
                maintype=maintype,
                subtype=subtype,
                filename=file.name
            )

    # 3. Base64 encode for the Gmail API
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'raw': encoded_message}

    # 4. Dispatch via Gmail API
    service = build('gmail', 'v1', credentials=credentials)
    try:
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        return sent_message
    except Exception as e:
        print(f"Error sending to {to_email}: {e}")
        return None