from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from model import User
from schema import UserCreate, UserOut, Token
from auth import hash_password, verify_password, create_access_token
from monitoring import log_auth_event, log_db_event

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):

    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        log_auth_event("register_duplicate_username", user.username, False)
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username = user.username,
        password = hash_password(user.password),
        role     = user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_auth_event("register", user.username, True)
    log_db_event("create", "user", new_user.id, user.username)

    return new_user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.username == form_data.username).first()

    if not db_user or not verify_password(form_data.password, db_user.password):
        log_auth_event("login", form_data.username, False)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={"sub": db_user.username, "role": db_user.role})

    log_auth_event("login", form_data.username, True)

    return {"access_token": token, "token_type": "bearer"}
