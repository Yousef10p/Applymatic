import os
import re
import hashlib
from django.conf import settings
import tldextract
import pdfplumber
from email.message import EmailMessage
from googleapiclient.discovery import build
import base64
import mimetypes


# ==========================================
# 1. Extraction & Email Utils
# ==========================================

def extract_leads_from_pdf(file_path):
    raw_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")

    EMAIL_RE = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    raw_emails = list(set(re.findall(EMAIL_RE, raw_text)))

    leads = []
    for email in raw_emails:
        ext = tldextract.extract(email.split('@')[1])
        domain = f"{ext.domain}.{ext.suffix}"
        company_name = ext.domain.replace('-', ' ').title()

        leads.append({
            "email": email.lower(),
            "website": domain,
            "company_name": company_name
        })

    return leads


def send_gmail_message(credentials, sender_email, to_email, subject, body_text, resume_pdf=None, attachments=None):
    message = EmailMessage()
    message['To'] = to_email
    message['From'] = sender_email
    message['Subject'] = subject
    message.set_content(body_text)

    if resume_pdf:
        resume_pdf.seek(0)
        message.add_attachment(
            resume_pdf.read(),
            maintype='application',
            subtype='pdf',
            filename=resume_pdf.name
        )

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
                filename=os.path.basename(file.name)
            )

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'raw': encoded_message}

    service = build('gmail', 'v1', credentials=credentials)
    try:
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        return sent_message
    except Exception as e:
        print(f"Error sending to {to_email}: {e}")
        return None


# ==========================================
# 2. File Saving & Folder Structure Utils
# ==========================================

def get_file_hash(file_obj):
    hasher = hashlib.sha256()
    file_obj.seek(0)
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()


def get_text_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def save_campaign_records(user, companies_pdf, cover_letter_text, resume_pdf, attachments, subject):
    # 1. Save Companies File (Zero Redundancy check)
    comp_hash = get_file_hash(companies_pdf)
    comp_ext = os.path.splitext(companies_pdf.name)[1]
    comp_filename = f"{comp_hash}{comp_ext}"

    companies_dir = os.path.join(settings.MEDIA_ROOT, 'companies')
    os.makedirs(companies_dir, exist_ok=True)
    comp_path = os.path.join(companies_dir, comp_filename)

    if not os.path.exists(comp_path):
        with open(comp_path, 'wb+') as dest:
            for chunk in companies_pdf.chunks():
                dest.write(chunk)
        companies_pdf.seek(0)

    # 2. Setup User's Base Folder Name
    first = user.first_name.strip().lower() if user.first_name else ""
    last = user.last_name.strip().lower() if user.last_name else ""

    if first and last:
        base_folder_name = f"{first}_{last}"
    elif user.email:
        base_folder_name = user.email.split('@')[0].replace('.', '_')
    else:
        base_folder_name = "user_campaign"

    campaigns_parent_dir = os.path.join(settings.MEDIA_ROOT, 'campaigns')
    os.makedirs(campaigns_parent_dir, exist_ok=True)

    # ALWAYS increment to create a new folder for each submission
    counter = 1
    while True:
        folder_name = f"{base_folder_name}_{counter}"
        campaign_path = os.path.join(campaigns_parent_dir, folder_name)

        if not os.path.exists(campaign_path):
            target_campaign_path = campaign_path
            break
        counter += 1

    # 3. Save New Campaign Files
    os.makedirs(target_campaign_path, exist_ok=True)

    # Save Subject!
    if subject:
        with open(os.path.join(target_campaign_path, "subject.txt"), "w", encoding="utf-8") as f:
            f.write(subject)

    # Save Resume
    if resume_pdf and getattr(resume_pdf, 'name', None):
        res_ext = os.path.splitext(resume_pdf.name)[1]
        res_path = os.path.join(target_campaign_path, f"resume{res_ext}")
        with open(res_path, 'wb+') as dest:
            for chunk in resume_pdf.chunks():
                dest.write(chunk)
        resume_pdf.seek(0)

    # Save Cover Letter
    if cover_letter_text:
        cl_path = os.path.join(target_campaign_path, "coverletter.txt")
        with open(cl_path, "w", encoding="utf-8") as f:
            f.write(cover_letter_text)

    # Save Attachments
    if attachments:
        for index, att in enumerate(attachments, start=1):
            if getattr(att, 'name', None):
                att_ext = os.path.splitext(att.name)[1]
                att_path = os.path.join(target_campaign_path, f"attachment_{index}{att_ext}")
                with open(att_path, 'wb+') as dest:
                    for chunk in att.chunks():
                        dest.write(chunk)
                att.seek(0)

    return target_campaign_path


def get_latest_campaign_path(user):
    """Finds the user's most recent campaign folder to auto-load data."""
    if not user.is_authenticated:
        return None

    first = user.first_name.strip().lower() if user.first_name else ""
    last = user.last_name.strip().lower() if user.last_name else ""

    if first and last:
        base_folder_name = f"{first}_{last}"
    elif user.email:
        base_folder_name = user.email.split('@')[0].replace('.', '_')
    else:
        return None

    campaigns_dir = os.path.join(settings.MEDIA_ROOT, 'campaigns')
    if not os.path.exists(campaigns_dir):
        return None

    highest_counter = 0
    latest_path = None

    for folder in os.listdir(campaigns_dir):
        if folder.startswith(base_folder_name):
            try:
                counter = int(folder.split('_')[-1])
                if counter > highest_counter:
                    highest_counter = counter
                    latest_path = os.path.join(campaigns_dir, folder)
            except ValueError:
                continue

    return latest_path