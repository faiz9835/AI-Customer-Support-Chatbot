import os, sqlite3, re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "chatbot.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS faqs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL, answer TEXT NOT NULL,
            category TEXT DEFAULT 'General', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, visitor_name TEXT DEFAULT 'Guest',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL, sender TEXT NOT NULL,
            message TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL, rating TEXT NOT NULL,
            comment TEXT DEFAULT '', created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        """)
        owner_email = os.getenv("OWNER_EMAIL", "faizakhtar567@gmail.com")
owner_password = os.getenv("OWNER_PASSWORD")

admin = con.execute(
    "SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1"
).fetchone()

if admin:
    if owner_password:
        con.execute(
            "UPDATE users SET name=?, email=?, password=? WHERE id=?",
            ("Faiz Akhtar", owner_email,
             generate_password_hash(owner_password), admin["id"])
        )
    else:
        con.execute(
            "UPDATE users SET name=?, email=? WHERE id=?",
            ("Faiz Akhtar", owner_email, admin["id"])
        )
elif owner_password:
    con.execute(
        "INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
        ("Faiz Akhtar", owner_email,
         generate_password_hash(owner_password), "admin",
         datetime.now().isoformat(timespec="seconds"))
    )
        count = con.execute("SELECT COUNT(*) AS n FROM faqs").fetchone()["n"]
        if count == 0:
            samples = [
                ("What are your business hours?", "Our support team is available Monday to Saturday, 9 AM to 6 PM.", "Business hours"),
                ("How can I contact support?", "You can contact our support team through the contact form. Our team will assist you as soon as possible.", "Support"),
                ("What is your refund policy?", "Eligible purchases can be returned within 7 days. Please keep your order details ready.", "Returns"),
                ("How long does delivery take?", "Standard delivery usually takes 3–5 working days, depending on your location.", "Delivery"),
                ("How can I track my order?", "Please sign in and open the Orders section to view your latest order status.", "Orders")
            ]
            con.executemany("INSERT INTO faqs(question,answer,category,created_at) VALUES(?,?,?,?)",
                [(q,a,c,datetime.now().isoformat(timespec="seconds")) for q,a,c in samples])

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access is required.", "danger")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def best_faq_reply(question):
    """Simple local FAQ matching so the demo works without a paid API key."""
    words = set(re.findall(r"[a-z0-9]+", question.lower()))
    stop = {"the","is","are","a","an","how","what","can","i","you","your","do","to","for","my","me","please","and","of","in"}
    words -= stop
    with db() as con:
        rows = con.execute("SELECT question,answer FROM faqs").fetchall()
    best, best_score = None, 0
    for row in rows:
        faq_words = set(re.findall(r"[a-z0-9]+", row["question"].lower())) - stop
        score = len(words & faq_words) / max(1, len(words | faq_words))
        if score > best_score:
            best, best_score = row, score
    if best and best_score >= 0.12:
        return best["answer"]
    return ("Thanks for your question! I couldn't find an exact answer in the business knowledge base. "
            "Please share a little more detail or contact the business support team. "
            "An administrator can add this question to the FAQs.")

@app.route("/")
def index():
    with db() as con:
        faqs = con.execute("SELECT * FROM faqs ORDER BY id DESC LIMIT 6").fetchall()
    return render_template("index.html", faqs=faqs)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or len(password) < 6:
            flash("Enter all details. Password must be at least 6 characters.", "danger")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                        (name,email,generate_password_hash(password),"customer",datetime.now().isoformat(timespec="seconds")))
                flash("Account created. Please sign in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("This email is already registered.", "danger")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            return redirect(url_for("admin_dashboard") if user["role"]=="admin" else url_for("chat"))
        flash("Invalid email or password.", "danger")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))

@app.route("/chat")
def chat():
    return render_template("chat.html")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")

    if not message:
        return jsonify(error="Please type a message."), 400

    if len(message) > 1500:
        return jsonify(error="Message is too long."), 400

    with db() as con:
        if conversation_id:
            conv = con.execute(
                "SELECT id FROM conversations WHERE id=?",
                (conversation_id,)
            ).fetchone()
        else:
            conv = None

        if not conv:
            cur = con.execute(
                """INSERT INTO conversations
                (user_id,visitor_name,created_at) VALUES(?,?,?)""",
                (
                    session.get("user_id"),
                    session.get("name", "Guest"),
                    datetime.now().isoformat(timespec="seconds")
                )
            )
            conversation_id = cur.lastrowid

        con.execute(
            """INSERT INTO messages
            (conversation_id,sender,message,created_at)
            VALUES(?,?,?,?)""",
            (
                conversation_id,
                "customer",
                message,
                datetime.now().isoformat(timespec="seconds")
            )
        )

    if client:
        try:
            with db() as con:
                history = con.execute(
                    """SELECT sender, message FROM messages
                    WHERE conversation_id=?
                    ORDER BY id DESC LIMIT 12""",
                    (conversation_id,)
                ).fetchall()

            history.reverse()
            # Load business knowledge from FAQ database
            with db() as con:
                faqs = con.execute(
                    "SELECT question, answer, category FROM faqs"
                ).fetchall()

            faq_context = ""
            for faq in faqs:
                faq_context += (
                    f"Category: {faq['category']}\n"
                    f"Question: {faq['question']}\n"
                    f"Answer: {faq['answer']}\n\n"
                )
            conversation = ""
            for item in history:
                role = "Customer" if item["sender"] == "customer" else "Assistant"
                conversation += f"{role}: {item['message']}\n"

            conversation += f"{role}: {item['message']}\n"

            prompt = f"""
