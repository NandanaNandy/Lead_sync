import imaplib
import email
from email.header import decode_header
import time
import csv
import ollama  # Using Ollama for LLaMA-3.2
import os

# Email credentials
EMAIL_USER = "crmproject2025@gmail.com"
EMAIL_PASS = "lzvsffsmckusmdxs"

CSV_FILE = "extracted_emails.csv"

def extract_content_with_llama(email_body):
    prompt = f"""
    Analyze the following email and classify it into one of the categories:  
    - **Lead** (potential customer showing interest)  
    - **Opportunity** (potential deal or sales conversation)  
    - **Other** (general communication, spam, or irrelevant email)

    Also, extract:  
    - Key entities (names, companies, organizations)  
    - Important dates  
    - Required actions  
    - Urgency level (low/medium/high)  

    Email Content:
    {email_body[:1000]}  # Limiting to first 1000 characters for efficiency

    **Expected Output Format:**
    Classification: [Lead/Opportunity/Other]  
    Entities: [...]  
    Dates: [...]  
    Actions: [...]  
    Urgency: [Low/Medium/High]
    """

    try:
        response = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
        return response['message']['content']  # Extract the generated response
    except Exception as e:
        print(f"LLaMA Error: {str(e)}")
        return "Extraction failed"
def save_to_csv(data):
    """ Saves extracted email data to a CSV file """
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['subject', 'sender', 'date', 'extracted_data']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow(data)

def process_email(msg):
    """ Processes a single email: extracts subject, sender, date, and body """
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
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # Process with LLaMA
        extracted_data = extract_content_with_llama(body)

        # Prepare CSV data
        csv_data = {
            'subject': subject,
            'sender': sender,
            'date': date,
            'extracted_data': extracted_data
        }
        
        save_to_csv(csv_data)
        return csv_data
    except Exception as e:
        print(f"Error processing email: {str(e)}")
        return None

def check_emails():
    """ Connects to Gmail, fetches unread emails, processes them, and marks as read """
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
                processed_data = process_email(msg)
                
                if processed_data:
                    print(f"Processed email: {processed_data['subject']}")
                
                mail.store(email_id, '+FLAGS', '\Seen')  # Mark email as read
                
        mail.logout()
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    """ Main loop: checks for new emails every 30 seconds """
    print("Email processing started. Press Ctrl+C to exit.")
    try:
        while True:
            check_emails()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\nProcessing stopped.")

if __name__ == "__main__":
    main()
