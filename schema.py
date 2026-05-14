from pydantic import BaseModel, ConfigDict, constr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: constr(min_length=6, max_length=72)
    role: str = "student"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str


class StudentBase(BaseModel):
    name: str
    department: str
    gpa: float
    email: str


class StudentIn(StudentBase):
    user_id: Optional[int] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    gpa: Optional[float] = None
    email: Optional[str] = None


class StudentOut(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    changed_by: str
    change_description: str
    timestamp: datetime