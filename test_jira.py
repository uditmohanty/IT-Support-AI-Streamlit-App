from utils.jira_client import JiraClient
from config import Config

def test_connection():
    print(f"Testing connection to: {Config.JIRA_URL}")
    print(f"Using email: {Config.JIRA_EMAIL}")
    print(f"API token configured: {'Yes' if Config.JIRA_API_TOKEN else 'No'}")
    
    client = JiraClient()
    result = client.fetch_tickets(days_back=30, max_results=1)
    
    if result['success']:
        print("✅ Connection successful!")
        print(f"Found {result['count']} tickets")
    else:
        print("❌ Connection failed!")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    test_connection()