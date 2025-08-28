import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from config import Config
from utils.jira_client import JiraClient
from utils.ai_analyzer import AIAnalyzer
from utils.database import Database

# Configure Streamlit
st.set_page_config(
    page_title=Config.PAGE_TITLE,
    page_icon=Config.PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def init_components():
    return {
        'jira': JiraClient(),
        'ai': AIAnalyzer(),
        'db': Database()
    }

def test_database_connection():
    """Test database connection"""
    try:
        db = Database()
        metrics = db.get_dashboard_metrics()
        return True, "Database connected successfully"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

def check_data_integrity(db):
    """Check database data integrity"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Count actual tickets
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = cursor.fetchone()[0]
        
        # Count processed tickets
        cursor.execute("SELECT COUNT(*) FROM processed_tickets")
        processed_count = cursor.fetchone()[0]
        
        # Count unique ticket IDs in processed tickets
        cursor.execute("SELECT COUNT(DISTINCT ticket_id) FROM processed_tickets")
        unique_processed = cursor.fetchone()[0]
        
        # Find duplicates
        cursor.execute("""
            SELECT ticket_id, COUNT(*) as count 
            FROM processed_tickets 
            GROUP BY ticket_id 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_tickets': total_tickets,
            'processed_count': processed_count,
            'unique_processed': unique_processed,
            'duplicates': duplicates
        }
    except Exception as e:
        st.error(f"Failed to check data integrity: {str(e)}")
        return None

def clean_database(db):
    """Clean duplicate processed tickets"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Remove duplicates (keep only the latest)
        cursor.execute("""
            DELETE FROM processed_tickets 
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT MAX(id) as id
                    FROM processed_tickets 
                    GROUP BY ticket_id
                ) as latest
            )
        """)
        
        duplicates_removed = cursor.rowcount
        conn.commit()
        conn.close()
        
        return duplicates_removed
    except Exception as e:
        st.error(f"Failed to clean database: {str(e)}")
        return 0

def reset_processed_tickets(db):
    """Reset all processed tickets"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM processed_tickets")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Failed to reset processed tickets: {str(e)}")
        return False

def main():
    components = init_components()
    
    # Sidebar
    with st.sidebar:
        st.title("IT Support AI")
        st.markdown("---")
        
        # Quick Actions
        st.subheader("Quick Actions")
        
        if st.button("Fetch New Tickets"):
            fetch_tickets(components)
        
        if st.button("Analyze Tickets"):
            analyze_tickets(components)
        
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        # Add database test button
        if st.button("Test Database"):
            success, message = test_database_connection()
            if success:
                st.success(message)
            else:
                st.error(message)
        
        st.markdown("---")
        
        # Database Maintenance
        st.subheader("Database Maintenance")
        
        if st.button("🔍 Check Data Integrity"):
            with st.spinner("Checking data integrity..."):
                integrity_data = check_data_integrity(components['db'])
                
                if integrity_data:
                    st.write(f"**Total tickets:** {integrity_data['total_tickets']}")
                    st.write(f"**Processed records:** {integrity_data['processed_count']}")
                    st.write(f"**Unique tickets processed:** {integrity_data['unique_processed']}")
                    
                    if integrity_data['duplicates']:
                        st.warning(f"**Duplicate records found:** {len(integrity_data['duplicates'])}")
                        with st.expander("View duplicates"):
                            for ticket_id, count in integrity_data['duplicates']:
                                st.write(f"- {ticket_id}: {count} records")
                    else:
                        st.success("No duplicates found!")
        
        if st.button("🧹 Clean Database"):
            with st.spinner("Cleaning database..."):
                duplicates_removed = clean_database(components['db'])
                if duplicates_removed > 0:
                    st.success(f"Cleaned up {duplicates_removed} duplicate processed tickets")
                    components['db'].log_system_event("clean_database", "SUCCESS", f"Removed {duplicates_removed} duplicates")
                    st.rerun()
                else:
                    st.info("No duplicates to clean")
        
        if st.button("🔄 Reset All Processed Tickets"):
            if st.session_state.get('confirm_reset', False):
                with st.spinner("Resetting processed tickets..."):
                    if reset_processed_tickets(components['db']):
                        st.success("All processed ticket records cleared")
                        components['db'].log_system_event("reset_processed", "SUCCESS", "All processed tickets cleared")
                        st.session_state.confirm_reset = False
                        st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("⚠️ This will delete ALL processed ticket data. Click again to confirm.")
        
        st.markdown("---")
        
        # System Status
        st.subheader("System Status")
        show_system_status(components)
    
    # Main content
    st.title("IT Support AI Dashboard")
    
    # Metrics row
    show_metrics(components['db'])
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Active Tickets", "AI Analysis", "Analytics"])
    
    with tab1:
        show_overview(components['db'])
    
    with tab2:
        show_active_tickets(components['db'])
    
    with tab3:
        show_ai_analysis(components)
    
    with tab4:
        show_analytics(components['db'])

