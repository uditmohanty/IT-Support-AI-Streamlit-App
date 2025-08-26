import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Jira Settings
    JIRA_URL = os.getenv('JIRA_URL', '')
    JIRA_EMAIL = os.getenv('JIRA_EMAIL', '')
    JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN', '')
    
    # Google AI
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Database
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./it_support.db')
    
    # App Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')  # ADD THIS LINE
    PAGE_TITLE = "IT Support AI Dashboard"
    PAGE_ICON = "🤖"
    
    # Categories
    TICKET_CATEGORIES = ['Hardware', 'Software', 'Network', 'Security', 'General']
    PRIORITIES = ['Critical', 'High', 'Medium', 'Low']
    
    @classmethod
    def validate_config(cls):
        """Validate configuration and return status"""
        issues = []
        
        if not cls.GEMINI_API_KEY:
            issues.append("GEMINI_API_KEY is missing")
        
        if not cls.JIRA_URL:
            issues.append("JIRA_URL is missing (set to demo mode)")
            
        if not cls.JIRA_EMAIL:
            issues.append("JIRA_EMAIL is missing (set to demo mode)")
            
        if not cls.JIRA_API_TOKEN:
            issues.append("JIRA_API_TOKEN is missing (set to demo mode)")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'demo_mode': not cls.JIRA_URL or not cls.JIRA_EMAIL or not cls.JIRA_API_TOKEN
        }