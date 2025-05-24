

from dotenv import load_dotenv
load_dotenv()




from flask import Flask, render_template, request, send_from_directory, jsonify, abort, session, redirect, url_for
import razorpay
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Load from .env

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")  # Load from .env
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")  # Load from .env
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

PDFS = {
    "cn": {"title": "Computer Networks", "price": 9, "file": "CN.pdf"},
}

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (email TEXT, note_id TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@login_required
def index():
    return render_template("index.html", pdfs=PDFS, key_id=RAZORPAY_KEY_ID)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session['email'] = request.form['email']
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/create-order", methods=["POST"])
@login_required
def create_order():
    data = request.json
    note_id = data["note_id"]
    if note_id not in PDFS:
        abort(404)
    amount = PDFS[note_id]["price"] * 100
    order = client.order.create({"amount": amount, "currency": "INR", "payment_capture": "1"})
    return jsonify(order)

@app.route("/verify", methods=["POST"])
@login_required
def verify():
    data = request.json
    try:
        client.utility.verify_payment_signature(data)
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO purchases (email, note_id) VALUES (?, ?)", (session['email'], data['note_id']))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except:
        return jsonify({"success": False}), 400

@app.route("/view/<note_id>")
@login_required
def view_pdf(note_id):
    if note_id not in PDFS:
        return "Note not found", 404

    # Check if user has purchased this note
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM purchases WHERE email=? AND note_id=?", (session['email'], note_id))
    result = c.fetchone()
    conn.close()

    if not result:
        return "Access denied. Please purchase this note to view it."

    pdf_path = f"/static/pdfjs/web/viewer.html?file=/pdfs/{PDFS[note_id]['file']}"
    return redirect(pdf_path)

if __name__ == "__main__":
    if not os.path.exists("pdfs"):
        os.mkdir("pdfs")
    app.run(debug=True)
