from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from model import Student, User, AuditLog
from schema import StudentIn, StudentOut, StudentUpdate
from dependencies import get_current_user, require_admin
from cache import delete_by_prefix, delete_key, get_json, set_json
from monitoring import log_db_event

router = APIRouter(prefix="/students", tags=["Students"])


def student_to_dict(student: Student):
    return {
        "id": student.id,
        "name": student.name,
        "department": student.department,
        "gpa": student.gpa,
        "email": student.email,
        "user_id": student.user_id,
    }


@router.get("/", response_model=List[StudentOut])
def get_all_students(
    department: Optional[str] = None,
    gpa_min: Optional[float] = None,
    gpa_max: Optional[float] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    cache_key = f"students:list:{department}:{gpa_min}:{gpa_max}:{skip}:{limit}"
    cached_students = get_json(cache_key)
    if cached_students is not None:
        return cached_students

    query = db.query(Student)

    if department:
        query = query.filter(Student.department == department)
    if gpa_min is not None:
        query = query.filter(Student.gpa >= gpa_min)
    if gpa_max is not None:
        query = query.filter(Student.gpa <= gpa_max)

    students = query.order_by(Student.id).offset(skip).limit(limit).all()
    result = [student_to_dict(student) for student in students]
    set_json(cache_key, result)

    return result


@router.get("/me", response_model=StudentOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == current_user.get("sub")).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    student = db.query(Student).filter(Student.user_id == user.id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    return student_to_dict(student)


@router.put("/me", response_model=StudentOut)
def update_my_profile(
    updated: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == current_user.get("sub")).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    student = db.query(Student).filter(Student.user_id == user.id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    if updated.name is not None:
        student.name = updated.name
    if updated.department is not None:
        student.department = updated.department
    if updated.gpa is not None:
        student.gpa = updated.gpa
    if updated.email is not None:
        student.email = updated.email

    log = AuditLog(
        student_id = student.id,
        changed_by = current_user.get("sub"),
        change_description = "Student updated own profile"
    )

    db.add(log)
    db.commit()
    db.refresh(student)

    delete_key(f"students:item:{student.id}")
    delete_by_prefix("students:list:")
    log_db_event("update", "student", student.id, current_user.get("sub"))

    return student_to_dict(student)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    cache_key = f"students:item:{student_id}"
    if current_user.get("role") == "admin":
        cached_student = get_json(cache_key)
        if cached_student is not None:
            return cached_student

    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user.get("role") != "admin":
        user = db.query(User).filter(User.username == current_user.get("sub")).first()

        if not user or student.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not allowed")

    result = student_to_dict(student)
    if current_user.get("role") == "admin":
        set_json(cache_key, result)

    return result


@router.post("/", response_model=StudentOut, status_code=201)
def create_student(
    student: StudentIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    existing = db.query(Student).filter(Student.email == student.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_student = Student(
        name       = student.name,
        department = student.department,
        gpa        = student.gpa,
        email      = student.email,
        user_id    = student.user_id
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    delete_by_prefix("students:list:")
    log_db_event("create", "student", new_student.id, current_user.get("sub"))

    return student_to_dict(new_student)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    updated: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if updated.name is not None:
        student.name = updated.name
    if updated.department is not None:
        student.department = updated.department
    if updated.gpa is not None:
        student.gpa = updated.gpa
    if updated.email is not None:
        student.email = updated.email

    log = AuditLog(
        student_id = student.id,
        changed_by = current_user.get("sub"),
        change_description = "Admin updated student"
    )

    db.add(log)
    db.commit()
    db.refresh(student)

    delete_key(f"students:item:{student.id}")
    delete_by_prefix("students:list:")
    log_db_event("update", "student", student.id, current_user.get("sub"))

    return student_to_dict(student)


@router.delete("/{student_id}", status_code=204)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()

    delete_key(f"students:item:{student_id}")
    delete_by_prefix("students:list:")
    log_db_event("delete", "student", student_id, current_user.get("sub"))
