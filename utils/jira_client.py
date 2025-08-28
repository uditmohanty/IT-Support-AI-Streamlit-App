import requests
import json
from datetime import datetime, timedelta
from config import Config
import streamlit as st
import random

class JiraClient:
    def __init__(self):
        self.url = Config.JIRA_URL
        self.email = Config.JIRA_EMAIL
        self.api_token = Config.JIRA_API_TOKEN
        self.auth = (self.email, self.api_token) if self.email and self.api_token else None
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Check if we're in demo mode
        self.demo_mode = not (self.url and self.email and self.api_token)
        if self.demo_mode:
            print("Running in DEMO MODE - using sample data")
    
    def fetch_tickets(self, days_back=30, max_results=50):
        """Fetch tickets from Jira or return demo data"""
        if self.demo_mode:
            return self._get_demo_tickets(max_results)
        
        try:
            # Broader JQL query to fetch more tickets
            # Removed restrictive status filter and extended date range
            jql = f'created >= -{days_back}d ORDER BY created DESC'
            
            url = f"{self.url}/rest/api/2/search"
            params = {
                'jql': jql,
                'maxResults': max_results,
                'fields': 'key,summary,description,priority,status,reporter,created,updated'
            }
            
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                tickets = self._process_tickets(data.get('issues', []))
                return {'success': True, 'tickets': tickets, 'count': len(tickets)}
            else:
                # If the filtered query fails, try a completely open query
                jql_fallback = 'ORDER BY created DESC'
                params['jql'] = jql_fallback
                
                fallback_response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
                
                if fallback_response.status_code == 200:
                    data = fallback_response.json()
                    tickets = self._process_tickets(data.get('issues', []))
                    return {'success': True, 'tickets': tickets, 'count': len(tickets)}
                else:
                    return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_ticket_status(self, ticket_id, new_status):
        """Update ticket status in JIRA"""
        if self.demo_mode:
            print(f"DEMO MODE: Would update {ticket_id} to {new_status}")
            return True
            
        try:
            # First get available transitions
            transitions_url = f"{self.url}/rest/api/2/issue/{ticket_id}/transitions"
            response = requests.get(transitions_url, auth=self.auth, headers=self.headers)
            
            if response.status_code == 200:
                transitions = response.json()['transitions']
                
                # Find the transition ID for the desired status
                transition_id = None
                for transition in transitions:
                    if transition['to']['name'].lower() == new_status.lower():
                        transition_id = transition['id']
                        break
                
                if transition_id:
                    # Execute the transition
                    transition_url = f"{self.url}/rest/api/2/issue/{ticket_id}/transitions"
                    payload = {
                        "transition": {"id": transition_id}
                    }
                    
                    update_response = requests.post(
                        transition_url, 
                        auth=self.auth, 
                        headers=self.headers,
                        data=json.dumps(payload)
                    )
                    
                    return update_response.status_code == 204
                else:
                    print(f"No transition found for status: {new_status}")
                    return False
            else:
                print(f"Failed to get transitions: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Failed to update JIRA ticket {ticket_id}: {str(e)}")
            return False
    
    def add_comment_to_ticket(self, ticket_id, comment):
        """Add comment to JIRA ticket"""
        if self.demo_mode:
            print(f"DEMO MODE: Would add comment to {ticket_id}")
            return True
            
        try:
            comment_url = f"{self.url}/rest/api/2/issue/{ticket_id}/comment"
            payload = {
                "body": comment
            }
            
            response = requests.post(
                comment_url,
                auth=self.auth,
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            return response.status_code == 201
            
        except Exception as e:
            print(f"Failed to add comment to {ticket_id}: {str(e)}")
            return False
    
    def _get_demo_tickets(self, max_results=10):
        """Generate demo tickets for testing"""
        demo_tickets = [
            {
                'id': 'DEMO-001',
                'summary': 'Laptop won\'t start after Windows update',
                'description': 'User reports laptop shows black screen after latest Windows update. Power button works but no display.',
                'priority': 'High',
                'status': 'Open',
                'reporter': 'John Smith',
                'created': (datetime.now() - timedelta(hours=2)).isoformat(),
                'updated': (datetime.now() - timedelta(hours=1)).isoformat(),
            },
            {
                'id': 'DEMO-002',
                'summary': 'Cannot access shared network drive',
                'description': 'Employee cannot connect to shared drive \\server\\finance. Gets access denied error.',
                'priority': 'Medium',
                'status': 'In Progress',
                'reporter': 'Jane Doe',
                'created': (datetime.now() - timedelta(hours=4)).isoformat(),
                'updated': (datetime.now() - timedelta(hours=3)).isoformat(),
            },
            {
                'id': 'DEMO-003',
                'summary': 'Office printer not working',
                'description': 'Main office printer showing error code E001. Paper jams cleared but still not printing.',
                'priority': 'Low',
                'status': 'Open',
                'reporter': 'Mike Johnson',
                'created': (datetime.now() - timedelta(days=1)).isoformat(),
                'updated': (datetime.now() - timedelta(hours=8)).isoformat(),
            },
            {
                'id': 'DEMO-004',
                'summary': 'Email account locked out',
                'description': 'User locked out of email account after multiple failed login attempts. Needs password reset.',
                'priority': 'High',
                'status': 'To Do',
                'reporter': 'Sarah Wilson',
                'created': (datetime.now() - timedelta(hours=6)).isoformat(),
                'updated': (datetime.now() - timedelta(hours=5)).isoformat(),
            },
            {
                'id': 'DEMO-005',
                'summary': 'VPN connection issues',
                'description': 'Remote employee cannot establish VPN connection. Times out during authentication.',
                'priority': 'Critical',
                'status': 'Open',
                'reporter': 'David Brown',
                'created': (datetime.now() - timedelta(minutes=30)).isoformat(),
                'updated': (datetime.now() - timedelta(minutes=15)).isoformat(),
            },
            {
                'id': 'DEMO-006',
                'summary': 'Microsoft Office license expired',
                'description': 'User getting activation errors when opening Word and Excel. License needs renewal.',
                'priority': 'Medium',
                'status': 'In Progress',
                'reporter': 'Lisa Anderson',
                'created': (datetime.now() - timedelta(hours=12)).isoformat(),
                'updated': (datetime.now() - timedelta(hours=10)).isoformat(),
            },
            {
                'id': 'DEMO-007',
                'summary': 'Slow computer performance',
                'description': 'Employee reports computer is very slow, takes 10+ minutes to boot up and programs freeze frequently.',
                'priority': 'Medium',
                'status': 'Open',
                'reporter': 'Robert Chen',
                'created': (datetime.now() - timedelta(days=2)).isoformat(),
                'updated': (datetime.now() - timedelta(days=1)).isoformat(),
            },
            {
                'id': 'DEMO-008',
                'summary': 'Cannot send emails',
                'description': 'User can receive emails but cannot send. Gets error: "SMTP server connection failed".',
                'priority': 'High',
                'status': 'To Do',
                'reporter': 'Maria Garcia',
                'created': (datetime.now() - timedelta(hours=8)).isoformat(),
                'updated': (datetime.now() - timedelta(hours=7)).isoformat(),
            },
            {
                'id': 'DEMO-009',
                'summary': 'USB devices not recognized',
                'description': 'Computer not recognizing USB flash drives and external hard drives. Tried multiple ports.',
                'priority': 'Low',
                'status': 'Open',
                'reporter': 'Kevin Martinez',
                'created': (datetime.now() - timedelta(days=3)).isoformat(),
                'updated': (datetime.now() - timedelta(days=2)).isoformat(),
            },
            {
                'id': 'DEMO-010',
                'summary': 'Phone system down',
                'description': 'Office phone system completely down. No incoming or outgoing calls possible.',
                'priority': 'Critical',
                'status': 'In Progress',
                'reporter': 'Amanda Taylor',
                'created': (datetime.now() - timedelta(minutes=45)).isoformat(),
                'updated': (datetime.now() - timedelta(minutes=30)).isoformat(),
            }
        ]
        
        # Add category classification
        for ticket in demo_tickets:
            ticket['category'] = self._classify_ticket(ticket['summary'] + ' ' + ticket['description'])
        
        # Return only requested number
        selected_tickets = demo_tickets[:min(max_results, len(demo_tickets))]
        
        return {
            'success': True,
            'tickets': selected_tickets,
            'count': len(selected_tickets)
        }
    
    def _process_tickets(self, issues):
        """Process raw Jira tickets"""
        tickets = []
        for issue in issues:
            fields = issue.get('fields', {})
            
            # Handle description field which can be complex in Jira
            description = ''
            if fields.get('description'):
                if isinstance(fields.get('description'), dict):
                    # For newer Jira versions with Atlassian Document Format
                    description = self._extract_text_from_adf(fields.get('description'))
                else:
                    # For older Jira versions with plain text
                    description = str(fields.get('description'))
            
            ticket = {
                'id': issue.get('key'),
                'summary': fields.get('summary', ''),
                'description': description,
                'priority': fields.get('priority', {}).get('name', 'Medium') if fields.get('priority') else 'Medium',
                'status': fields.get('status', {}).get('name', 'Unknown'),
                'reporter': fields.get('reporter', {}).get('displayName', 'Unknown') if fields.get('reporter') else 'Unknown',
                'created': fields.get('created'),
                'updated': fields.get('updated'),
                'category': self._classify_ticket(fields.get('summary', '') + ' ' + description)
            }
            tickets.append(ticket)
        
        return tickets
    
    def _extract_text_from_adf(self, adf_content):
        """Extract plain text from Atlassian Document Format"""
        if not adf_content or not isinstance(adf_content, dict):
            return ''
        
        text_parts = []
        
        def extract_text_recursive(content):
            if isinstance(content, dict):
                if content.get('type') == 'text':
                    text_parts.append(content.get('text', ''))
                elif content.get('content'):
                    for item in content['content']:
                        extract_text_recursive(item)
            elif isinstance(content, list):
                for item in content:
                    extract_text_recursive(item)
        
        extract_text_recursive(adf_content)
        return ' '.join(text_parts).strip()
    
    def _classify_ticket(self, text):
        """Basic ticket classification"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['computer', 'laptop', 'desktop', 'monitor', 'printer', 'hardware', 'usb', 'mouse', 'keyboard']):
            return 'Hardware'
        elif any(word in text_lower for word in ['software', 'application', 'program', 'install', 'update', 'office', 'microsoft', 'license']):
            return 'Software'
        elif any(word in text_lower for word in ['network', 'wifi', 'internet', 'connection', 'vpn', 'email', 'smtp']):
            return 'Network'
        elif any(word in text_lower for word in ['password', 'login', 'access', 'security', 'account', 'locked', 'authentication']):
            return 'Security'
        elif any(word in text_lower for word in ['phone', 'telephone', 'call', 'voip']):
            return 'Telecom'
        else:
            return 'General'

# Test function
def test_jira_connection():
    client = JiraClient()
    result = client.fetch_tickets(days_back=30, max_results=10)
    return result