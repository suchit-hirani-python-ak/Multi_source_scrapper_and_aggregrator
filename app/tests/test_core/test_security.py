from app.core.security import (
    hash_password, 
    verify_password, 
    generate_tokens
)

def test_password_hashing_and_verification():
    password = "secure_password123"
    hashed = hash_password(password)
    

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False



def test_generate_tokens_structure():
    user = {
        "email": "dev@test.com",
        "_id": "660adb23f51bb4362e0020ee",
        "role": "admin"
    }
    
    tokens = generate_tokens(user)
    
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["type"] == "bearer"

