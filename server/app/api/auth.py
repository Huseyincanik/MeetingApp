from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserLogin, UserResponse, Token
from ..utils.security import verify_password, get_password_hash, create_access_token, decode_access_token
from ..config import settings

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Mevcut kullanıcıyı token'dan al"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama başarısız",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Kullanıcı kaydı"""
    # Email kontrolü
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email adresi zaten kullanılıyor"
        )
    
    # Yeni kullanıcı oluştur
    hashed_password = get_password_hash(user_data.password)
    print(f"🔐 Yeni kullanıcı oluşturuluyor: {user_data.email}")
    print(f"🔑 Hash uzunluğu: {len(hashed_password)}")
    print(f"🔑 Hash başlangıcı: {hashed_password[:20]}...")
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Test: Şifre doğrulama testi
    test_verify = verify_password(user_data.password, new_user.hashed_password)
    print(f"✅ Şifre doğrulama testi (register sonrası): {test_verify}")
    
    return new_user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Kullanıcı girişi"""
    print(f"🔐 Giriş denemesi: {form_data.username}")
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        print(f"❌ Kullanıcı bulunamadı: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"✅ Kullanıcı bulundu: {user.email}")
    print(f"🔑 DB'den gelen hash uzunluğu: {len(user.hashed_password) if user.hashed_password else 'None'}")
    print(f"🔑 DB'den gelen hash başlangıcı: {user.hashed_password[:20] if user.hashed_password else 'None'}...")
    
    # Şifre doğrulama
    password_valid = verify_password(form_data.password, user.hashed_password)
    print(f"🔐 Şifre doğrulama sonucu: {password_valid}")
    
    if not password_valid:
        print(f"❌ Şifre doğrulama başarısız: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kullanıcı hesabı aktif değil"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Mevcut kullanıcı bilgileri"""
    return current_user

