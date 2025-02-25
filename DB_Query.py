import sqlite3

DB_FILE = "emails.db"

def fetch_emails(filter_by=None, value=None):
    """ Fetches and displays emails based on optional filters """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    query = "SELECT sender, urgency, date_mentioned, classification FROM emails"
    
    if filter_by and value:
        query += f" WHERE {filter_by} = ?"
        cursor.execute(query, (value,))
    else:
        cursor.execute(query)

    emails = cursor.fetchall()
    conn.close()
    
    return emails

def display_emails(emails):
    """ Prints the fetched emails in a readable format """
    if not emails:
        print("[INFO] No matching emails found.")
        return

    print("\n📩 **Stored Emails**\n")
    for idx, (sender, urgency, date, classification) in enumerate(emails, start=1):
        print(f"{idx}. Sender: {sender}\n   Urgency: {urgency}\n   Date Mentioned: {date}\n   Classification: {classification}\n")

def main():
    """ Menu-driven interface for querying the database """
    print("\n🔍 **Email Query System**")
    print("1. View all emails")
    print("2. Filter by classification (Lead/Opportunity)")
    print("3. Filter by urgency (Low/Medium/High)")
    print("4. Exit")
    
    choice = input("Enter your choice: ").strip()
    
    if choice == "1":
        emails = fetch_emails()
    elif choice == "2":
        classification = input("Enter classification (Lead/Opportunity): ").strip().capitalize()
        emails = fetch_emails("classification", classification)
    elif choice == "3":
        urgency = input("Enter urgency level (Low/Medium/High): ").strip().capitalize()
        emails = fetch_emails("urgency", urgency)
    elif choice == "4":
        print("Exiting...")
        return
    else:
        print("[ERROR] Invalid choice.")
        return

    display_emails(emails)

if __name__ == "__main__":
    main()
