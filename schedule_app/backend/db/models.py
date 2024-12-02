from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum, Boolean
from sqlalchemy.orm import relationship
from backend.db.database import Base

# Роли пользователей
class UserRoleEnum(str, Enum):
    employee = "employee"
    manager = "manager"

# Модель сотрудника
class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    position = Column(String, nullable=False)
    shift_quota = Column(Integer, nullable=False)
    role = Column(Enum(UserRoleEnum), default="employee")

    vacations = relationship("Vacation", back_populates="employee")
    requests = relationship("SpecialRequest", back_populates="employee")

# Модель оборудования
class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    shift_morning = Column(Boolean, default=True)
    shift_evening = Column(Boolean, default=True)
    shift_night = Column(Boolean, default=False)

# Модель связи сотрудника и оборудования
class EmployeeEquipment(Base):
    __tablename__ = "employee_equipment"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    is_primary = Column(Boolean, default=True)

# Модель с отпусками
class Vacation(Base):
    __tablename__ = "vacations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    employee = relationship("Employee", back_populates="vacations")

# Модель пожеланий сотрудников
class SpecialRequest(Base):
    __tablename__ = "special_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    date = Column(Date, nullable=False)
    priority = Column(String, nullable=False)

    employee = relationship("Employee", back_populates="requests")

# Модель графика работы
class Schedule(Base):
    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    equipment_id = Column(Integer, ForeignKey("equipment.id"))
    shift_type = Column(String, nullable=False)  # morning, evening, night
    date = Column(Date, nullable=False)