def fetch_tickets(components):
    """Fetch tickets from Jira"""
    with st.spinner("Fetching tickets from Jira..."):
        try:
            result = components['jira'].fetch_tickets()
            
            if result['success']:
                if components['db'].save_tickets(result['tickets']):
                    st.success(f"Fetched and saved {result['count']} tickets")
                    components['db'].log_system_event("fetch_tickets", "SUCCESS", f"Fetched {result['count']} tickets")
                else:
                    st.error("Failed to save tickets to database")
                    components['db'].log_system_event("fetch_tickets", "ERROR", "Failed to save tickets")
            else:
                st.error(f"Failed to fetch tickets: {result['error']}")
                components['db'].log_system_event("fetch_tickets", "ERROR", result['error'])
        except Exception as e:
            st.error(f"Error fetching tickets: {str(e)}")
            components['db'].log_system_event("fetch_tickets", "ERROR", str(e))

def analyze_tickets(components):
    """Analyze tickets with AI"""
    try:
        # Get unprocessed tickets
        all_tickets = components['db'].get_tickets()
        processed_tickets = components['db'].get_processed_tickets()
        
        processed_ids = set(processed_tickets['ticket_id'].tolist()) if not processed_tickets.empty else set()
        unprocessed = all_tickets[~all_tickets['id'].isin(processed_ids)]
        
        if unprocessed.empty:
            st.info("No unprocessed tickets found")
            return
        
        with st.spinner(f"Analyzing {len(unprocessed)} tickets with AI..."):
            # Convert to list of dicts
            tickets_to_analyze = unprocessed.to_dict('records')
            
            # Analyze tickets
            results = components['ai'].analyze_tickets_batch(tickets_to_analyze)
            
            # Save results
            success_count = 0
            error_count = 0
            
            for result in results:
                if result['success']:
                    if components['db'].save_processed_ticket(result['ticket_id'], result['analysis']):
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1
            
            if success_count > 0:
                st.success(f"Successfully analyzed {success_count} tickets")
                components['db'].log_system_event("analyze_tickets", "SUCCESS", f"Analyzed {success_count} tickets")
            
            if error_count > 0:
                st.warning(f"Failed to analyze {error_count} tickets")
                components['db'].log_system_event("analyze_tickets", "PARTIAL", f"Failed {error_count} tickets")
                
    except Exception as e:
        st.error(f"Error analyzing tickets: {str(e)}")
        components['db'].log_system_event("analyze_tickets", "ERROR", str(e))

def show_system_status(components):
    """Show system status indicators"""
    # Test Jira connection
    try:
        tickets = components['db'].get_tickets(limit=1)
        jira_status = "🟢 Connected" if not tickets.empty else "🟡 No Data"
    except Exception as e:
        jira_status = "🔴 Error"
    
    st.write(f"**Jira:** {jira_status}")
    
    # Test AI
    try:
        # Simple test - create a dummy ticket
        test_ticket = {
            'id': 'TEST-1',
            'summary': 'Test ticket',
            'description': 'Test description',
            'category': 'General',
            'priority': 'Low'
        }
        ai_result = components['ai'].analyze_ticket(test_ticket)
        ai_status = "🟢 Ready" if ai_result.get('success', False) else "🔴 Error"
    except Exception as e:
        ai_status = "🔴 Error"
    
    st.write(f"**AI:** {ai_status}")
    
    # Database status
    try:
        metrics = components['db'].get_dashboard_metrics()
        db_status = "🟢 Connected"
    except Exception as e:
        db_status = "🔴 Error"
    
    st.write(f"**Database:** {db_status}")

