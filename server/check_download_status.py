"""
İndirme durumunu kontrol et ve devam eden indirmeleri göster
"""
import os
import sys
from pathlib import Path


def format_size(size_bytes: int) -> str:
    """Byte'ı okunabilir formata çevir"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_file_size(file_path: str) -> int:
    """Dosya boyutunu byte cinsinden döndür"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0


def check_download_status():
    """Mevcut model dosyalarını kontrol et"""
    models_dir = "./models"
    
    if not os.path.exists(models_dir):
        print("❌ Models klasörü bulunamadı.")
        return
    
    print("\n" + "="*60)
    print("  MEVCUT MODEL DOSYALARI")
    print("="*60 + "\n")
    
    pt_files = [f for f in os.listdir(models_dir) if f.endswith('.pt')]
    
    if not pt_files:
        print("⚠️  Henüz model dosyası bulunamadı.\n")
        return
    
    expected_sizes = {
        "tiny": 75 * 1024 * 1024,      # ~75 MB
        "base": 142 * 1024 * 1024,     # ~142 MB
        "small": 466 * 1024 * 1024,    # ~466 MB
        "medium": 1500 * 1024 * 1024,  # ~1.5 GB
        "large": 2900 * 1024 * 1024,   # ~2.9 GB (large-v3)
    }
    
    for file in sorted(pt_files):
        file_path = os.path.join(models_dir, file)
        file_size = get_file_size(file_path)
        
        # Model adını tahmin et
        model_name = file.replace('.pt', '').replace('-v3', '').replace('-v2', '')
        expected_size = expected_sizes.get(model_name, 0)
        
        if expected_size > 0:
            percentage = (file_size / expected_size) * 100
            if percentage >= 95:
                status = "✓ Tamamlanmış"
            elif percentage > 0:
                status = f"⬇️  İndiriliyor (%{percentage:.1f})"
            else:
                status = "⚠️  Çok küçük"
        else:
            status = "❓ Bilinmeyen"
        
        print(f"📁 {file}")
        print(f"   Boyut: {format_size(file_size)}")
        print(f"   Durum: {status}")
        
        if expected_size > 0 and file_size < expected_size * 0.95:
            remaining = expected_size - file_size
            print(f"   ⚠️  Kalan: {format_size(remaining)}")
        
        print()
    
    print("="*60)
    print("\n💡 İpucu:")
    print("   - Eğer indirme donmuş görünüyorsa, Ctrl+C ile iptal edip")
    print("     tekrar indirme scriptini çalıştırın.")
    print("   - Whisper kesintiye uğrayan indirmeleri otomatik olarak devam ettirir.")
    print()


if __name__ == "__main__":
    check_download_status()

