from utils.database import Database

def check_data_integrity():
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    print("=== DATA INTEGRITY CHECK ===")
    
    # Count actual tickets
    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]
    print(f"Total tickets: {total_tickets}")
    
    # Count processed tickets
    cursor.execute("SELECT COUNT(*) FROM processed_tickets")
    processed_count = cursor.fetchone()[0]
    print(f"Processed ticket records: {processed_count}")
    
    # Count unique ticket IDs in processed tickets
    cursor.execute("SELECT COUNT(DISTINCT ticket_id) FROM processed_tickets")
    unique_processed = cursor.fetchone()[0]
    print(f"Unique tickets processed: {unique_processed}")
    
    # Find orphaned processed tickets
    cursor.execute("""
        SELECT ticket_id, COUNT(*) as count 
        FROM processed_tickets 
        WHERE ticket_id NOT IN (SELECT id FROM tickets)
        GROUP BY ticket_id
    """)
    orphaned = cursor.fetchall()
    if orphaned:
        print(f"\nOrphaned processed tickets: {len(orphaned)}")
        for ticket_id, count in orphaned:
            print(f"  {ticket_id}: {count} records")
    
    # Find duplicate processed tickets
    cursor.execute("""
        SELECT ticket_id, COUNT(*) as count 
        FROM processed_tickets 
        GROUP BY ticket_id 
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"\nDuplicate processed tickets:")
        for ticket_id, count in duplicates:
            print(f"  {ticket_id}: {count} records")
    
    conn.close()

if __name__ == "__main__":
    check_data_integrity()