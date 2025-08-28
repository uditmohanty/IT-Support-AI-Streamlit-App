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
            params = {
                'host': parsed.hostname,
                'database': parsed.path[1:] if parsed.path else 'neondb',
                'user': parsed.username,
                'password': parsed.password,
                'port': parsed.port or 5432
            }
            
            # Add SSL mode for Neon (required)
            if 'sslmode=require' in self.database_url:
                params['ssl_context'] = True
                
            return params
        else:
            # Fallback to individual parameters
            try:
                return {
                    'host': st.secrets.get("NEON_HOST", os.getenv("NEON_HOST")),
                    'database': st.secrets.get("NEON_DATABASE", os.getenv("NEON_DATABASE", "neondb")),
                    'user': st.secrets.get("NEON_USER", os.getenv("NEON_USER")),
                    'password': st.secrets.get("NEON_PASSWORD", os.getenv("NEON_PASSWORD")),
                    'port': int(st.secrets.get("NEON_PORT", os.getenv("NEON_PORT", "5432"))),
                    'ssl_context': True
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
        try:
            return pg8000.connect(**self.connection_params)
        except Exception as e:
            # Try without SSL context if it fails
            params_no_ssl = self.connection_params.copy()
            params_no_ssl.pop('ssl_context', None)
            return pg8000.connect(**params_no_ssl)
    
    def save_tickets(self, tickets):
        """Save tickets to database"""
        if not tickets:
            return True
            
        conn = None
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
            return True
            
        except Exception as e:
            st.error(f"Failed to save tickets: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def save_processed_ticket(self, ticket_id, analysis):
        """Save processed ticket analysis"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            processed_id = f"processed_{ticket_id}_{int(datetime.now().timestamp())}"
            
            # Ensure analysis is properly serialized
            analysis_json = json.dumps(analysis) if isinstance(analysis, dict) else str(analysis)
            
            cursor.execute('''
                INSERT INTO processed_tickets 
                (id, ticket_id, analysis, confidence, processed_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', [
                processed_id,
                ticket_id,
                analysis_json,
                analysis.get('confidence', 0.5) if isinstance(analysis, dict) else 0.5,
                datetime.now(),
                'pending'
            ])
            
            conn.commit()
            return True
            
        except Exception as e:
            st.error(f"Failed to save processed ticket: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def get_tickets(self, status_filter=None, limit=100):
        """Get tickets from database"""
        conn = None
        try:
            conn = self.get_connection()
            
            if status_filter:
                query = "SELECT * FROM tickets WHERE status = %s ORDER BY created DESC LIMIT %s"
                df = pd.read_sql_query(query, conn, params=[status_filter, limit])
            else:
                query = "SELECT * FROM tickets ORDER BY created DESC LIMIT %s"
                df = pd.read_sql_query(query, conn, params=[limit])
            
            return df
            
        except Exception as e:
            st.error(f"Failed to get tickets: {str(e)}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
    
    def get_processed_tickets(self, status_filter=None, limit=50):
        """Get processed tickets with analysis"""
        conn = None
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
            
            # Safe JSON parsing with proper error handling
            if not df.empty:
                def safe_json_parse(x):
                    """Safely parse JSON data from various formats"""
                    if pd.isna(x) or x is None:
                        return {}
                    
                    try:
                        # If it's already a dict, return it
                        if isinstance(x, dict):
                            return x
                        
                        # If it's a string, parse it
                        if isinstance(x, str):
                            if x.strip() == '':
                                return {}
                            return json.loads(x)
                        
                        # If it's bytes, decode and parse
                        if isinstance(x, (bytes, bytearray)):
                            return json.loads(x.decode('utf-8'))
                        
                        # Try to convert to string and parse
                        return json.loads(str(x))
                        
                    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
                        # If all else fails, return empty dict
                        return {}
                
                df['analysis_parsed'] = df['analysis'].apply(safe_json_parse)
            
            return df
            
        except Exception as e:
            st.error(f"Failed to get processed tickets: {str(e)}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
    
    def save_feedback(self, ticket_id, agent_id, rating, action, comments):
        """Save agent feedback"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO agent_feedback 
                (ticket_id, agent_id, rating, action, comments, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', [ticket_id, agent_id, rating, action, comments, datetime.now()])
            
            conn.commit()
            return True
            
        except Exception as e:
            st.error(f"Failed to save feedback: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def get_dashboard_metrics(self):
        """Get metrics for dashboard with proper error handling"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            metrics = {
                'total_tickets': 0,
                'processed_tickets': 0,
                'avg_confidence': 0,
                'pending_tickets': 0,
                'avg_feedback': 0
            }
            
            # Total tickets
            try:
                cursor.execute("SELECT COUNT(*) FROM tickets")
                result = cursor.fetchone()
                metrics['total_tickets'] = result[0] if result else 0
            except Exception:
                metrics['total_tickets'] = 0
            
            # Processed tickets
            try:
                cursor.execute("SELECT COUNT(*) FROM processed_tickets")
                result = cursor.fetchone()
                metrics['processed_tickets'] = result[0] if result else 0
            except Exception:
                metrics['processed_tickets'] = 0
            
            # Average confidence
            try:
                cursor.execute("SELECT AVG(confidence) FROM processed_tickets WHERE confidence IS NOT NULL")
                result = cursor.fetchone()
                if result and result[0] is not None:
                    metrics['avg_confidence'] = float(result[0])
                else:
                    metrics['avg_confidence'] = 0
            except Exception:
                metrics['avg_confidence'] = 0
            
            # Pending tickets (ensure non-negative)
            metrics['pending_tickets'] = max(0, metrics['total_tickets'] - metrics['processed_tickets'])
            
            # Recent feedback average
            try:
                cursor.execute('''
                    SELECT AVG(rating) FROM agent_feedback 
                    WHERE timestamp > NOW() - INTERVAL '7 days' AND rating IS NOT NULL
                ''')
                result = cursor.fetchone()
                if result and result[0] is not None:
                    metrics['avg_feedback'] = float(result[0])
                else:
                    metrics['avg_feedback'] = 0
            except Exception:
                # Fallback query for databases that don't support INTERVAL
                try:
                    cursor.execute('''
                        SELECT AVG(rating) FROM agent_feedback 
                        WHERE rating IS NOT NULL
                    ''')
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        metrics['avg_feedback'] = float(result[0])
                    else:
                        metrics['avg_feedback'] = 0
                except Exception:
                    metrics['avg_feedback'] = 0
            
            return metrics
            
        except Exception as e:
            st.error(f"Failed to get metrics: {str(e)}")
            return {
                'total_tickets': 0,
                'processed_tickets': 0,
                'avg_confidence': 0,
                'pending_tickets': 0,
                'avg_feedback': 0
            }
        finally:
            if conn:
                conn.close()
    
    def log_system_event(self, function_name, status, details=""):
        """Log system events"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_logs (timestamp, function_name, status, details)
                VALUES (%s, %s, %s, %s)
            ''', [datetime.now(), function_name, status, details])
            
            conn.commit()
            
        except Exception:
            # Don't show error for logging failures, but still ensure cleanup
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    
    def cleanup_orphaned_processed_tickets(self):
        """Clean up processed tickets that reference non-existent tickets"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM processed_tickets 
                WHERE ticket_id NOT IN (SELECT id FROM tickets)
            ''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                st.info(f"Cleaned up {deleted_count} orphaned processed tickets")
            
            return deleted_count
            
        except Exception as e:
            st.error(f"Failed to cleanup orphaned tickets: {str(e)}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_ticket_by_id(self, ticket_id):
        """Get a specific ticket by ID"""
        conn = None
        try:
            conn = self.get_connection()
            
            query = "SELECT * FROM tickets WHERE id = %s"
            df = pd.read_sql_query(query, conn, params=[ticket_id])
            
            return df.iloc[0].to_dict() if not df.empty else None
            
        except Exception as e:
            st.error(f"Failed to get ticket {ticket_id}: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()