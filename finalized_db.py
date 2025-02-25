import imaplib
import email
from email.header import decode_header
import time
import sqlite3
import ollama  # Using Ollama for LLaMA-3.2
import os

# Email credentials
EMAIL_USER = "crmproject2025@gmail.com"
EMAIL_PASS = "lzvsffsmckusmdxs"

DB_FILE = "emails.db"

def create_database():
    """ Creates the database and table if they don't exist """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            urgency TEXT,
            date_mentioned TEXT,
            classification TEXT
        )
    ''')

    conn.commit()
    conn.close()

def save_to_database(sender, urgency, date_mentioned, classification):
    """ Saves extracted email data to SQLite database """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO emails (sender, urgency, date_mentioned, classification)
            VALUES (?, ?, ?, ?)
        ''', (sender, urgency, date_mentioned, classification))

        conn.commit()
        conn.close()
        print("[INFO] Email data saved to database.")
    except Exception as e:
        print(f"[ERROR] Database error: {str(e)}")

def extract_content_with_llama(email_body):
    """ Uses LLaMA to extract classification, urgency, and date from the email content """
    prompt = f"""
    Analyze the following email and classify it into one of the categories:
    - **Lead** (potential customer showing interest)
    - **Opportunity** (potential deal or sales conversation)
    - **Other** (general communication, spam, or irrelevant email)

    Also, extract:
    - Important dates mentioned in the email
    - Urgency level (low/medium/high)

    Email Content:
    {email_body[:1000]}  # Limiting to first 1000 characters for efficiency

    **Expected Output Format:**
    Classification: [Lead/Opportunity/Other]
    Date: [Extracted date or 'None']
    Urgency: [Low/Medium/High]
    """

    try:
        response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
        output = response['message']['content']
        
        # Extract relevant fields
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
    """ Processes a single email: extracts sender, date, and body """
    try:
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or 'utf-8')
        
        sender = msg.get("From")
        date = msg.get("Date")

        # Extract email body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors='ignore')
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')

        # Process with LLaMA
        classification, urgency, date_mentioned = extract_content_with_llama(body)

        # Save to database
        save_to_database(sender, urgency, date_mentioned, classification)

        print(f"[INFO] Processed email from {sender}: {classification}, Urgency: {urgency}, Date Mentioned: {date_mentioned}")
    except Exception as e:
        print(f"Error processing email: {str(e)}")

def check_emails():
    """ Connects to Gmail, fetches unread emails, processes them, and marks them as read """
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

                mail.store(email_id, '+FLAGS', '\\Seen')  # Mark email as read
                
        mail.logout()
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    """ Main loop: checks for new emails every 30 seconds """
    create_database()  # Ensure the database is created
    print("Email processing started. Press Ctrl+C to exit.")
    
    try:
        while True:
            check_emails()
            time.sleep(180)
    except KeyboardInterrupt:
        print("\nProcessing stopped.")

if __name__ == "__main__":
    main()
