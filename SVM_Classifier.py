import imaplib
import email
import os
import joblib
from email.header import decode_header
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC

# Configuration
EMAIL_HOST = "imap.gmail.com"
EMAIL_USER = "arikaran258@gmail.com"
EMAIL_PASS = "xgcj kime wyeh qokd"
TIMEOUT = 15  # Seconds for connection timeout
CLASSIFIER_PATH = "lead_classifier.joblib"
KEYWORDS = [
    'collaborat', 'quot', 'partnership', 'opportunity', 
    'busi', 'proposal', 'deal', 'pricing', 'order'
]

def fetch_unread_emails():
    mail = None
    try:
        # Initialize connection with timeout
        mail = imaplib.IMAP4_SSL(EMAIL_HOST, timeout=TIMEOUT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox", readonly=True)

        # Fetch unread emails
        status, messages = mail.search(None, 'UNSEEN')
        if status != "OK" or not messages[0]:
            return []

        email_ids = messages[0].split()[-20:]  # Process max 20 emails
        results = []

        for idx, e_id in enumerate(email_ids, 1):
            try:
                # Email processing
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Subject decoding
                subject_header = decode_header(msg.get("Subject", ""))
                subject = "(No Subject)"
                if subject_header and subject_header[0]:
                    subject_bytes, encoding = subject_header[0]
                    encoding = encoding or 'utf-8'
                    subject = subject_bytes.decode(encoding, errors='ignore') if isinstance(subject_bytes, bytes) else str(subject_bytes)

                # Body extraction
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            except:
                                pass
                            break
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass

                full_text = f"Subject: {subject}\nBody: {body}"
                classification = classify_email(full_text)

                results.append({
                    "id": e_id.decode(),
                    "subject": subject,
                    "classification": classification,
                    "preview": full_text[:150] + "..." if len(full_text) > 150 else full_text
                })

                print(f"Processed email {idx}/{len(email_ids)} - {classification}")

            except Exception as e:
                print(f"Error processing email {idx}: {str(e)[:100]}")
                continue

        return results

    except Exception as e:
        print(f"Connection error: {str(e)[:100]}")
        return []
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except:
                pass

def classify_email(text):
    # Rule-based classification
    text_lower = text.lower()
    if any(kw in text_lower for kw in KEYWORDS):
        return "Potential Lead"
    
    # ML classification
    if os.path.exists(CLASSIFIER_PATH):
        model = joblib.load(CLASSIFIER_PATH)
        return model.predict([text])[0]
    
    return "Unclassified"

def train_initial_model():
    # Sample training data
    emails = [
        "Please send quotation for your services",
        "Partnership opportunity inquiry",
        "Requesting price list for bulk orders",
        "Meeting invitation for project discussion",
        "Your weekly newsletter", 
        "Account security update"
    ]
    labels = ["Lead", "Opportunity", "Lead", "Opportunity", "Other", "Other"]
    
    model = make_pipeline(
        TfidfVectorizer(stop_words='english'),
        SVC(kernel='linear', class_weight='balanced')
    )
    model.fit(emails, labels)
    joblib.dump(model, CLASSIFIER_PATH)
    print("Initial classifier trained with sample data")

def generate_report(results):
    print("\n" + "="*50)
    print("Email Classification Report".center(50))
    print("="*50)
    
    lead_count = sum(1 for r in results if "Lead" in r['classification'])
    opportunity_count = sum(1 for r in results if "Opportunity" in r['classification'])
    
    print(f"\nTotal Emails Processed: {len(results)}")
    print(f"Potential Leads: {lead_count}")
    print(f"Business Opportunities: {opportunity_count}")
    print(f"Other/Unclassified: {len(results) - (lead_count + opportunity_count)}")
    
    print("\nDetails:")
    for idx, res in enumerate(results, 1):
        print(f"\nEmail {idx}:")
        print(f"ID: {res['id']}")
        print(f"Subject: {res['subject']}")
        print(f"Classification: {res['classification']}")
        print(f"Preview: {res['preview']}")

if __name__ == "__main__":
    # Create initial model if missing
    if not os.path.exists(CLASSIFIER_PATH):
        train_initial_model()
    
    # Process emails
    emails = fetch_unread_emails()
    
    if emails:
        generate_report(emails)
    else:
        print("\nNo unread emails found or error occurred during processing")