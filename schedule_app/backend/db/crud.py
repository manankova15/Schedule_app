from sqlalchemy.orm import Session
from backend.db import models
from backend.schemas import employee as schemas

def create_employee(db: Session, employee: schemas.EmployeeCreate):
    """
    Summary:
        Создать сотрудника.

    Args:
        db (Session): Сессия базы данных.
        employee (schemas.EmployeeCreate): Данные нового сотрудника.

    Returns:
        models.Employee - Созданный объект сотрудника.
    """
    db_employee = models.Employee(**employee.dict())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

def get_employees(db: Session, skip: int = 0, limit: int = 10):
    """
    Summary:
        Получить всех сотрудников.

    Args:
        db (Session): Сессия базы данных.
        skip (int, optional): Количество записей для пропуска. Значение по умолчанию - 0.
        limit (int, optional): Максимальное количество записей для получения. Значение по умолчанию - 10.

    Returns:
        List[models.Employee]: Список сотрудников.
    """
    return db.query(models.Employee).offset(skip).limit(limit).all()

def get_employee(db: Session, employee_id: int):
    """
    Summary:
        Получить одного сотрудника.

    Args:
        db (Session): Сессия базы данных.
        employee_id (int): Идентификатор сотрудника.

    Returns:
        models.Employee: Объект сотрудника, если найден, иначе None.
    """
    return db.query(models.Employee).filter(models.Employee.id == employee_id).first()

# Обновить данные сотрудника
def update_employee(db: Session, employee_id: int, employee: schemas.EmployeeUpdate):
    """
    Summary:
        Обновить данные сотрудника.

    Args:
        db (Session): Сессия базы данных.
        employee_id (int): Идентификатор сотрудника.
        employee (schemas.EmployeeUpdate): Обновленные данные сотрудника.

    Returns:
        models.Employee: Обновленный объект сотрудника, если найден, иначе None.
    """
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if db_employee:
        for key, value in employee.dict().items():
            setattr(db_employee, key, value)
        db.commit()
        db.refresh(db_employee)
    return db_employee

# Удалить сотрудника
def delete_employee(db: Session, employee_id: int):
    """
    Summary:
        Удалить сотрудника.

    Args:
        db (Session): Сессия базы данных.
        employee_id (int): Идентификатор сотрудника.

    Returns:
        models.Employee: Удаленный объект сотрудника, если найден, иначе None.
    """
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if db_employee:
        db.delete(db_employee)
        db.commit()
    return db_employee
