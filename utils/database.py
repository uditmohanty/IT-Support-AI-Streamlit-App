import pg8000
import pandas as pd
import json
from datetime import datetime
import streamlit as st
import os
from urllib.parse import urlparse

class Database:
    def __init__(self):
        self.database_url = self._get_database_url()
        self.connection_params = self._get_connection_params()
        self._test_connection()
    
    def _get_database_url(self):
        """Get direct database URL connection string"""
        try:
            # Try Streamlit secrets first, then environment variables
            return st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL"))
        except Exception:
            return os.getenv("DATABASE_URL")
    
    def _get_connection_params(self):
        """Get database connection parameters"""
        if self.database_url:
            # Parse the database URL
            parsed = urlparse(self.database_url)
            return {
                'host': parsed.hostname,
                'database': parsed.path[1:] if parsed.path else 'postgres',
                'user': parsed.username,
                'password': parsed.password,
                'port': parsed.port or 5432
            }
        else:
            # Try to get from Streamlit secrets first, then environment variables
            try:
                return {
                    'host': st.secrets.get("SUPABASE_HOST", os.getenv("SUPABASE_HOST")),
                    'database': st.secrets.get("SUPABASE_DATABASE", os.getenv("SUPABASE_DATABASE", "postgres")),
                    'user': st.secrets.get("SUPABASE_USER", os.getenv("SUPABASE_USER", "postgres")),
                    'password': st.secrets.get("SUPABASE_PASSWORD", os.getenv("SUPABASE_PASSWORD")),
                    'port': int(st.secrets.get("SUPABASE_PORT", os.getenv("SUPABASE_PORT", "5432")))
                }
            except Exception as e:
                st.error(f"Failed to get database credentials: {str(e)}")
                return {}
    
    def _test_connection(self):
        """Test database connection"""
        try:
            conn = self.get_connection()
            conn.close()
        except Exception as e:
            st.error(f"Database connection failed: {str(e)}")
    
    def get_connection(self):
        """Get database connection"""
        return pg8000.connect(**self.connection_params)
    
    def save_tickets(self, tickets):
        """Save tickets to database"""
        if not tickets:
            return True
            
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for ticket in tickets:
                # Convert datetime strings to proper format
                created = ticket.get('created')
                updated = ticket.get('updated')
                
                cursor.execute('''
                    INSERT INTO tickets 
                    (id, summary, description, category, priority, status, reporter, created, updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        priority = EXCLUDED.priority,
                        status = EXCLUDED.status,
                        reporter = EXCLUDED.reporter,
                        updated = EXCLUDED.updated
                ''', [
                    ticket['id'], ticket['summary'], ticket['description'],
                    ticket['category'], ticket['priority'], ticket['status'],
                    ticket['reporter'], created, updated
                ])
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Failed to save tickets: {str(e)}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def save_processed_ticket(self, ticket_id, analysis):
        """Save processed ticket analysis"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            processed_id = f"processed_{ticket_id}_{int(datetime.now().timestamp())}"
            
            cursor.execute('''
                INSERT INTO processed_tickets 
                (id, ticket_id, analysis, confidence, processed_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', [
                processed_id,
                ticket_id,
                json.dumps(analysis),
                analysis.get('confidence', 0.5),
                datetime.now(),
                'pending'
            ])
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Failed to save processed ticket: {str(e)}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def get_tickets(self, status_filter=None, limit=100):
        """Get tickets from database"""
        try:
            conn = self.get_connection()
            
            if status_filter:
                query = "SELECT * FROM tickets WHERE status = %s ORDER BY created DESC LIMIT %s"
                df = pd.read_sql_query(query, conn, params=[status_filter, limit])
            else:
                query = "SELECT * FROM tickets ORDER BY created DESC LIMIT %s"
                df = pd.read_sql_query(query, conn, params=[limit])
            
            conn.close()
            return df
            
        except Exception as e:
            st.error(f"Failed to get tickets: {str(e)}")
            if 'conn' in locals():
                conn.close()
            return pd.DataFrame()
    
    def get_processed_tickets(self, status_filter=None, limit=50):
        """Get processed tickets with analysis"""
        try:
            conn = self.get_connection()
            
            query = '''
                SELECT pt.*, t.summary, t.category, t.priority, t.description
                FROM processed_tickets pt
                JOIN tickets t ON pt.ticket_id = t.id
            '''
            
            params = []
            if status_filter:
                query += " WHERE pt.status = %s"
                params.append(status_filter)
            
            query += " ORDER BY pt.processed_date DESC LIMIT %s"
            params.append(limit)
            
            df = pd.read_sql_query(query, conn, params=params)
            
            # Parse analysis JSON
            if not df.empty:
                df['analysis_parsed'] = df['analysis'].apply(
                    lambda x: json.loads(x) if x else {}
                )
            
            conn.close()
            return df
            
        except Exception as e:
            st.error(f"Failed to get processed tickets: {str(e)}")
            if 'conn' in locals():
                conn.close()
            return pd.DataFrame()
    
    def save_feedback(self, ticket_id, agent_id, rating, action, comments):
        """Save agent feedback"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO agent_feedback 
                (ticket_id, agent_id, rating, action, comments, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', [ticket_id, agent_id, rating, action, comments, datetime.now()])
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Failed to save feedback: {str(e)}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def get_dashboard_metrics(self):
        """Get metrics for dashboard"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            metrics = {}
            
            # Total tickets
            cursor.execute("SELECT COUNT(*) FROM tickets")
            metrics['total_tickets'] = cursor.fetchone()[0]
            
            # Processed tickets
            cursor.execute("SELECT COUNT(*) FROM processed_tickets")
            metrics['processed_tickets'] = cursor.fetchone()[0]
            
            # Average confidence
            cursor.execute("SELECT AVG(confidence) FROM processed_tickets")
            result = cursor.fetchone()[0]
            metrics['avg_confidence'] = float(result) if result else 0
            
            # Pending tickets
            metrics['pending_tickets'] = metrics['total_tickets'] - metrics['processed_tickets']
            
            # Recent feedback average
            cursor.execute('''
                SELECT AVG(rating) FROM agent_feedback 
                WHERE timestamp > NOW() - INTERVAL '7 days'
            ''')
            result = cursor.fetchone()[0]
            metrics['avg_feedback'] = float(result) if result else 0
            
            conn.close()
            return metrics
            
        except Exception as e:
            st.error(f"Failed to get metrics: {str(e)}")
            if 'conn' in locals():
                conn.close()
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
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_logs (timestamp, function_name, status, details)
                VALUES (%s, %s, %s, %s)
            ''', [datetime.now(), function_name, status, details])
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Don't show error for logging failures
            pass