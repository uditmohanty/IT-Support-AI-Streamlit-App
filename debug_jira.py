from utils.jira_client import JiraClient

def debug_jira_update():
    """Debug JIRA ticket update functionality"""
    print("=== JIRA Update Debug ===")
    
    client = JiraClient()
    ticket_id = "KAN-58"
    
    # Check if we're in demo mode
    print(f"Demo mode: {client.demo_mode}")
    print(f"JIRA URL: {client.url}")
    print(f"Email configured: {'Yes' if client.email else 'No'}")
    print(f"Token configured: {'Yes' if client.api_token else 'No'}")
    
    if client.demo_mode:
        print("❌ In demo mode - JIRA updates won't work")
        return
    
    print(f"\n--- Getting available transitions for {ticket_id} ---")
    
    # Check available transitions
    try:
        import requests
        transitions_url = f"{client.url}/rest/api/2/issue/{ticket_id}/transitions"
        response = requests.get(transitions_url, auth=client.auth, headers=client.headers)
        
        print(f"Transitions API Status: {response.status_code}")
        
        if response.status_code == 200:
            transitions = response.json()['transitions']
            print(f"Available transitions:")
            for transition in transitions:
                print(f"  - {transition['name']} (ID: {transition['id']}) → {transition['to']['name']}")
        else:
            print(f"❌ Failed to get transitions: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error getting transitions: {str(e)}")
        return
    
    print(f"\n--- Testing update to 'Done' ---")
    
    # Test the update
    success = client.update_ticket_status(ticket_id, "Done")
    print(f"Update result: {'✅ Success' if success else '❌ Failed'}")
    
    # Also test with different status names that might exist
    common_statuses = ["Done", "Resolved", "Closed", "Complete"]
    
    print(f"\n--- Testing common status names ---")
    for status in common_statuses:
        # Check if this status is available in transitions
        status_available = False
        if response.status_code == 200:
            for transition in transitions:
                if transition['to']['name'].lower() == status.lower():
                    status_available = True
                    break
        
        print(f"  {status}: {'Available' if status_available else 'Not available'}")

if __name__ == "__main__":
    debug_jira_update()