def show_metrics(db):
    """Show dashboard metrics"""
    try:
        metrics = db.get_dashboard_metrics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Tickets",
                value=metrics['total_tickets']
            )
        
        with col2:
            st.metric(
                label="AI Processed",
                value=metrics['processed_tickets']
            )
        
        with col3:
            avg_conf = metrics.get('avg_confidence', 0)
            st.metric(
                label="Avg Confidence",
                value=f"{avg_conf:.1%}" if avg_conf else "N/A"
            )
        
        with col4:
            st.metric(
                label="Pending",
                value=metrics['pending_tickets']
            )
    except Exception as e:
        st.error(f"Failed to load metrics: {str(e)}")

def show_overview(db):
    """Show overview dashboard"""
    st.subheader("System Overview")
    
    try:
        # Recent tickets
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Recent Tickets**")
            recent_tickets = db.get_tickets(limit=10)
            if not recent_tickets.empty:
                st.dataframe(
                    recent_tickets[['id', 'summary', 'category', 'priority', 'status']],
                    use_container_width=True
                )
            else:
                st.info("No tickets found")
        
        with col2:
            st.write("**Category Distribution**")
            if not recent_tickets.empty:
                category_counts = recent_tickets['category'].value_counts()
                fig = px.pie(values=category_counts.values, names=category_counts.index)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for chart")
    except Exception as e:
        st.error(f"Failed to load overview: {str(e)}")

def show_active_tickets(db):
    """Show active tickets management"""
    st.subheader("Active Tickets")
    
    try:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox("Status", ["All", "Open", "In Progress", "To Do"])
        
        with col2:
            category_filter = st.selectbox("Category", ["All"] + Config.TICKET_CATEGORIES)
        
        with col3:
            priority_filter = st.selectbox("Priority", ["All"] + Config.PRIORITIES)
        
        # Get tickets
        tickets = db.get_tickets(limit=100)
        
        if not tickets.empty:
            # Apply filters
            if status_filter != "All":
                tickets = tickets[tickets['status'] == status_filter]
            if category_filter != "All":
                tickets = tickets[tickets['category'] == category_filter]
            if priority_filter != "All":
                tickets = tickets[tickets['priority'] == priority_filter]
            
            # Display tickets
            st.dataframe(
                tickets[['id', 'summary', 'category', 'priority', 'status', 'reporter', 'created']],
                use_container_width=True
            )
            
            # Ticket details
            if not tickets.empty:
                selected_ticket = st.selectbox("Select ticket for details:", tickets['id'].tolist())
                
                if selected_ticket:
                    ticket_details = tickets[tickets['id'] == selected_ticket].iloc[0]
                    
                    with st.expander(f"Details for {selected_ticket}", expanded=True):
                        st.write(f"**Summary:** {ticket_details['summary']}")
                        st.write(f"**Description:** {ticket_details['description']}")
                        st.write(f"**Status:** {ticket_details['status']}")
                        st.write(f"**Priority:** {ticket_details['priority']}")
                        st.write(f"**Category:** {ticket_details['category']}")
                        st.write(f"**Reporter:** {ticket_details['reporter']}")
        else:
            st.info("No active tickets found")
    except Exception as e:
        st.error(f"Failed to load active tickets: {str(e)}")

