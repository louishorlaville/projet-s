"""
Script to clear all reconciliation results from the database.
Run this to reset the reconciliation state.
"""

import sys
import os

# Adapt path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.db.schema import get_engine, ReconciliationResult
from sqlalchemy.orm import Session

def clear_reconciliation_db(db_path='data/project.db'):
    """Clear all records from the reconciliation_results table."""
    engine = get_engine(db_path)
    session = Session(bind=engine)
    
    try:
        # Count existing records
        count = session.query(ReconciliationResult).count()
        
        if count == 0:
            print("✅ Reconciliation database is already empty.")
            return
        
        # Delete all records
        session.query(ReconciliationResult).delete()
        session.commit()
        
        print(f"✅ Successfully deleted {count} reconciliation record(s).")
        print("The reconciliation table is now clean.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error clearing reconciliation database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🧹 Clearing Reconciliation Database...")
    clear_reconciliation_db()
