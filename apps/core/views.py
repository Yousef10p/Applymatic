import os
import io
import uuid
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from .forms import ApplyForm
from .utils import extract_leads_from_pdf, send_gmail_message, save_campaign_records, get_latest_campaign_path, get_drive_service
from googleapiclient.http import MediaIoBaseDownload

# ==========================================
# DEVELOPER TOGGLE
# ==========================================
ENABLE_EMAIL_SENDING = True

def landing_view(request):
    return render(request, "core/landing.html")

def start_guest(request):
    if not request.session.get("applymatic_guest_id"):
        request.session["applymatic_guest_id"] = str(uuid.uuid4())
    return redirect("core:apply")

# --- Google Drive Download Helpers ---
def get_text_from_drive(service, file_id):
    """Downloads text files (subject, cover letter) from Drive to memory."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue().decode('utf-8')

def get_file_from_drive(service, file_id, filename):
    """Downloads PDFs/Attachments from Drive to memory so they can be emailed."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    fh.name = filename # Spoof the filename so the email sender knows what to call it
    return fh
# --------------------------------------

def apply_view(request):
    is_auth = request.user.is_authenticated
    latest_campaign = get_latest_campaign_path(request.user) if is_auth else None
    
    # 1. PRE-FETCH GOOGLE DRIVE FILES (If user has a previous campaign)
    drive_service = get_drive_service() if (is_auth and latest_campaign) else None
    drive_files = {} # Dictionary to hold { "resume.pdf": "file_id_123" }
    
    if drive_service and latest_campaign:
        query = f"'{latest_campaign}' in parents and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        for f in results.get('files', []):
            drive_files[f['name']] = f['id']

    if request.method == "POST":
        action = request.POST.get("action")
        form = ApplyForm(request.POST, request.FILES)

        if not is_auth:
            form.fields['resume_pdf'].required = False
            form.fields['subject'].required = False
            form.fields['cover_letter'].required = False
            form.fields['attachments'].required = False
        elif latest_campaign:
            form.fields['resume_pdf'].required = False

        if form.is_valid():
            # ==========================================
            # ACTION 1: EXTRACT ONLY (Guest & Auth)
            # ==========================================
            if action == "extract":
                companies_pdf = request.FILES.get("companies_pdf")
                fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
                filename = fs.save(companies_pdf.name, companies_pdf)
                file_path = fs.path(filename)

                try:
                    leads = extract_leads_from_pdf(file_path)
                    request.session['extracted_leads'] = leads 
                    return JsonResponse({"count": len(leads), "leads": leads})
                except ValueError as e:
                    return JsonResponse({"error": str(e)}, status=400)
                finally:
                    if os.path.exists(file_path):
                        os.remove(file_path)

            # ==========================================
            # ACTION 2: SEND EMAILS (Auth Only)
            # ==========================================
            elif action == "send" and is_auth:
                leads = request.session.get('extracted_leads', [])
                if not leads:
                    return JsonResponse({"error": "No leads found to send."}, status=400)

                resume_pdf = request.FILES.get("resume_pdf")
                opened_resume = None

                # Fetch Resume from Drive if left blank
                if not resume_pdf and drive_files:
                    for name, f_id in drive_files.items():
                        if name.startswith("resume"):
                            opened_resume = get_file_from_drive(drive_service, f_id, name)
                            resume_pdf = opened_resume
                            break

                extra_attachments = request.FILES.getlist("attachments")
                opened_attachments = []

                # Fetch Attachments from Drive if left blank
                if not extra_attachments and drive_files:
                    for name, f_id in drive_files.items():
                        if name.startswith("attachment_"):
                            opened_attachments.append(get_file_from_drive(drive_service, f_id, name))
                    extra_attachments = opened_attachments

                cover_letter = form.cleaned_data.get("cover_letter")
                subject = form.cleaned_data.get("subject")

                save_campaign_records(
                    user=request.user, companies_pdf=request.FILES.get("companies_pdf"),
                    cover_letter_text=cover_letter, resume_pdf=resume_pdf,
                    attachments=extra_attachments, subject=subject
                )

                user_credentials = request.user.googleoauthprofile.get_credentials()
                sent_count = 0

                for lead in leads:
                    personalized_body = cover_letter.replace("{company_name}", lead["company_name"])

                    if ENABLE_EMAIL_SENDING:
                        if not user_credentials:
                            return JsonResponse({"error": "Google OAuth credentials missing."}, status=403)

                        send_gmail_message(
                            credentials=user_credentials, sender_email=request.user.email,
                            to_email=lead["email"], subject=subject,
                            body_text=personalized_body, resume_pdf=resume_pdf,
                            attachments=extra_attachments
                        )
                        sent_count += 1
                        time.sleep(1)
                    else:
                        print(f"[TEST MODE] Sent to: {lead['email']}")
                        sent_count += 1

                # Cleanup
                if opened_resume: opened_resume.close()
                for att in opened_attachments: att.close()

                return JsonResponse({"status": "success", "sent_count": sent_count})

        return JsonResponse({"error": "Form validation failed."}, status=400)

    # ==========================================
    # GET REQUEST: Auto-fill from Google Drive
    # ==========================================
    initial_data = {}
    previous_resume_name = None
    previous_attachments_count = 0

    if drive_files:
        if 'coverletter.txt' in drive_files:
            initial_data['cover_letter'] = get_text_from_drive(drive_service, drive_files['coverletter.txt'])
        if 'subject.txt' in drive_files:
            initial_data['subject'] = get_text_from_drive(drive_service, drive_files['subject.txt'])

        for name in drive_files.keys():
            if name.startswith("resume"): previous_resume_name = name
            elif name.startswith("attachment_"): previous_attachments_count += 1

    form = ApplyForm(initial=initial_data)

    if not is_auth:
        form.fields['resume_pdf'].required = False
        form.fields['subject'].required = False
        form.fields['cover_letter'].required = False
        form.fields['attachments'].required = False
    elif latest_campaign:
        form.fields['resume_pdf'].required = False

    return render(request, "core/apply.html", {
        "form": form, "has_previous_campaign": bool(latest_campaign),
        "previous_resume_name": previous_resume_name, "previous_attachments_count": previous_attachments_count
    })