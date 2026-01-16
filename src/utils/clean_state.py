import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.db.schema import get_engine, Base

def clean_state():
    print("Cleaning Agent State...")
    engine = get_engine('data/project.db')
    
    # Force drop of legacy tables that are no longer in Base
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS invoices"))
        conn.execute(text("DROP TABLE IF EXISTS payments"))
        conn.execute(text("DROP TABLE IF EXISTS reconciliation_results"))
        conn.commit()
    
    # Re-create only what is in schema.py (ReconciliationResult)
    Base.metadata.create_all(engine)
    print("Agent State Reset! Legacy simulation data removed.")

if __name__ == "__main__":
    clean_state()
