"""
Backend başlatma scripti - Model ve FFmpeg kontrolü ile
"""
import os
import sys
import subprocess


def check_ffmpeg():
    """FFmpeg kurulu mu kontrol et"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ FFmpeg kurulu")
            return True
        else:
            return False
    except FileNotFoundError:
        print("\n❌ FFmpeg bulunamadı!")
        print("\n💡 FFmpeg kurulumu gerekli:")
        print("  Windows: choco install ffmpeg")
        print("  Detaylı talimatlar: INSTALL_FFMPEG.md\n")
        return False
    except Exception:
        return False


def check_models():
    """Whisper modeli varlığını kontrol et"""
    models_dir = "./models"
    
    if not os.path.exists(models_dir):
        print("\n⚠ Models klasörü bulunamadı.")
        return False
    
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.pt')]
    
    if not model_files:
        print("\n⚠ Hiç Whisper modeli indirilmemiş.")
        return False
    
    print(f"✓ {len(model_files)} model bulundu: {', '.join([f.replace('.pt', '') for f in model_files])}")
    return True


def main():
    print("="*60)
    print("  MEETING TRANSCRIPT APP - BACKEND BAŞLATILIYOR")
    print("="*60)
    print()
    
    # FFmpeg kontrolü
    if not check_ffmpeg():
        sys.exit(1)
    
    # Model kontrolü
    if not check_models():
        print("\n❌ Whisper modeli bulunamadı!")
        print("\nÇözüm:")
        print("  1. python setup_whisper.py")
        print("  veya")
        print("  2. python download_models.py")
        print("\nKomutlarından birini çalıştırın.\n")
        #sys.exit(1)
    
    # Backend'i başlat
    print("\n🚀 Backend başlatılıyor...\n")
    print("="*60)
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n\n✓ Backend durduruldu.")
    except Exception as e:
        print(f"\n✗ Hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

