from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

Base = declarative_base()

class ReconciliationResult(Base):
    __tablename__ = 'reconciliation_results'
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, nullable=False) # Dolibarr Invoice ID (rowid)
    payment_id = Column(Integer, nullable=False) # Dolibarr Bank Line ID (rowid)
    confidence_score = Column(Float, default=1.0)
    match_date = Column(Date, nullable=False)
    
    def __repr__(self):
        return f"<Match(Inv={self.invoice_id}, Pay={self.payment_id}, Score={self.confidence_score})>"

# Database setup
# Store agent state locally, but logic relies on external data
DATABASE_URL = "sqlite:///../data/project.db"

def get_engine(db_path="data/project.db"):
    # Ensure absolute path or correct relative path handling
    return create_engine(f"sqlite:///{db_path}")

def init_db(engine):
    Base.metadata.create_all(engine)
