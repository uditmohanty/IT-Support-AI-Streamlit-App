# test_jira_debug.py
import requests
import json

def test_jira_connection():
    url = "https://uditmohanty98.atlassian.net"
    email = "uditmohanty98@gmail.com"
    api_token = "ATATT3xFfGF0ZuhLYr1LQRJWILoIqhYVYh4T7MdDfMreiU9-8UHFNSD3oRHsA2eCsUlqLgkpaCXmvucAJ-IKle04foS"
    
    auth = (email, api_token)
    headers = {'Accept': 'application/json'}
    
    print("=== JIRA DEBUG TEST ===")
    
    # Test 1: Authentication
    print("1. Testing authentication...")
    try:
        response = requests.get(f"{url}/rest/api/2/myself", auth=auth, headers=headers, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✓ Auth successful: {user_data.get('displayName')} ({user_data.get('emailAddress')})")
        else:
            print(f"✗ Auth failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False
    
    # Test 2: Projects
    print("\n2. Checking available projects...")
    try:
        response = requests.get(f"{url}/rest/api/2/project", auth=auth, headers=headers, timeout=10)
        if response.status_code == 200:
            projects = response.json()
            print(f"✓ Found {len(projects)} projects:")
            for project in projects:
                print(f"   - {project['key']}: {project['name']}")
        else:
            print(f"✗ Projects failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Projects error: {e}")
    
    # Test 3: Simple ticket search
    print("\n3. Testing basic ticket search...")
    jql_queries = [
        "ORDER BY created DESC",
        "created >= -365d ORDER BY created DESC",
        "status is not EMPTY ORDER BY created DESC"
    ]
    
    for i, jql in enumerate(jql_queries, 1):
        print(f"\n   Query {i}: {jql}")
        try:
            params = {
                'jql': jql,
                'maxResults': 10,
                'fields': 'key,summary,status,created'
            }
            response = requests.get(f"{url}/rest/api/2/search", auth=auth, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                issues = data.get('issues', [])
                print(f"   ✓ Total tickets: {total}")
                
                if issues:
                    print("   Recent tickets:")
                    for issue in issues[:5]:
                        print(f"     {issue['key']}: {issue['fields']['summary'][:50]}...")
                else:
                    print("   No tickets found")
                    
                if total > 0:
                    return True
                    
            else:
                print(f"   ✗ Query failed: {response.status_code}")
                if response.status_code == 400:
                    error_data = response.json()
                    print(f"     Error: {error_data.get('errorMessages', [])}")
        except Exception as e:
            print(f"   ✗ Query error: {e}")
    
    return False

if __name__ == "__main__":
    test_jira_connection()