You are an intelligent and professional AI customer support assistant.

BUSINESS KNOWLEDGE:
{faq_context}

CONVERSATION HISTORY:
{conversation}

INSTRUCTIONS:
1. Answer customer questions naturally and politely.
2. Use business knowledge whenever relevant.
3. Understand follow-up questions using conversation history.
4. Answer general questions using your knowledge.
5. Never invent business prices, policies or product details.
6. If business information is missing, honestly tell the customer.
7. Support English and Hindi.
8. Keep answers clear and helpful.

Reply to the latest customer message.
"""

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

            reply = response.text or "Sorry, please try again."

        except Exception as e:
            print("Gemini API Error:", str(e))
            reply = best_faq_reply(message)

    else:
        reply = best_faq_reply(message)

    with db() as con:
        con.execute(
            """INSERT INTO messages
            (conversation_id,sender,message,created_at)
            VALUES(?,?,?,?)""",
            (
                conversation_id,
                "bot",
                reply,
                datetime.now().isoformat(timespec="seconds")
            )
        )

    return jsonify(reply=reply, conversation_id=conversation_id)
@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json(silent=True) or {}
    try:
        cid = int(data.get("conversation_id"))
    except (TypeError, ValueError):
        return jsonify(error="No conversation found."), 400
    rating = data.get("rating")
    if rating not in ("helpful","not-helpful"):
        return jsonify(error="Invalid feedback."), 400
    with db() as con:
        exists = con.execute("SELECT id FROM conversations WHERE id=?", (cid,)).fetchone()
        if not exists:
            return jsonify(error="Conversation not found."), 404
        con.execute("INSERT INTO feedback(conversation_id,rating,comment,created_at) VALUES(?,?,?,?)",
            (cid,rating,(data.get("comment") or "")[:500],datetime.now().isoformat(timespec="seconds")))
    return jsonify(message="Thank you for your feedback!")

@app.route("/admin")
@admin_required
def admin_dashboard():
    with db() as con:
        stats = {
            "users": con.execute("SELECT COUNT(*) n FROM users WHERE role='customer'").fetchone()["n"],
            "faqs": con.execute("SELECT COUNT(*) n FROM faqs").fetchone()["n"],
            "chats": con.execute("SELECT COUNT(*) n FROM conversations").fetchone()["n"],
            "feedback": con.execute("SELECT COUNT(*) n FROM feedback").fetchone()["n"]
        }
        recent = con.execute("""SELECT c.id,c.visitor_name,c.created_at,
            (SELECT message FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) last_message
            FROM conversations c ORDER BY c.id DESC LIMIT 8""").fetchall()
    return render_template("admin.html", stats=stats, recent=recent)

@app.route("/admin/faqs", methods=["GET","POST"])
@admin_required
def manage_faqs():
    if request.method == "POST":
        q=request.form.get("question","").strip(); a=request.form.get("answer","").strip(); cat=request.form.get("category","General").strip()
        if q and a:
            with db() as con:
                con.execute("INSERT INTO faqs(question,answer,category,created_at) VALUES(?,?,?,?)",
                    (q,a,cat or "General",datetime.now().isoformat(timespec="seconds")))
            flash("FAQ added successfully.", "success")
        else:
            flash("Question and answer are required.", "danger")
        return redirect(url_for("manage_faqs"))
    with db() as con:
        faqs=con.execute("SELECT * FROM faqs ORDER BY id DESC").fetchall()
    return render_template("faqs.html", faqs=faqs)

@app.route("/admin/faqs/<int:faq_id>/delete", methods=["POST"])
@admin_required
def delete_faq(faq_id):
    with db() as con:
        con.execute("DELETE FROM faqs WHERE id=?", (faq_id,))
    flash("FAQ deleted.", "success")
    return redirect(url_for("manage_faqs"))

@app.route("/admin/conversations")
@admin_required
def conversations():
    with db() as con:
        rows=con.execute("""SELECT c.id,c.visitor_name,c.created_at,
          (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) message_count
          FROM conversations c ORDER BY c.id DESC""").fetchall()
    return render_template("conversations.html", rows=rows)

@app.route("/admin/conversations/<int:cid>")
@admin_required
def conversation_detail(cid):
    with db() as con:
        conv=con.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        messages=con.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (cid,)).fetchall()
    if not conv:
        flash("Conversation not found.", "danger")
        return redirect(url_for("conversations"))
    return render_template("conversation_detail.html", conv=conv, messages=messages)

@app.route("/health")
def health():
    return jsonify(status="ok", application="AI Customer Support Chatbot")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
