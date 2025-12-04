"""
Veritabanı Migration Scripti
Transcripts tablosuna speaker_id ve speaker_label kolonlarını ekler
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# .env dosyasını yükle
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Database URL'i environment'tan al
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("[ERROR] DATABASE_URL environment variable bulunamadi!")
    print("[INFO] .env dosyasinda DATABASE_URL tanimli olmali.")
    sys.exit(1)

def migrate_database():
    """Transcripts tablosuna yeni kolonları ekle"""
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Transaction başlat
            trans = conn.begin()
            
            try:
                # Kolonların var olup olmadığını kontrol et (SQL Server için)
                check_speaker_id = text("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'transcripts' 
                    AND COLUMN_NAME = 'speaker_id'
                """)
                
                result = conn.execute(check_speaker_id).fetchone()
                
                if result[0] == 0:
                    # speaker_id kolonunu ekle
                    print("[INFO] speaker_id kolonu ekleniyor...")
                    conn.execute(text("""
                        ALTER TABLE transcripts 
                        ADD speaker_id NVARCHAR(50) NULL
                    """))
                    print("[OK] speaker_id kolonu eklendi")
                else:
                    print("[INFO] speaker_id kolonu zaten mevcut")
                
                # speaker_label kontrolü
                check_speaker_label = text("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'transcripts' 
                    AND COLUMN_NAME = 'speaker_label'
                """)
                
                result = conn.execute(check_speaker_label).fetchone()
                
                if result[0] == 0:
                    # speaker_label kolonunu ekle
                    print("[INFO] speaker_label kolonu ekleniyor...")
                    conn.execute(text("""
                        ALTER TABLE transcripts 
                        ADD speaker_label NVARCHAR(100) NULL
                    """))
                    print("[OK] speaker_label kolonu eklendi")
                else:
                    print("[INFO] speaker_label kolonu zaten mevcut")
                
                # Commit transaction
                trans.commit()
                print("[OK] Migration basariyla tamamlandi!")
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                print(f"[ERROR] Hata olustu: {e}")
                raise
                
    except Exception as e:
        print(f"[ERROR] Veritabani baglanti hatasi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("[INFO] Veritabani migration baslatiliyor...")
    migrate_database()

