import os
import uuid
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from .forms import ApplyForm
from .utils import extract_leads_from_pdf, send_gmail_message

# ==========================================
# DEVELOPER TOGGLE
# False = Returns JSON of extracted companies (Test Mode)
# True = Sends emails via Gmail API & renders Success HTML
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

    if request.method == "POST":
        form = ApplyForm(request.POST, request.FILES)

        # Enforce rule: Guests don't need to provide email assets
        if not is_auth:
            form.fields['resume_pdf'].required = False
            form.fields['subject'].required = False
            form.fields['cover_letter'].required = False
            form.fields['attachments'].required = False

        if form.is_valid():
            companies_pdf = request.FILES.get("companies_pdf")

            # Save PDF temporarily to parse it
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
                resume_pdf = request.FILES.get("resume_pdf")
                cover_letter = form.cleaned_data.get("cover_letter")
                subject = form.cleaned_data.get("subject")
                extra_attachments = request.FILES.getlist("attachments")

                user_credentials = request.user.googleoauthprofile.get_credentials()

                sent_count = 0
                for lead in leads:
                    # Inject personalized company name into the cover letter
                    personalized_body = cover_letter.replace("{company_name}", lead["company_name"])

                    if ENABLE_EMAIL_SENDING:
                        if not user_credentials:
                            return JsonResponse({
                                "error": "Cannot send emails. Google OAuth credentials missing."
                            }, status=403)

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
                        # Rate limit protection
                        time.sleep(0.2)
                    else:
                        # DRY RUN: Print to console for debugging
                        print(f"\n[TEST MODE] Would send to: {lead['email']}")
                        print(f"[TEST MODE] Subject: {subject}")
                        print(f"[TEST MODE] Body Preview: {personalized_body[:60]}...")
                        sent_count += 1

                # If we are strictly testing, return the JSON to inspect the companies
                if not ENABLE_EMAIL_SENDING:
                    return JsonResponse({
                        "status": "success",
                        "mode": "test",
                        "message": f"Test mode. Extracted {len(leads)} leads. Emails printed to console.",
                        "leads_count": len(leads),
                        "leads": leads
                    })

                # If we actually sent the emails, render the beautiful success page
                context = {
                    "status": "success",
                    "sent_count": sent_count,
                    "leads_count": len(leads),
                    "test_mode": False,
                    "leads": leads,
                }
                return render(request, "core/result.html", context)

            # Guest response (cannot send emails, so we just show the extracted data)
            context = {
                "status": "guest",
                "leads_count": len(leads),
                "leads": leads,
            }
            return render(request, "core/result.html", context)

    else:
        form = ApplyForm()
        if not is_auth:
            form.fields['resume_pdf'].required = False
            form.fields['subject'].required = False
            form.fields['cover_letter'].required = False
            form.fields['attachments'].required = False

    return render(request, "core/apply.html", {"form": form})