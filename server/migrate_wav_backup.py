"""
Database migration script to add wav_backup_path column to Meeting table

This script adds the wav_backup_path column to store WAV backup file paths
"""

from sqlalchemy import create_engine, text
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_add_wav_backup_path():
    """Add wav_backup_path column to Meeting table"""
    
    try:
        # Create database engine
        engine = create_engine(settings.database_url)
        
        with engine.connect() as connection:
            # Check if column already exists
            check_query = text("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'meetings'
                AND COLUMN_NAME = 'wav_backup_path'
            """)
            
            result = connection.execute(check_query)
            row = result.fetchone()
            
            if row[0] > 0:
                logger.info("✅ Column 'wav_backup_path' already exists in 'meetings' table")
                return True
            
            # Add the column
            alter_query = text("""
                ALTER TABLE meetings
                ADD wav_backup_path NVARCHAR(500) NULL
            """)
            
            connection.execute(alter_query)
            connection.commit()
            
            logger.info("✅ Successfully added 'wav_backup_path' column to 'meetings' table")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error adding wav_backup_path column: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting database migration: Add wav_backup_path column")
    success = migrate_add_wav_backup_path()
    
    if success:
        logger.info("✅ Migration completed successfully")
    else:
        logger.error("❌ Migration failed")
