"""
Whisper modellerini manuel olarak indirme scripti
"""
import whisper
import os
import sys
import time
import threading
from pathlib import Path


MODELS = {
    "1": {"name": "tiny", "size": "~75 MB"},
    "2": {"name": "base", "size": "~142 MB"},
    "3": {"name": "small", "size": "~466 MB"},
    "4": {"name": "medium", "size": "~1.5 GB"},
    "5": {"name": "large", "size": "~2.9 GB"},
}


def get_file_size(file_path: str) -> int:
    """Dosya boyutunu byte cinsinden döndür"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0


def format_size(size_bytes: int) -> str:
    """Byte'ı okunabilir formata çevir"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def find_model_file(model_name: str, models_dir: str) -> str:
    """Model dosyasını bul (farklı uzantılar olabilir: .pt, -v3.pt, vb.)"""
    if not os.path.exists(models_dir):
        return None
    
    # Önce tam eşleşmeyi kontrol et
    possible_names = [
        f"{model_name}.pt",
        f"{model_name}-v3.pt",
        f"{model_name}-v2.pt",
    ]
    
    for name in possible_names:
        file_path = os.path.join(models_dir, name)
        if os.path.exists(file_path):
            return file_path
    
    # Eğer bulunamazsa, model_name ile başlayan tüm .pt dosyalarını kontrol et
    for file in os.listdir(models_dir):
        if file.startswith(model_name) and file.endswith('.pt'):
            return os.path.join(models_dir, file)
    
    return None


def monitor_download_progress(model_name: str, models_dir: str):
    """İndirme ilerlemesini izle ve göster"""
    last_size = 0
    stalled_count = 0
    model_file = None
    
    print("\n📊 İndirme İlerlemesi:")
    print("-" * 60)
    
    while True:
        # Model dosyasını bul (indirme sırasında oluşabilir)
        if not model_file:
            model_file = find_model_file(model_name, models_dir)
        
        if model_file and os.path.exists(model_file):
            current_size = get_file_size(model_file)
            
            if current_size > last_size:
                stalled_count = 0
                print(f"  ⬇️  İndiriliyor: {format_size(current_size)}", end='\r')
                last_size = current_size
            else:
                stalled_count += 1
                if stalled_count > 10:  # 20 saniye boyunca değişiklik yoksa
                    print(f"\n  ⚠️  İndirme duraklamış gibi görünüyor (son {stalled_count * 2} saniye)...")
                    print(f"  💡 İnternet bağlantınızı kontrol edin veya Ctrl+C ile iptal edip tekrar deneyin.")
                    stalled_count = 0
        
        time.sleep(2)  # Her 2 saniyede bir kontrol et


def download_model(model_name: str, models_dir: str = "./models", max_retries: int = 3):
    """Belirtilen modeli indir"""
    print(f"\n{'='*60}")
    print(f"📦 Model indiriliyor: {model_name}")
    print(f"📁 Hedef klasör: {os.path.abspath(models_dir)}")
    print(f"{'='*60}\n")
    
    os.makedirs(models_dir, exist_ok=True)
    
    # Mevcut model dosyasını kontrol et
    existing_file = find_model_file(model_name, models_dir)
    if existing_file:
        file_size = get_file_size(existing_file)
        print(f"⚠️  Mevcut dosya bulundu: {os.path.basename(existing_file)} ({format_size(file_size)})")
        print("   Whisper dosyayı kontrol edip gerekirse yeniden indirecek...\n")
    
    # İndirme ilerlemesini izlemek için thread başlat
    progress_thread = threading.Thread(
        target=monitor_download_progress,
        args=(model_name, models_dir),
        daemon=True
    )
    progress_thread.start()
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔄 İndirme denemesi {attempt}/{max_retries}...")
            print("   (Bu işlem büyük modeller için uzun sürebilir, lütfen bekleyin...)\n")
            
            model = whisper.load_model(model_name, download_root=models_dir)
            
            # İndirme başarılı, dosya boyutunu kontrol et
            downloaded_file = find_model_file(model_name, models_dir)
            if downloaded_file:
                final_size = get_file_size(downloaded_file)
                print(f"\n{'='*60}")
                print(f"✓ Model başarıyla indirildi: {model_name}")
                print(f"📦 Dosya: {os.path.basename(downloaded_file)}")
                print(f"📦 Dosya boyutu: {format_size(final_size)}")
                print(f"📁 Konum: {os.path.abspath(downloaded_file)}")
                print(f"{'='*60}\n")
                return True
            else:
                print(f"\n⚠️  Model yüklendi ancak dosya bulunamadı. Tekrar deniyor...")
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️  İndirme kullanıcı tarafından iptal edildi.")
            partial_file = find_model_file(model_name, models_dir)
            if partial_file:
                file_size = get_file_size(partial_file)
                print(f"   Mevcut dosya: {os.path.basename(partial_file)} ({format_size(file_size)})")
                print(f"   Dosya kısmen indirilmiş olabilir. Tekrar çalıştırdığınızda devam edecektir.")
            return False
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n✗ İndirme hatası (deneme {attempt}/{max_retries}): {error_msg}")
            
            if attempt < max_retries:
                wait_time = attempt * 5
                print(f"   {wait_time} saniye sonra tekrar denenecek...")
                time.sleep(wait_time)
            else:
                print(f"\n✗ Model indirilemedi. {max_retries} deneme başarısız oldu.")
                print(f"   Lütfen:")
                print(f"   1. İnternet bağlantınızı kontrol edin")
                print(f"   2. Disk alanınızı kontrol edin")
                print(f"   3. Firewall/antivirus ayarlarınızı kontrol edin")
                partial_file = find_model_file(model_name, models_dir)
                if partial_file:
                    file_size = get_file_size(partial_file)
                    print(f"   Kısmen indirilmiş dosya: {os.path.basename(partial_file)} ({format_size(file_size)})")
                return False
    
    return False


