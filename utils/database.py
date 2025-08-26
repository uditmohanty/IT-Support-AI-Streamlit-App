import sqlite3
import pandas as pd
import json
from datetime import datetime
from config import Config
import streamlit as st
import os

class Database:
    def __init__(self):
        # Handle different database URL formats
        database_url = Config.DATABASE_URL
        if database_url.startswith('sqlite:///'):
            self.db_path = database_url.replace('sqlite:///', '')
        else:
            self.db_path = database_url
        
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tickets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    summary TEXT,
                    description TEXT,
                    category TEXT,
                    priority TEXT,
                    status TEXT,
                    reporter TEXT,
                    created TEXT,
                    updated TEXT
                )
            ''')
            
            # Processed tickets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_tickets (
                    id TEXT PRIMARY KEY,
                    ticket_id TEXT,
                    analysis TEXT,
                    confidence REAL,
                    processed_date TEXT,
                    status TEXT,
                    FOREIGN KEY (ticket_id) REFERENCES tickets (id)
                )
            ''')
            
            # Agent feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT,
                    agent_id TEXT,
                    rating INTEGER,
                    action TEXT,
                    comments TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (ticket_id) REFERENCES tickets (id)
                )
            ''')
            
            # Knowledge base table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    category TEXT,
                    description TEXT,
                    solution TEXT,
                    tags TEXT,
                    quality_score REAL,
                    created TEXT,
                    updated TEXT
                )
            ''')
            
            # System logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    function_name TEXT,
                    status TEXT,
                    details TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Database initialization failed: {str(e)}")
            # Don't show streamlit error here as it might not be available
    
    def save_tickets(self, tickets):
        """Save tickets to database"""
        if not tickets:
            return True
            
        try:
            conn = sqlite3.connect(self.db_path)
            
            for ticket in tickets:
                # Insert or update ticket
                conn.execute('''
                    INSERT OR REPLACE INTO tickets 
                    (id, summary, description, category, priority, status, reporter, created, updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ticket.get('id', ''),
                    ticket.get('summary', ''),
                    ticket.get('description', ''),
                    ticket.get('category', ''),
                    ticket.get('priority', ''),
                    ticket.get('status', ''),
                    ticket.get('reporter', ''),
                    ticket.get('created', ''),
                    ticket.get('updated', '')
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Failed to save tickets: {str(e)}")
            return False
    
    def save_processed_ticket(self, ticket_id, analysis):
        """Save processed ticket analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            conn.execute('''
                INSERT OR REPLACE INTO processed_tickets 
                (id, ticket_id, analysis, confidence, processed_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                f"processed_{ticket_id}_{int(datetime.now().timestamp())}",
                ticket_id,
                json.dumps(analysis),
                analysis.get('confidence', 0.5),
                datetime.now().isoformat(),
                'pending'
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Failed to save processed ticket: {str(e)}")
            return False
    
    def get_tickets(self, status_filter=None, limit=100):
        """Get tickets from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            if status_filter:
                query = "SELECT * FROM tickets WHERE status = ? ORDER BY created DESC LIMIT ?"
                df = pd.read_sql_query(query, conn, params=(status_filter, limit))
            else:
                query = "SELECT * FROM tickets ORDER BY created DESC LIMIT ?"
                df = pd.read_sql_query(query, conn, params=(limit,))
            
            conn.close()
            return df
            
        except Exception as e:
            print(f"Failed to get tickets: {str(e)}")
            return pd.DataFrame()
    
    def get_processed_tickets(self, status_filter=None, limit=50):
        """Get processed tickets with analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
                SELECT pt.*, t.summary, t.category, t.priority, t.description
                FROM processed_tickets pt
                JOIN tickets t ON pt.ticket_id = t.id
            '''
            
            if status_filter:
                query += " WHERE pt.status = ?"
                params = (status_filter,)
            else:
                params = ()
            
            query += " ORDER BY pt.processed_date DESC LIMIT ?"
            params += (limit,)
            
            df = pd.read_sql_query(query, conn, params=params)
            
            # Parse analysis JSON
            if not df.empty:
                df['analysis_parsed'] = df['analysis'].apply(
                    lambda x: json.loads(x) if x else {}
                )
            
            conn.close()
            return df
            
        except Exception as e:
            print(f"Failed to get processed tickets: {str(e)}")
            return pd.DataFrame()
    
    def save_feedback(self, ticket_id, agent_id, rating, action, comments):
        """Save agent feedback"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            conn.execute('''
                INSERT INTO agent_feedback 
                (ticket_id, agent_id, rating, action, comments, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ticket_id, agent_id, rating, action, comments, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Failed to save feedback: {str(e)}")
            return False
    
    def get_dashboard_metrics(self):
        """Get metrics for dashboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            metrics = {}
            
            # Total tickets
            result = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()
            metrics['total_tickets'] = result[0] if result else 0
            
            # Processed tickets
            result = conn.execute("SELECT COUNT(*) FROM processed_tickets").fetchone()
            metrics['processed_tickets'] = result[0] if result else 0
            
            # Average confidence
            result = conn.execute("SELECT AVG(confidence) FROM processed_tickets").fetchone()
            metrics['avg_confidence'] = result[0] if result and result[0] else 0
            
            # Pending tickets
            metrics['pending_tickets'] = metrics['total_tickets'] - metrics['processed_tickets']
            
            # Recent feedback
            feedback_result = conn.execute('''
                SELECT AVG(rating) FROM agent_feedback 
                WHERE timestamp > datetime('now', '-7 days')
            ''').fetchone()
            metrics['avg_feedback'] = feedback_result[0] if feedback_result and feedback_result[0] else 0
            
            conn.close()
            return metrics
            
        except Exception as e:
            print(f"Failed to get metrics: {str(e)}")
            return {
                'total_tickets': 0,
                'processed_tickets': 0,
                'avg_confidence': 0,
                'pending_tickets': 0,
                'avg_feedback': 0
            }
    
    def log_system_event(self, function_name, status, details=""):
        """Log system events"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            conn.execute('''
                INSERT INTO system_logs (timestamp, function_name, status, details)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), function_name, status, details))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Don't show error for logging failures
            pass