def show_ai_analysis(components):
    """Show AI analysis results"""
    st.subheader("AI Analysis Results")
    
    try:
        processed_tickets = components['db'].get_processed_tickets()
        
        if not processed_tickets.empty:
            for _, ticket in processed_tickets.iterrows():
                analysis = ticket['analysis_parsed']
                
                with st.expander(f"{ticket['ticket_id']} - {ticket['summary']}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**AI Category:** {analysis.get('category', 'Unknown')}")
                        st.write(f"**AI Priority:** {analysis.get('priority', 'Unknown')}")
                        st.write(f"**Confidence:** {analysis.get('confidence', 0):.1%}")
                        st.write(f"**Risk Assessment:** {analysis.get('risk_assessment', 'Unknown')}")
                    
                    with col2:
                        st.write(f"**Urgency Score:** {analysis.get('urgency_score', 'Unknown')}/10")
                        st.write(f"**Complexity Score:** {analysis.get('complexity_score', 'Unknown')}/10")
                        st.write(f"**Est. Resolution:** {analysis.get('estimated_resolution_time', 'Unknown')}")
                    
                    # Suggested solutions
                    st.write("**Suggested Solutions:**")
                    solutions = analysis.get('suggested_solutions', [])
                    
                    for i, solution in enumerate(solutions, 1):
                        st.write(f"**Solution {i}:** {solution.get('title', 'Unknown')}")
                        steps = solution.get('steps', [])
                        for step in steps:
                            st.write(f"  • {step}")
                        st.write(f"  Confidence: {solution.get('confidence', 0):.1%} | Time: {solution.get('estimated_time', 'Unknown')}")
                    
                    # Feedback buttons
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button(f"✅ Apply", key=f"apply_{ticket['ticket_id']}"):
                            save_feedback(components, ticket['ticket_id'], 5, "Applied", "Applied AI suggestion")
                    
                    with col2:
                        if st.button(f"✏️ Modify", key=f"modify_{ticket['ticket_id']}"):
                            save_feedback(components, ticket['ticket_id'], 3, "Modified", "Modified AI suggestion")
                    
                    with col3:
                        if st.button(f"❌ Reject", key=f"reject_{ticket['ticket_id']}"):
                            save_feedback(components, ticket['ticket_id'], 1, "Rejected", "Rejected AI suggestion")
                    
                    with col4:
                        if st.button(f"⬆️ Escalate", key=f"escalate_{ticket['ticket_id']}"):
                            save_feedback(components, ticket['ticket_id'], 2, "Escalated", "Escalated for manual review")
        else:
            st.info("No processed tickets found")
    except Exception as e:
        st.error(f"Failed to load AI analysis: {str(e)}")

def save_feedback(components, ticket_id, rating, action, comments):
    """Save agent feedback and update JIRA if needed"""
    try:
        if components['db'].save_feedback(ticket_id, "current_agent", rating, action, comments):
            
            # If applied, update JIRA status
            if action == "Applied":
                success = components['jira'].update_ticket_status(ticket_id, "Done")
                
                if success:
                    st.success(f"Feedback saved and JIRA ticket {ticket_id} marked as Done")
                    components['db'].log_system_event("update_jira", "SUCCESS", f"Updated {ticket_id} to Done")
                else:
                    st.warning(f"Feedback saved but failed to update JIRA ticket {ticket_id}")
                    components['db'].log_system_event("update_jira", "ERROR", f"Failed to update {ticket_id}")
            else:
                st.success(f"Feedback saved for {ticket_id}")
                
            components['db'].log_system_event("save_feedback", "SUCCESS", f"Saved {action} feedback for {ticket_id}")
        else:
            st.error("Failed to save feedback")
            components['db'].log_system_event("save_feedback", "ERROR", f"Failed to save feedback for {ticket_id}")
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        components['db'].log_system_event("save_feedback", "ERROR", str(e))

def show_analytics(db):
    """Show analytics and reports"""
    st.subheader("Analytics & Reports")
    
    try:
        # Time-based metrics
        tickets = db.get_tickets(limit=1000)
        
        if not tickets.empty:
            # Convert created date
            tickets['created_date'] = pd.to_datetime(tickets['created']).dt.date
            
            # Tickets over time
            daily_tickets = tickets.groupby('created_date').size().reset_index(name='count')
            
            fig = px.line(daily_tickets, x='created_date', y='count', title='Tickets Created Over Time')
            st.plotly_chart(fig, use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Category analysis
                category_counts = tickets['category'].value_counts()
                fig = px.bar(x=category_counts.index, y=category_counts.values, title='Tickets by Category')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Priority analysis
                priority_counts = tickets['priority'].value_counts()
                fig = px.bar(x=priority_counts.index, y=priority_counts.values, title='Tickets by Priority')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for analytics")
    except Exception as e:
        st.error(f"Failed to load analytics: {str(e)}")

if __name__ == "__main__":
    main()