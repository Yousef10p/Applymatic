import os
import re
import io
import hashlib
from django.conf import settings
import tldextract
import pdfplumber
from email.message import EmailMessage
import base64
import mimetypes

# Google API Imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# 1. Extraction & Email Utils (Unchanged)
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
            resume_pdf.read(), maintype='application', subtype='pdf', filename=resume_pdf.name
        )

    if attachments:
        for file in attachments:
            file.seek(0)
            ctype, _ = mimetypes.guess_type(file.name)
            if ctype is None: ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            message.add_attachment(
                file.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(file.name)
            )

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'raw': encoded_message}

    service = build('gmail', 'v1', credentials=credentials)
    try:
        return service.users().messages().send(userId="me", body=create_message).execute()
    except Exception as e:
        print(f"Error sending to {to_email}: {e}")
        return None

# ==========================================
# 2. Google Drive Storage Utils
# ==========================================

def get_drive_service():
    """Initializes the connection to the Google Drive bot."""
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_APPLICATION_CREDENTIALS, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def get_or_create_drive_folder(service, folder_name, parent_id):
    """Finds a folder in Drive, or creates it if it doesn't exist."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    
    metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    return service.files().create(body=metadata, fields='id').execute().get('id')

def get_file_hash(file_obj):
    hasher = hashlib.sha256()
    file_obj.seek(0)
    for chunk in file_obj.chunks(): hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()

def save_campaign_records(user, companies_pdf, cover_letter_text, resume_pdf, attachments, subject):
    service = get_drive_service()
    master_folder_id = settings.GOOGLE_DRIVE_FOLDER_ID # You must add this to settings.py!

    # 1. Save Companies File (Check if hash already exists in Drive)
    companies_folder_id = get_or_create_drive_folder(service, 'companies', master_folder_id)
    comp_hash = get_file_hash(companies_pdf)
    comp_ext = os.path.splitext(companies_pdf.name)[1]
    comp_filename = f"{comp_hash}{comp_ext}"

    query = f"name='{comp_filename}' and '{companies_folder_id}' in parents and trashed=false"
    existing_comp = service.files().list(q=query, fields='files(id)').execute().get('files', [])
    
    if not existing_comp:
        companies_pdf.seek(0)
        media = MediaIoBaseUpload(companies_pdf, mimetype='application/pdf', resumable=True)
        service.files().create(body={'name': comp_filename, 'parents': [companies_folder_id]}, media_body=media).execute()

    # 2. Setup User's Base Folder Name
    campaigns_folder_id = get_or_create_drive_folder(service, 'campaigns', master_folder_id)
    first = user.first_name.strip().lower() if user.first_name else ""
    last = user.last_name.strip().lower() if user.last_name else ""
    base_folder_name = f"{first}_{last}" if first and last else (user.email.split('@')[0].replace('.', '_') if user.email else "user_campaign")

    # Increment folder counter logic in Drive
    query = f"name contains '{base_folder_name}_' and mimeType='application/vnd.google-apps.folder' and '{campaigns_folder_id}' in parents and trashed=false"
    existing_campaigns = service.files().list(q=query, fields='files(name)').execute().get('files', [])

    highest_counter = 0
    for item in existing_campaigns:
        try:
            counter = int(item['name'].split('_')[-1])
            if counter > highest_counter: highest_counter = counter
        except ValueError:
            continue

    target_campaign_id = get_or_create_drive_folder(service, f"{base_folder_name}_{highest_counter + 1}", campaigns_folder_id)

    # 3. Save New Campaign Files
    def upload_text(filename, content):
        if not content: return
        file_obj = io.BytesIO(content.encode('utf-8'))
        media = MediaIoBaseUpload(file_obj, mimetype='text/plain', resumable=True)
        service.files().create(body={'name': filename, 'parents': [target_campaign_id]}, media_body=media).execute()

    def upload_media(filename, file_obj):
        if not file_obj or not getattr(file_obj, 'name', None): return
        file_obj.seek(0)
        ctype, _ = mimetypes.guess_type(file_obj.name)
        media = MediaIoBaseUpload(file_obj, mimetype=ctype or 'application/octet-stream', resumable=True)
        service.files().create(body={'name': filename, 'parents': [target_campaign_id]}, media_body=media).execute()

    upload_text('subject.txt', subject)
    upload_text('coverletter.txt', cover_letter_text)
    
    if resume_pdf:
        res_ext = os.path.splitext(resume_pdf.name)[1]
        upload_media(f"resume{res_ext}", resume_pdf)

    if attachments:
        for index, att in enumerate(attachments, start=1):
            att_ext = os.path.splitext(att.name)[1]
            upload_media(f"attachment_{index}{att_ext}", att)

    return target_campaign_id

def get_latest_campaign_path(user):
    """Returns the Google Drive Folder ID of the most recent campaign."""
    if not user.is_authenticated: return None

    service = get_drive_service()
    master_folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    
    query = f"name='campaigns' and mimeType='application/vnd.google-apps.folder' and '{master_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields='files(id)').execute().get('files', [])
    if not results: return None
    campaigns_folder_id = results[0]['id']

    first = user.first_name.strip().lower() if user.first_name else ""
    last = user.last_name.strip().lower() if user.last_name else ""
    base_folder_name = f"{first}_{last}" if first and last else (user.email.split('@')[0].replace('.', '_') if user.email else "user_campaign")

    query = f"name contains '{base_folder_name}_' and mimeType='application/vnd.google-apps.folder' and '{campaigns_folder_id}' in parents and trashed=false"
    existing_campaigns = service.files().list(q=query, fields='files(id, name)').execute().get('files', [])

    highest_counter = 0
    latest_id = None

    for item in existing_campaigns:
        try:
            counter = int(item['name'].split('_')[-1])
            if counter >= highest_counter:
                highest_counter = counter
                latest_id = item['id']
        except ValueError:
            continue

    return latest_id