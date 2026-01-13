from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

Base = declarative_base()

class Currency(enum.Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class InvoiceStatus(enum.Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, unique=True, nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="EUR")  # Storing enum as string for simplicity in SQLite
    customer_name = Column(String, nullable=False)
    status = Column(String, default="UNPAID")

    def __repr__(self):
        return f"<Invoice(number='{self.invoice_number}', amount={self.amount}, customer='{self.customer_name}')>"

class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="EUR")
    description = Column(String)
    reference_id = Column(String, unique=True) # Bank Transaction ID
    
    def __repr__(self):
        return f"<Payment(amount={self.amount}, date='{self.date}', ref='{self.reference_id}')>"

class ReconciliationResult(Base):
    __tablename__ = 'reconciliation_results'
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, nullable=False) # FK to invoices.id
    payment_id = Column(Integer, nullable=False) # FK to payments.id
    confidence_score = Column(Float, default=1.0)
    match_date = Column(Date, nullable=False)
    
    def __repr__(self):
        return f"<Match(Inv={self.invoice_id}, Pay={self.payment_id}, Score={self.confidence_score})>"

# Database setup
DATABASE_URL = "sqlite:///../data/project.db"

def get_engine(db_path="data/project.db"):
    # Ensure absolute path or correct relative path handling
    return create_engine(f"sqlite:///{db_path}")

def init_db(engine):
    Base.metadata.create_all(engine)
