"""
암호화 유틸리티 모듈
"""

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 고정된 솔트 값 (실제 프로덕션에서는 안전하게 관리해야 함)
_SALT = b'gazua_trading_salt'

def _get_key() -> bytes:
    """암호화 키 생성"""
    # PBKDF2를 사용하여 키 생성
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100000,
    )
    
    # 시스템 고유 정보를 사용하여 키 생성
    import platform
    system_info = platform.node().encode()
    key = base64.urlsafe_b64encode(kdf.derive(system_info))
    return key

def encrypt_data(data: str) -> str:
    """데이터 암호화
    
    Args:
        data: 암호화할 데이터
        
    Returns:
        암호화된 데이터 (base64 인코딩)
    """
    key = _get_key()
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_data(encrypted_data: str) -> str:
    """데이터 복호화
    
    Args:
        encrypted_data: 복호화할 데이터 (base64 인코딩)
        
    Returns:
        복호화된 데이터
    """
    key = _get_key()
    f = Fernet(key)
    decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted_data))
    return decrypted.decode() 