def list_downloaded_models(models_dir: str = "./models"):
    """İndirilmiş modelleri listele"""
    if not os.path.exists(models_dir):
        return []
    
    model_files = []
    for file in os.listdir(models_dir):
        if file.endswith('.pt'):
            model_files.append(file.replace('.pt', ''))
    
    return model_files


def list_downloaded_models_with_files(models_dir: str = "./models"):
    """İndirilmiş modelleri dosya bilgileriyle birlikte listele"""
    if not os.path.exists(models_dir):
        return []
    
    model_info = []
    for file in os.listdir(models_dir):
        if file.endswith('.pt'):
            file_path = os.path.join(models_dir, file)
            file_size = get_file_size(file_path)
            # Model adını temizle (large-v3.pt -> large)
            model_name = file.replace('.pt', '').replace('-v3', '').replace('-v2', '')
            model_info.append({
                'name': model_name,
                'file': file,
                'file_path': file_path,
                'size': file_size
            })
    
    return model_info


def delete_model(model_name: str, models_dir: str = "./models"):
    """Belirtilen modeli sil"""
    model_file = find_model_file(model_name, models_dir)
    
    if not model_file:
        print(f"\n✗ {model_name} modeli bulunamadı.")
        return False
    
    try:
        file_size = get_file_size(model_file)
        file_name = os.path.basename(model_file)
        
        print(f"\n⚠️  Silinecek Model:")
        print(f"   İsim: {model_name}")
        print(f"   Dosya: {file_name}")
        print(f"   Boyut: {format_size(file_size)}")
        
        confirm = input("\nBu modeli silmek istediğinizden emin misiniz? (e/h): ").strip().lower()
        
        if confirm != 'e':
            print("İptal edildi.")
            return False
        
        os.remove(model_file)
        print(f"\n✓ Model başarıyla silindi: {file_name}")
        print(f"   Kullanılan alan: {format_size(file_size)}")
        return True
        
    except Exception as e:
        print(f"\n✗ Model silme hatası: {e}")
        return False


