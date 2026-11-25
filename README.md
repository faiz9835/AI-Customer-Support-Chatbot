# AI Customer Support Chatbot for Small Businesses

A runnable Flask + SQLite full-stack academic project. It includes customer registration/login, FAQ knowledge base, a chatbot API, stored conversations, feedback, and an admin dashboard.

## Requirements
- Windows 10/11
- Python 3.10 or newer
- Internet for the first-time Flask installation

## Run on Windows
1. Extract this ZIP.
2. Open the extracted folder in VS Code.
3. Double-click `run_windows.bat`, OR open VS Code terminal in this folder and run:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

4. Open `http://127.0.0.1:5000` in your browser.

If PowerShell blocks activation, use Command Prompt terminal and run:
`venv\Scripts\activate.bat`

## Demo admin account
- Email: `admin@demo.com`
- Password: `Admin@123`

Change this password and `SECRET_KEY` before any public deployment. This is a local academic demo, not a production-ready service.

## Features to demonstrate
1. Register a customer account and sign in.
2. Open Chat Assistant and ask about business hours, delivery, refunds, support, or order tracking.
3. Open Admin Login and use the demo credentials.
4. Dashboard shows users, FAQs, conversations, and feedback counts.
5. FAQ Manager lets admin add/delete knowledge-base entries.
6. Conversations page shows stored chat history.
7. Customer can submit Helpful / Not Helpful feedback.

## How the chatbot works
The `/api/chat` endpoint stores the customer's message in SQLite, searches the business FAQ knowledge base using simple token similarity, returns the best matching answer, and stores the bot reply. This offline FAQ retrieval makes the demo work without an external API key. For a real AI/LLM integration, connect a provider securely on the server and add its key as an environment variable; never put API keys in frontend JavaScript.

## Database
SQLite database `chatbot.db` is automatically created on first run. Tables: `users`, `faqs`, `conversations`, `messages`, `feedback`.

## Project structure
```
app.py
requirements.txt
run_windows.bat
chatbot.db             # generated automatically on first run
templates/
  base.html
  index.html
  auth.html
  chat.html
  admin.html
  faqs.html
  conversations.html
  conversation_detail.html
static/
  style.css
  app.js
```
