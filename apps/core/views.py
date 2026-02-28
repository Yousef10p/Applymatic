import os
import uuid
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from .forms import ApplyForm
from .utils import extract_leads_from_pdf, send_gmail_message, save_campaign_records, get_latest_campaign_path

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


def apply_view(request):
    is_auth = request.user.is_authenticated
    latest_campaign = get_latest_campaign_path(request.user) if is_auth else None

    if request.method == "POST":
        form = ApplyForm(request.POST, request.FILES)

        if not is_auth:
            form.fields['resume_pdf'].required = False
            form.fields['subject'].required = False
            form.fields['cover_letter'].required = False
            form.fields['attachments'].required = False
        elif latest_campaign:
            # If they have a previous campaign, the resume is optional
            form.fields['resume_pdf'].required = False

        if form.is_valid():
            companies_pdf = request.FILES.get("companies_pdf")

            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
            filename = fs.save(companies_pdf.name, companies_pdf)
            file_path = fs.path(filename)

            try:
                leads = extract_leads_from_pdf(file_path)
            except ValueError as e:
                return JsonResponse({"error": str(e)}, status=400)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

            if is_auth:
                # ----------------------------------------------------
                # AUTO-LOAD RESUME & ATTACHMENTS IF LEFT BLANK
                # ----------------------------------------------------
                resume_pdf = request.FILES.get("resume_pdf")
                opened_resume = None

                if not resume_pdf and latest_campaign:
                    # Look for any file starting with 'resume' in the old folder
                    for filename in os.listdir(latest_campaign):
                        if filename.startswith("resume"):
                            old_resume_path = os.path.join(latest_campaign, filename)
                            opened_resume = open(old_resume_path, 'rb')
                            resume_pdf = opened_resume
                            break

                extra_attachments = request.FILES.getlist("attachments")
                opened_attachments = []

                if not extra_attachments and latest_campaign:
                    # Find any files that start with "attachment_" in the old folder
                    for filename in os.listdir(latest_campaign):
                        if filename.startswith("attachment_"):
                            att_path = os.path.join(latest_campaign, filename)
                            opened_attachments.append(open(att_path, 'rb'))
                    extra_attachments = opened_attachments

                cover_letter = form.cleaned_data.get("cover_letter")
                subject = form.cleaned_data.get("subject")

                # Save the new configuration
                save_campaign_records(
                    user=request.user,
                    companies_pdf=companies_pdf,
                    cover_letter_text=cover_letter,
                    resume_pdf=resume_pdf,
                    attachments=extra_attachments,
                    subject=subject
                )

                user_credentials = request.user.googleoauthprofile.get_credentials()
                sent_count = 0

                for lead in leads:
                    personalized_body = cover_letter.replace("{company_name}", lead["company_name"])

                    if ENABLE_EMAIL_SENDING:
                        if not user_credentials:
                            return JsonResponse({"error": "Google OAuth credentials missing."}, status=403)

                        send_gmail_message(
                            credentials=user_credentials,
                            sender_email=request.user.email,
                            to_email=lead["email"],
                            subject=subject,
                            body_text=personalized_body,
                            resume_pdf=resume_pdf,
                            attachments=extra_attachments
                        )
                        sent_count += 1
                        time.sleep(1)
                    else:
                        print(f"[TEST MODE] Sent to: {lead['email']}")
                        print(f"[TEST MODE] Attachments count: {len(extra_attachments)}")
                        sent_count += 1

                # ----------------------------------------------------
                # CLEANUP: Close any auto-loaded files to prevent leaks
                # ----------------------------------------------------
                if opened_resume:
                    opened_resume.close()
                for att in opened_attachments:
                    att.close()

                if not ENABLE_EMAIL_SENDING:
                    return JsonResponse({"status": "test", "leads": leads})

                return render(request, "core/result.html", {
                    "status": "success", "sent_count": sent_count, "leads_count": len(leads)
                })

            return render(request, "core/result.html", {"status": "guest", "leads_count": len(leads)})

    else:
        # GET REQUEST: Auto-load text fields and find file names for the UI
        initial_data = {}
        previous_resume_name = None
        previous_attachments_count = 0

        if latest_campaign:
            # Load Cover Letter
            cl_path = os.path.join(latest_campaign, "coverletter.txt")
            if os.path.exists(cl_path):
                with open(cl_path, "r", encoding="utf-8") as f:
                    initial_data['cover_letter'] = f.read()

            # Load Subject
            subj_path = os.path.join(latest_campaign, "subject.txt")
            if os.path.exists(subj_path):
                with open(subj_path, "r", encoding="utf-8") as f:
                    initial_data['subject'] = f.read()

            # Find the names of the saved files for the UI badge
            for filename in os.listdir(latest_campaign):
                if filename.startswith("resume"):
                    previous_resume_name = filename
                elif filename.startswith("attachment_"):
                    previous_attachments_count += 1

        form = ApplyForm(initial=initial_data)

        if not is_auth:
            form.fields['resume_pdf'].required = False
            form.fields['subject'].required = False
            form.fields['cover_letter'].required = False
            form.fields['attachments'].required = False
        elif latest_campaign:
            # Let the HTML form know the files are optional because we have them saved
            form.fields['resume_pdf'].required = False

    return render(request, "core/apply.html", {
        "form": form,
        "has_previous_campaign": bool(latest_campaign),
        "previous_resume_name": previous_resume_name,
        "previous_attachments_count": previous_attachments_count
    })