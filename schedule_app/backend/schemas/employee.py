from pydantic import BaseModel, EmailStr
from typing import Optional

class EmployeeBase(BaseModel):
    """
    Summary:
        Схема для отображения данных сотрудника.

    Attributes:
        full_name (str): Полное имя сотрудника.
        email (EmailStr): Электронная почта сотрудника.
        phone (str): Номер телефона сотрудника.
        position (str): Должность сотрудника.
        shift_quota (int): Квота смен сотрудника.
    """
    full_name: str
    email: EmailStr
    phone: str
    position: str
    shift_quota: int

class EmployeeCreate(EmployeeBase):
    """
    Summary:
        Схема для создания нового сотрудника.

    Attributes::
        TO DO.
    """
    pass

class EmployeeUpdate(EmployeeBase):
    """
    Summary:
        Схема для обновления сотрудника.

    Attributes::
       TO DO.
    """
    pass

class EmployeeOut(EmployeeBase):
    """
    Summary:
        Схема для отображения ответа API.

    Attributes:
        id (int): Идентификатор сотрудника.

    Inherits:
        EmployeeBase: Наследует все поля из базовой схемы EmployeeBase.

    Config:
        orm_mode (bool): Установлено в True для поддержки работы с ORM-моделями.
    """
    id: int

    class Config:
        from_attributes = True