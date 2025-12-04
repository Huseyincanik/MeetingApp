"""
Veritabanı Migration Scripti - Pyannote Diarization Alanları
Meetings tablosuna yeni kolonları ekler
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
    """Meetings tablosuna Pyannote diarization kolonlarını ekle"""
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Transaction başlat
            trans = conn.begin()
            
            try:
                # use_pyannote kolonu kontrolü
                check_use_pyannote = text("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'meetings' 
                    AND COLUMN_NAME = 'use_pyannote'
                """)
                
                result = conn.execute(check_use_pyannote).fetchone()
                
                if result[0] == 0:
                    print("[INFO] use_pyannote kolonu ekleniyor...")
                    conn.execute(text("""
                        ALTER TABLE meetings 
                        ADD use_pyannote NVARCHAR(10) NULL
                    """))
                    print("[OK] use_pyannote kolonu eklendi")
                else:
                    print("[INFO] use_pyannote kolonu zaten mevcut")
                
                # diarization_profile kolonu kontrolü
                check_diarization_profile = text("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'meetings' 
                    AND COLUMN_NAME = 'diarization_profile'
                """)
                
                result = conn.execute(check_diarization_profile).fetchone()
                
                if result[0] == 0:
                    print("[INFO] diarization_profile kolonu ekleniyor...")
                    conn.execute(text("""
                        ALTER TABLE meetings 
                        ADD diarization_profile NVARCHAR(50) NULL
                    """))
                    print("[OK] diarization_profile kolonu eklendi")
                else:
                    print("[INFO] diarization_profile kolonu zaten mevcut")
                
                # min_speakers kolonu kontrolü
                check_min_speakers = text("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'meetings' 
                    AND COLUMN_NAME = 'min_speakers'
                """)
                
                result = conn.execute(check_min_speakers).fetchone()
                
                if result[0] == 0:
                    print("[INFO] min_speakers kolonu ekleniyor...")
                    conn.execute(text("""
                        ALTER TABLE meetings 
                        ADD min_speakers INT NULL
                    """))
                    print("[OK] min_speakers kolonu eklendi")
                else:
                    print("[INFO] min_speakers kolonu zaten mevcut")
                
                # max_speakers kolonu kontrolü
                check_max_speakers = text("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'meetings' 
                    AND COLUMN_NAME = 'max_speakers'
                """)
                
                result = conn.execute(check_max_speakers).fetchone()
                
                if result[0] == 0:
                    print("[INFO] max_speakers kolonu ekleniyor...")
                    conn.execute(text("""
                        ALTER TABLE meetings 
                        ADD max_speakers INT NULL
                    """))
                    print("[OK] max_speakers kolonu eklendi")
                else:
                    print("[INFO] max_speakers kolonu zaten mevcut")
                
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
    print("[INFO] Pyannote Diarization migration baslatiliyor...")
    migrate_database()

