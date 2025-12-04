"""
Backend başlatma öncesi Whisper model seçimi ve kontrolü
"""
import os
import sys
import whisper


def list_available_models():
    """Mevcut modelleri listele"""
    return ["tiny", "base", "small", "medium", "large"]


def list_downloaded_models(models_dir: str = "./models"):
    """İndirilmiş modelleri listele"""
    if not os.path.exists(models_dir):
        return []
    
    model_files = []
    for file in os.listdir(models_dir):
        if file.endswith('.pt'):
            model_files.append(file.replace('.pt', ''))
    
    return model_files


def download_model(model_name: str, models_dir: str = "./models"):
    """Model indir"""
    print(f"\n{'='*60}")
    print(f"📦 Model indiriliyor: {model_name}")
    print(f"{'='*60}\n")
    
    os.makedirs(models_dir, exist_ok=True)
    
    try:
        model = whisper.load_model(model_name, download_root=models_dir)
        print(f"\n✓ Model başarıyla indirildi: {model_name}\n")
        return True
    except Exception as e:
        print(f"\n✗ Model indirme hatası: {e}\n")
        return False


def setup_default_model():
    """Varsayılan modeli ayarla"""
    print("\n" + "="*60)
    print("  WHISPER MODEL KURULUMU")
    print("="*60)
    
    available_models = list_available_models()
    downloaded_models = list_downloaded_models()
    
    if downloaded_models:
        print("\n✓ İndirilmiş Modeller:")
        for i, model in enumerate(downloaded_models, 1):
            print(f"  {i}. {model}")
    else:
        print("\n⚠ Henüz indirilmiş model yok.")
    
    print("\n📦 Tüm Modeller:")
    print("-" * 60)
    model_sizes = {
        "tiny": "~75 MB",
        "base": "~142 MB", 
        "small": "~466 MB",
        "medium": "~1.5 GB",
        "large": "~2.9 GB"
    }
    
    for i, model in enumerate(available_models, 1):
        status = "✓" if model in downloaded_models else "○"
        print(f"  {i}. {status} {model:<10} ({model_sizes.get(model, 'N/A')})")
    print("-" * 60)
    
    # Varsayılan model önerisi
    if "small" in downloaded_models:
        default_choice = "small"
    elif downloaded_models:
        default_choice = downloaded_models[0]
    else:
        default_choice = "small"
    
    print(f"\n💡 Önerilen: {default_choice}")
    choice = input(f"\nKullanmak istediğiniz modeli girin (varsayılan: {default_choice}): ").strip().lower()
    
    if not choice:
        choice = default_choice
    
    if choice not in available_models:
        print(f"\n✗ Geçersiz model: {choice}")
        return False
    
    # Model kontrolü
    if choice not in downloaded_models:
        print(f"\n⚠ {choice} modeli indirilmemiş.")
        download_choice = input("Şimdi indirmek ister misiniz? (e/h): ").strip().lower()
        
        if download_choice == 'e':
            success = download_model(choice)
            if not success:
                return False
        else:
            print("\n✗ Model indirilmeden backend başlatılamaz.")
            return False
    
    # .env dosyasına kaydet
    env_path = ".env"
    lines = []
    
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # DEFAULT_WHISPER_MODEL varsa güncelle, yoksa ekle
    found = False
    for i, line in enumerate(lines):
        if line.startswith('DEFAULT_WHISPER_MODEL='):
            lines[i] = f'DEFAULT_WHISPER_MODEL={choice}\n'
            found = True
            break
    
    if not found:
        lines.append(f'\nDEFAULT_WHISPER_MODEL={choice}\n')
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"\n✓ Varsayılan model ayarlandı: {choice}")
    print(f"  Konum: {env_path}")
    print("\n✓ Backend başlatmaya hazır!")
    
    return True


if __name__ == "__main__":
    success = setup_default_model()
    if not success:
        sys.exit(1)

