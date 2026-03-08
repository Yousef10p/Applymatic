import os
import io
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from .forms import ApplyForm
from .utils import extract_leads, send_gmail_message, save_campaign_records, get_latest_campaign_path, get_drive_service, extract_text_from_document
from googleapiclient.http import MediaIoBaseDownload

ENABLE_EMAIL_SENDING = True

def landing_view(request):
    return render(request, "core/landing.html")

# --- Google Drive Download Helpers ---
def get_text_from_drive(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    return fh.getvalue().decode('utf-8')

def get_file_from_drive(service, file_id, filename):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    fh.seek(0)
    fh.name = filename 
    return fh
# --------------------------------------

# ==========================================
# VIEW 1: AUTHENTICATED CAMPAIGN MANAGER
# ==========================================
def apply_view(request):
    if not request.user.is_authenticated:
        return redirect("core:landing")

    latest_campaign = get_latest_campaign_path(request.user)
    drive_service = get_drive_service() if latest_campaign else None
    drive_files = {} 
    
    if drive_service and latest_campaign:
        query = f"'{latest_campaign}' in parents and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        for f in results.get('files', []):
            drive_files[f['name']] = f['id']

    if request.method == "POST":
        action = request.POST.get("action")
        
        # ==========================================
        # AI INTERCEPTORS (Bypasses Form Validation)
        # ==========================================
        if action == "generate_cover_letter":
            resume_pdf = request.FILES.get("resume_pdf")
            file_path = None
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
            
            try:
                # 1. Prioritize newly uploaded resume
                if resume_pdf:
                    filename = fs.save(resume_pdf.name, resume_pdf)
                    file_path = fs.path(filename)
                    
                # 2. Fallback to Drive resume
                elif drive_files:
                    for name, f_id in drive_files.items():
                        if name.startswith("resume"):
                            opened_resume = get_file_from_drive(drive_service, f_id, name)
                            filename = fs.get_available_name(name)
                            file_path = fs.path(filename)
                            with open(file_path, 'wb') as f:
                                f.write(opened_resume.getvalue())
                            opened_resume.close()
                            break
                            
                if not file_path:
                    return JsonResponse({"error": "No resume uploaded, and no previous resume found in your Google Drive."}, status=400)
                    
                # Extract text and send to AI
                resume_text = extract_text_from_document(file_path)
                from apps.AI.main import ApplymaticAI
                ai = ApplymaticAI()
                generated_text = ai.generate_cover_letter(resume_text)
                
                return JsonResponse({"status": "success", "cover_letter": generated_text})
                
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)
            finally:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    
        elif action == "refine_cover_letter":
            current_text = request.POST.get("current_cover_letter", "").strip()
            if not current_text:
                return JsonResponse({"error": "Your cover letter is empty! Please write something or generate one first."}, status=400)
                
            try:
                from apps.AI.main import ApplymaticAI
                ai = ApplymaticAI()
                refined_text = ai.refine_cover_letter(current_text)
                return JsonResponse({"status": "success", "cover_letter": refined_text})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)

        # ==========================================
        # STANDARD FORM ACTIONS (Extract & Send)
        # ==========================================
        form = ApplyForm(request.POST, request.FILES)

        if latest_campaign:
            form.fields['resume_pdf'].required = False

        if form.is_valid():
            # ACTION 1: EXTRACT
            if action == "extract":
                companies_file = request.FILES.get("companies_file")
                manual_text = form.cleaned_data.get("manual_leads_text", "")
                
                file_path = None
                if companies_file:
                    fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
                    filename = fs.save(companies_file.name, companies_file)
                    file_path = fs.path(filename)

                try:
                    leads = extract_leads(file_path=file_path, manual_text=manual_text)
                    if not leads:
                        return JsonResponse({"error": "Could not find any valid email addresses in the provided file/text."}, status=400)
                    
                    request.session['extracted_leads'] = leads 
                    return JsonResponse({"count": len(leads), "leads": leads})
                except ValueError as e:
                    return JsonResponse({"error": str(e)}, status=400)
                finally:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)

            # ACTION 2: SEND EMAILS
            elif action == "send":
                leads = request.session.get('extracted_leads', [])
                if not leads:
                    return JsonResponse({"error": "No leads found to send."}, status=400)

                resume_pdf = request.FILES.get("resume_pdf")
                opened_resume = None

                if not resume_pdf and drive_files:
                    for name, f_id in drive_files.items():
                        if name.startswith("resume"):
                            opened_resume = get_file_from_drive(drive_service, f_id, name)
                            resume_pdf = opened_resume
                            break

                extra_attachments = request.FILES.getlist("attachments")
                opened_attachments = []

                if not extra_attachments and drive_files:
                    for name, f_id in drive_files.items():
                        if name.startswith("attachment_"):
                            opened_attachments.append(get_file_from_drive(drive_service, f_id, name))
                    extra_attachments = opened_attachments

                cover_letter = form.cleaned_data.get("cover_letter")
                subject = form.cleaned_data.get("subject")
                companies_file = request.FILES.get("companies_file")

                save_campaign_records(
                    user=request.user, companies_file=companies_file,
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

                if opened_resume: opened_resume.close()
                for att in opened_attachments: att.close()

                return JsonResponse({"status": "success", "sent_count": sent_count})

        return JsonResponse({"error": "Form validation failed."}, status=400)

    # GET REQUEST
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
    if latest_campaign: form.fields['resume_pdf'].required = False

    return render(request, "core/apply.html", {
        "form": form, "has_previous_campaign": bool(latest_campaign),
        "previous_resume_name": previous_resume_name, "previous_attachments_count": previous_attachments_count
    })

# ==========================================
# VIEW 2: GUEST EXTRACTION TESTER
# ==========================================
def guest_extract_view(request):
    if request.method == "POST":
        form = ApplyForm(request.POST, request.FILES)
        
        # Turn off all email requirements for testing
        form.fields['resume_pdf'].required = False
        form.fields['subject'].required = False
        form.fields['cover_letter'].required = False

        if form.is_valid():
            companies_file = request.FILES.get("companies_file")
            manual_text = form.cleaned_data.get("manual_leads_text", "")
            
            file_path = None
            if companies_file:
                fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
                filename = fs.save(companies_file.name, companies_file)
                file_path = fs.path(filename)

            try:
                leads = extract_leads(file_path=file_path, manual_text=manual_text)
                if not leads:
                    return JsonResponse({"error": "Could not find any valid email addresses in the provided file/text."}, status=400)
                
                return JsonResponse({"count": len(leads), "leads": leads})
            except ValueError as e:
                return JsonResponse({"error": str(e)}, status=400)
            finally:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

        return JsonResponse({"error": "Form validation failed."}, status=400)

    # GET REQUEST
    form = ApplyForm()
    form.fields['resume_pdf'].required = False
    form.fields['subject'].required = False
    form.fields['cover_letter'].required = False

    return render(request, "core/guest_extract.html", {"form": form})