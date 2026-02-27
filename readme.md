# Applymatic — Project README (V1)

## Overview

Applymatic is a Django-based semi-automated job application engine designed to simplify large-scale outreach for CO-OP and job applications.

The system allows users to upload an unstructured PDF containing company contact information, automatically extract email addresses, infer company names, and send personalized application emails directly from their own Gmail account.

---

## Core Features

- Upload unstructured PDF files containing company emails  
- Automatically extract valid email addresses  
- Infer company names from email domains  
- Personalize cover letters using a `{company_name}` placeholder  
- Attach resume and optional supporting documents  
- Send emails securely through Gmail API  
- Guest mode for testing extraction without sending emails  
- Developer dry-run mode for safe testing  

---

## Tech Stack

- **Backend:** Django 5.x  
- **Language:** Python 3.13  
- **Database:** SQLite (development)  
- **Frontend:** Django Templates + Bootstrap 5  
- **PDF Parsing:** pdfplumber  
- **Domain Parsing:** tldextract  
- **Email Sending:** Gmail API  

---

## Authentication

Applymatic uses **Google OAuth 2.0** instead of traditional passwords.

- Users log in with Google  
- Gmail send permission is required  
- Access and refresh tokens are securely stored  
- Logout is handled via POST for CSRF protection  

---

## How It Works

1. User logs in with Google (or continues as Guest).
2. User uploads a PDF containing company contact emails.
3. The system extracts emails and infers company names.
4. User provides subject line, cover letter, and resume.
5. Emails are personalized and sent through Gmail API.
6. A results page confirms how many emails were processed or sent.

---

## Guest Mode

Guest users can:

- Upload and parse PDFs  
- View extracted leads  

Guest users cannot:

- Send emails  
- Upload resumes or attachments  

---

## Developer Mode

A configuration toggle allows:

- Dry-run testing (no real emails sent)  
- Console preview of personalized messages  
- Safe local development  

---

## Project Structure
```
applymatic/
├── config/
├── apps/
│ ├── accounts/
│ ├── core/
│ ├── applications/ (future)
│ ├── companies/ (future)
├── media/
├── templates/
```


---

## Purpose

Applymatic reduces repetitive manual emailing during job applications by automating extraction and personalized outreach — while keeping users in control of their own email account.

---

Built to streamline outreach.  
Designed for scalability.