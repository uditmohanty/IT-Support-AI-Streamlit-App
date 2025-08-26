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
    
    def fetch_tickets(self, days_back=7, max_results=50):
        """Fetch tickets from Jira or return demo data"""
        if self.demo_mode:
            return self._get_demo_tickets(max_results)
        
        try:
            # JQL query for recent tickets
            jql = f'status IN ("Open", "To Do", "In Progress") AND created >= -{days_back}d ORDER BY created DESC'
            
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
            
            ticket = {
                'id': issue.get('key'),
                'summary': fields.get('summary', ''),
                'description': fields.get('description', '') or '',
                'priority': fields.get('priority', {}).get('name', 'Medium') if fields.get('priority') else 'Medium',
                'status': fields.get('status', {}).get('name', 'Unknown'),
                'reporter': fields.get('reporter', {}).get('displayName', 'Unknown') if fields.get('reporter') else 'Unknown',
                'created': fields.get('created'),
                'updated': fields.get('updated'),
                'category': self._classify_ticket(fields.get('summary', '') + ' ' + (fields.get('description', '') or ''))
            }
            tickets.append(ticket)
        
        return tickets
    
    def _classify_ticket(self, text):
        """Basic ticket classification"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['computer', 'laptop', 'desktop', 'monitor', 'printer', 'hardware']):
            return 'Hardware'
        elif any(word in text_lower for word in ['software', 'application', 'program', 'install', 'update']):
            return 'Software'
        elif any(word in text_lower for word in ['network', 'wifi', 'internet', 'connection', 'vpn']):
            return 'Network'
        elif any(word in text_lower for word in ['password', 'login', 'access', 'security', 'account', 'locked']):
            return 'Security'
        else:
            return 'General'

# Test function
def test_jira_connection():
    client = JiraClient()
    result = client.fetch_tickets(days_back=1, max_results=5)
    return result