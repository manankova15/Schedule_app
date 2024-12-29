from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import crud, models
from backend.db.database import SessionLocal
from backend.schemas import employee as schemas

router = APIRouter()

def get_db():
    """
    Summary:
        Функция получения сессии БД.

    Yields:
        Session: Сессия базы данных.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.EmployeeOut)
def create_employee(employee: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    """
    Summary:
        Создание сотрудника.

    Args:
        employee (schemas.EmployeeCreate): Данные нового сотрудника.
        db (Session, optional): Сессия базы данных, предоставляется автоматически через Depends(get_db).

    Returns:
        schemas.EmployeeOut: Созданный объект сотрудника.
    """
    return crud.create_employee(db, employee)

@router.get("/", response_model=list[schemas.EmployeeOut])
def read_employees(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Summary:
        Получение всех сотрудников.

    Args:
        skip (int, optional): Количество записей для пропуска. Значение по умолчанию - 0.
        limit (int, optional): Максимальное количество записей для получения. Значение по умолчанию - 10.
        db (Session, optional): Сессия базы данных, предоставляется автоматически через Depends(get_db).

    Returns:
        List[schemas.EmployeeOut]: Список объектов сотрудников.
    """
    return crud.get_employees(db, skip, limit)

@router.get("/{employee_id}", response_model=schemas.EmployeeOut)
def read_employee(employee_id: int, db: Session = Depends(get_db)):
    """
    Summary:
        Получить одного сотрудника.

    Args:
        employee_id (int): Идентификатор сотрудника.
        db (Session, optional): Сессия базы данных, предоставляется автоматически через Depends(get_db).

    Returns:
        schemas.EmployeeOut: Объект сотрудника, если найден.

    Raises:
        HTTPException: Если сотрудник не найден, возвращает статус код 404 с соответствующим сообщением.
    """
    employee = crud.get_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return employee

@router.put("/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(employee_id: int, employee: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    """
    Summary:
        Обновление сотрудника.

    Args:
        employee_id (int): Идентификатор сотрудника.
        employee (schemas.EmployeeUpdate): Обновленные данные сотрудника.
        db (Session, optional): Сессия базы данных, предоставляется автоматически через Depends(get_db).

    Returns:
        schemas.EmployeeOut: Обновленный объект сотрудника, если найден.

    Raises:
        HTTPException: Если сотрудник не найден, возвращает статус код 404 с соответствующим сообщением.
    """
    updated_employee = crud.update_employee(db, employee_id, employee)
    if updated_employee is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return updated_employee

@router.delete("/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    """
    Summary:
        Удаление сотрудника.

    Args:
        employee_id (int): Идентификатор сотрудника.
        db (Session, optional): Сессия базы данных, предоставляется автоматически через Depends(get_db).

    Returns:
        Dict[str, str]: Сообщение о том, что сотрудник удален.

    Raises:
        HTTPException: Если сотрудник не найден, возвращает статус код 404 с соответствующим сообщением.
    """
    deleted_employee = crud.delete_employee(db, employee_id)
    if deleted_employee is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return {"message": "Сотрудник удален"}