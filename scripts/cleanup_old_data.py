import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.repository import Repository
from src.config import DATABASE_URL

def cleanup_old_data(days_threshold=30):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        repository = Repository(session)
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
        old_records = repository.get_old_records(cutoff_date)
        
        for record in old_records:
            repository.delete_record(record)
            print(f"Deleted record: {record.id} - {record.name}")
        
        session.commit()
        print("Cleanup completed.")
    except Exception as e:
        session.rollback()
        print(f"An error occurred during cleanup: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_old_data()