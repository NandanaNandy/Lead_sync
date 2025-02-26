import imaplib
import email
from email.header import decode_header
import time
import sqlite3
import ollama
import os
from datetime import datetime

EMAIL_USER = "crmproject2025@gmail.com"
EMAIL_PASS = "lzvsffsmckusmdxs"
DB_FILE = "crm_emails.db"

def create_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Lead (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        lead_status TEXT,
        lead_owner TEXT,
        created_by TEXT,
        created_on TEXT,
        country TEXT,
        state TEXT,
        company_website TEXT,
        annual_revenue REAL,
        remark TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Contact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        company_name TEXT UNIQUE,
        name TEXT,
        status TEXT,
        phone_number TEXT UNIQUE,
        email_id TEXT,
        created_by TEXT,
        created_on TEXT,
        is_primary BOOLEAN,
        FOREIGN KEY(lead_id) REFERENCES Lead(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Opportunity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        primary_contact_id INTEGER,
        name TEXT,
        stage TEXT,
        owner TEXT,
        opportunity_value REAL,
        closing_date TEXT,
        probability REAL,
        created_by TEXT,
        created_on TEXT,
        remark TEXT,
        FOREIGN KEY(lead_id) REFERENCES Lead(id),
        FOREIGN KEY(primary_contact_id) REFERENCES Contact(id)
    )''')
    
    conn.commit()
    conn.close()

def save_to_database(sender, classification, urgency, date_mentioned, email_body):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        created_on = datetime.now().strftime("%Y-%m-%d")

        if classification == "Lead":
            cursor.execute("INSERT OR IGNORE INTO Lead (name, lead_owner, created_by, created_on, remark) VALUES (?, ?, ?, ?, ?)",
                           (sender, sender, sender, created_on, email_body))
        elif classification == "Opportunity":
            cursor.execute("INSERT INTO Opportunity (name, owner, opportunity_value, closing_date, created_by, created_on, remark) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (sender, sender, 0, date_mentioned, sender, created_on, email_body))
        else:
            cursor.execute("INSERT OR IGNORE INTO Contact (name, email_id, created_by, created_on, remark) VALUES (?, ?, ?, ?, ?)",
                           (sender, sender, sender, created_on, email_body))

        conn.commit()
        conn.close()
        print("[INFO] Email data saved to database.")
    except Exception as e:
        print(f"[ERROR] Database error: {str(e)}")

def extract_content_with_llama(email_body):
    prompt = f"""
    Analyze the following email and classify it into:
    - Lead
    - Opportunity
    - Other
    Also extract:
    - Important dates mentioned in the email
    - Urgency level (low/medium/high)
    Email Content:
    {email_body[:1000]}
    Expected Output Format:
    Classification: [Lead/Opportunity/Other]
    Date: [Extracted date or 'None']
    Urgency: [Low/Medium/High]
    """
    try:
        response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
        output = response['message']['content']
        
        classification = "Other"
        urgency = "Low"
        date_mentioned = "None"

        for line in output.split("\n"):
            if "Classification:" in line:
                classification = line.split(":")[1].strip()
            elif "Urgency:" in line:
                urgency = line.split(":")[1].strip()
            elif "Date:" in line:
                date_mentioned = line.split(":")[1].strip()

        return classification, urgency, date_mentioned
    except Exception as e:
        print(f"LLaMA Error: {str(e)}")
        return "Other", "Low", "None"

def process_email(msg):
    try:
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or 'utf-8')
        
        sender = msg.get("From")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        
        classification, urgency, date_mentioned = extract_content_with_llama(body)
        save_to_database(sender, classification, urgency, date_mentioned, body)

        print(f"[INFO] Processed email from {sender}: {classification}, Urgency: {urgency}, Date Mentioned: {date_mentioned}")
    except Exception as e:
        print(f"Error processing email: {str(e)}")

def check_emails():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != "OK":
            return
        
        for email_id in messages[0].split():
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status == "OK":
                msg = email.message_from_bytes(msg_data[0][1])
                process_email(msg)
                mail.store(email_id, '+FLAGS', '\\Seen')
                
        mail.logout()
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    create_database()
    print("Email processing started. Press Ctrl+C to exit.")
    try:
        while True:
            check_emails()
            time.sleep(180)
    except KeyboardInterrupt:
        print("\nProcessing stopped.")

if __name__ == "__main__":
    main()