def interactive_menu():
    """İnteraktif model seçim menüsü"""
    print("\n" + "="*60)
    print("  WHISPER MODEL YÖNETİM ARACI")
    print("="*60)
    
    # İndirilmiş modelleri göster
    downloaded = list_downloaded_models()
    downloaded_info = list_downloaded_models_with_files()
    
    if downloaded_info:
        print("\n✓ İndirilmiş Modeller:")
        for info in downloaded_info:
            print(f"  - {info['name']:<10} ({format_size(info['size']):>10}) - {info['file']}")
    
    # Model seçeneklerini göster
    print("\n📦 Mevcut Modeller:")
    print("-" * 60)
    for key, info in MODELS.items():
        status = "✓ İndirildi" if info["name"] in downloaded else "○ Yüklenmedi"
        print(f"  {key}. {info['name']:<10} ({info['size']:<10}) {status}")
    print("-" * 60)
    print(f"  d. Model Sil")
    print(f"  0. Çıkış")
    print("-" * 60)
    
    while True:
        choice = input("\nİşlem seçin (0-5 veya 'd'): ").strip().lower()
        
        if choice == "0":
            print("\nÇıkılıyor...")
            sys.exit(0)
        
        if choice == "d":
            # Model silme menüsü
            if not downloaded_info:
                print("\n⚠️  Silinecek model bulunamadı.")
                continue
            
            print("\n🗑️  Silinecek Model Seçin:")
            print("-" * 60)
            for idx, info in enumerate(downloaded_info, 1):
                print(f"  {idx}. {info['name']:<10} ({format_size(info['size']):>10}) - {info['file']}")
            print(f"  0. Geri")
            print("-" * 60)
            
            delete_choice = input("\nSilinecek modeli seçin (0-{}): ".format(len(downloaded_info))).strip()
            
            if delete_choice == "0":
                continue
            
            try:
                delete_idx = int(delete_choice) - 1
                if 0 <= delete_idx < len(downloaded_info):
                    model_to_delete = downloaded_info[delete_idx]['name']
                    delete_model(model_to_delete)
                    # Listeyi yenile
                    downloaded = list_downloaded_models()
                    downloaded_info = list_downloaded_models_with_files()
                    
                    # Menüyü tekrar göster
                    print("\n" + "="*60)
                    print("  WHISPER MODEL YÖNETİM ARACI")
                    print("="*60)
                    
                    if downloaded_info:
                        print("\n✓ İndirilmiş Modeller:")
                        for info in downloaded_info:
                            print(f"  - {info['name']:<10} ({format_size(info['size']):>10}) - {info['file']}")
                    
                    print("\n📦 Mevcut Modeller:")
                    print("-" * 60)
                    for key, info in MODELS.items():
                        status = "✓ İndirildi" if info["name"] in downloaded else "○ Yüklenmedi"
                        print(f"  {key}. {info['name']:<10} ({info['size']:<10}) {status}")
                    print("-" * 60)
                    print(f"  d. Model Sil")
                    print(f"  0. Çıkış")
                    print("-" * 60)
                else:
                    print("✗ Geçersiz seçim.")
            except ValueError:
                print("✗ Geçersiz seçim. Lütfen bir sayı girin.")
            continue
        
        if choice in MODELS:
            model_name = MODELS[choice]["name"]
            
            if model_name in downloaded:
                print(f"\n⚠ {model_name} modeli zaten indirilmiş.")
                confirm = input("Yeniden indirmek ister misiniz? (e/h): ").strip().lower()
                if confirm != 'e':
                    continue
            
            # Model indirmeyi onayla
            print(f"\n{model_name} modeli indirilecek ({MODELS[choice]['size']})")
            confirm = input("Devam etmek istiyor musunuz? (e/h): ").strip().lower()
            
            if confirm == 'e':
                success = download_model(model_name)
                if success:
                    print("\n✓ İşlem tamamlandı!")
                    # Listeyi yenile
                    downloaded = list_downloaded_models()
                    downloaded_info = list_downloaded_models_with_files()
                    
                    another = input("\nBaşka bir işlem yapmak ister misiniz? (e/h): ").strip().lower()
                    if another != 'e':
                        break
                else:
                    print("\n✗ Model indirilemedi. Tekrar deneyin.")
            else:
                print("\nİptal edildi.")
        else:
            print("✗ Geçersiz seçim. Lütfen 0-5 arası bir sayı veya 'd' girin.")
    
    print("\n✓ Program sonlandı.")


def main():
    """Ana fonksiyon"""
    if len(sys.argv) > 1:
        # Komut satırından model adı verilmişse
        model_name = sys.argv[1]
        
        # Silme komutu kontrolü
        if len(sys.argv) > 2 and sys.argv[2] == "--delete":
            delete_model(model_name)
        elif model_name in [m["name"] for m in MODELS.values()]:
            download_model(model_name)
        else:
            print(f"✗ Geçersiz model: {model_name}")
            print(f"Geçerli modeller: {', '.join([m['name'] for m in MODELS.values()])}")
            print(f"\nKullanım:")
            print(f"  İndirme: python download_models.py <model_name>")
            print(f"  Silme:   python download_models.py <model_name> --delete")
    else:
        # İnteraktif menüyü göster
        interactive_menu()


if __name__ == "__main__":
    main()

