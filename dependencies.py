from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from auth import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401)

        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(current_user: dict = Depends(get_current_user)):

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    return current_user
