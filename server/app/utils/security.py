from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from ..config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifreyi doğrula"""
    if not plain_password or not hashed_password:
        return False
    
    try:
        # Eğer hashed_password zaten bytes ise, string'e çevir
        if isinstance(hashed_password, bytes):
            hashed_password = hashed_password.decode('utf-8')
        
        # Plain password'u bytes'a çevir
        password_bytes = plain_password.encode('utf-8')
        
        # Hashed password'u bytes'a çevir
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Bcrypt ile doğrula
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        # Hata durumunda log'la (production'da logger kullanılabilir)
        print(f"Şifre doğrulama hatası: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Şifreyi hashle"""
    # bcrypt maksimum 72 byte şifre kabul eder
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT token oluştur"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """JWT token'ı decode et"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
