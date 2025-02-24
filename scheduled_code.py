import sys
sys.stdout.reconfigure(encoding="utf-8")
import imaplib
import email
import pandas as pd
import re
import schedule
import time
from email.header import decode_header
from serpapi import GoogleSearch  # Used for fetching company contact details from Google

# Gmail IMAP Credentials
EMAIL_USER = "crmproject2025@gmail.com"  # Replace with your Gmail
EMAIL_PASS = "lzvsffsmckusmdxs"  # Replace with your generated App Password

# CSV Files for Storing Data
LEAD_CSV = "lead_data.csv"
OPPORTUNITY_CSV = "opportunity_data.csv"

# Keywords to Classify Emails
OPPORTUNITY_KEYWORDS = ["service", "website", "marketing", "project", "pricing", "quote","we need", "we require", "looking for", "want to develop", "need a solution", "our project","budget", "deadline", "proposal"]
LEAD_KEYWORDS = ["interest", "inquiry", "looking for", "details", "solution"]

# Function to extract contact number from email
def extract_contact_number(email_body):
    phone_pattern = r"(\+?\d{1,3}[-.\s]?)?(\d{10}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})"
    match = re.search(phone_pattern, email_body)
    if match:
        return match.group()
    return None

# Function to extract company name from email body
def extract_company_name(email_body):
    company_pattern = r"\b(?:Company|Organization|Firm|Business):?\s*([\w\s]+)"
    match = re.search(company_pattern, email_body, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

# Function to fetch company contact number from Google Search
def fetch_contact_number_from_google(company_name):
    try:
        api_key = "your-serpapi-key"  # Replace with your actual SerpAPI Key
        search = GoogleSearch({
            "q": f"{company_name} contact number",
            "api_key": api_key
        })
        results = search.get_dict()
        if "organic_results" in results:
            for result in results["organic_results"]:
                contact_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\d{10}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})", result["snippet"])
                if contact_match:
                    return contact_match.group()
    except Exception as e:
        print(f"Failed to fetch contact from Google: {e}")
    return None

# Function to classify email content
def classify_email(subject, body):
    content = f"{subject} {body}".lower()
    if any(keyword in content for keyword in OPPORTUNITY_KEYWORDS):
        return "Opportunity"
    if any(keyword in content for keyword in LEAD_KEYWORDS):
        return "Lead"
    return "Lead"  # Default to Lead if unsure

# Function to update CSV files
def update_csv(file_name, data):
    try:
        df = pd.read_csv(file_name)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["Name", "Company", "Email", "Contact Number", "Message"])
    
    if not df[df["Email"] == data["Email"]].empty:
        print(f"Skipping duplicate entry for {data['Email']}")
        return

    df = df.append(data, ignore_index=True)
    df.to_csv(file_name, index=False)
    print(f"✅ Data saved to {file_name}")

# Main function to fetch and process emails
def fetch_emails():
    try:
        print("📩 Connecting to Gmail IMAP server...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        print("🔎 Searching for unread emails...")
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if not email_ids:
            print("📭 No unread emails found.")
            return

        for email_id in email_ids:
            print(f"📨 Fetching email ID {email_id.decode()}...")
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    from_email = msg.get("From")
                    body = ""
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                    classification = classify_email(subject, body)
                    contact_number = extract_contact_number(body)
                    company_name = extract_company_name(body)

                    if not contact_number and company_name:
                        print(f"🔍 No contact found. Searching for {company_name} online...")
                        contact_number = fetch_contact_number_from_google(company_name)

                    data = {
                        "Name": from_email.split("<")[0].strip(),
                        "Company": company_name or "Unknown",
                        "Email": from_email.split("<")[-1].strip(">").strip(),
                        "Contact Number": contact_number or "Not Available",
                        "Message": body.strip()
                    }

                    if classification == "Lead":
                        update_csv(LEAD_CSV, data)
                    else:
                        update_csv(OPPORTUNITY_CSV, data)

        print("✅ Email classification and storage completed!")

    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try:
            mail.logout()
            print("📤 Logged out from email.")
        except Exception as e:
            print(f"Failed to logout: {e}")

# Scheduling the email fetcher to run every 3 minutes
schedule.every(3).minutes.do(fetch_emails)

print("📅 Email checker scheduled to run every 3 minutes...")

while True:
    schedule.run_pending()
    time.sleep(1)  # Prevent CPU overuse
