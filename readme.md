# Applymatic

> **Automated job application outreach — upload your leads, extract contacts, send personalized emails.**

Applymatic is a Django-powered web application that streamlines CO-OP and job application outreach at scale. Instead of manually hunting for company emails and crafting individual messages, Applymatic lets you upload a leads file (or paste raw text), automatically extracts email addresses and infers company names, then sends personalized cover letter emails through your own Gmail account — all in a few clicks.

🌐 **Live at:** [applymatic-ya.up.railway.app](https://applymatic-ya.up.railway.app/)

---

## Features

- 📄 **Multi-Format Lead Extraction** — Upload PDFs, Word Docs (`.docx`), Excel Sheets (`.xlsx`), or plain TXT files; Applymatic pulls out all valid email addresses automatically.
- 📋 **Manual Text Paste** — Skip file uploads entirely and paste raw text directly into the input box to extract emails instantly.
- 🔀 **Smart Merging** — Use a file and the text box simultaneously; Applymatic merges both sources into one consolidated lead list.
- 🏢 **Smart Company Inference** — Company names are inferred from email domains, so you don't need a clean or formatted contact list.
- ✉️ **Personalized Outreach** — Write your cover letter once with a `{company_name}` placeholder; Applymatic personalizes each email before sending.
- 🤖 **AI-Powered Cover Letters** — Upload your CV and let the LLM generate a cover letter for you from scratch, or supply your own draft and have the LLM refine and improve it — your choice.
- 📎 **Resume & Attachment Support** — Attach your resume and any supporting documents to every outgoing email.
- 🔐 **Google OAuth 2.0 Login** — Sign in with Google; emails are sent directly through your own Gmail account via the Gmail API — no third-party SMTP required.
- 👤 **Guest Mode** — Try the extraction and lead preview without signing in or sending any emails.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 5.x |
| Language | Python 3.13 |
| Database (dev) | SQLite |
| Database (prod) | PostgreSQL |
| Frontend | HTML + Bootstrap 5 + JS |
| Email Sending | Gmail API (OAuth 2.0) |
| Background Tasks | Celery + Redis |
| Auth | Google OAuth 2.0 |

---

## Project Structure

```
Applymatic/
├── applymatic/           # Django project config (settings, urls, wsgi)
├── apps/
│   ├── accounts/         # Google OAuth login, user model, token storage
│   ├── core/             # File upload, email extraction, sending logic
│   ├── applications/     # (planned) Application tracking
│   └── companies/        # (planned) Company management
├── templates/            # HTML templates
├── media/                # Uploaded resumes and attachments
├── manage.py
├── requirements.txt
└── .gitignore
```

---

## How It Works

```
1. Login with Google         →  Gmail send permission granted
2. Upload file / paste text  →  Emails extracted, company names inferred
3. Cover letter              →  Generate from your CV using AI, write manually,
                                or paste a draft and let AI refine it
4. Attach resume             →  Optional supporting documents too
5. Send                      →  Personalized emails dispatched via Gmail API
6. Results page              →  See how many emails were sent / processed
```

---

## Guest Mode

Guests can upload files or paste text and preview extracted leads — no account or email sending required. To actually send emails, sign in with Google.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

---

## Author

Built by **Yousef** — [Connect on LinkedIn](https://www.linkedin.com/in/yousef-alogiely-29389b283/)

---

> Built to streamline outreach. Designed for scalability.


