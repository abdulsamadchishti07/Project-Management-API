from .database import Base
from sqlalchemy import Integer, Column, String, Boolean, text, ForeignKey

from sqlalchemy.sql.sqltypes import TIMESTAMP


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable= False)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable= False)
    password = Column(String, nullable=False)
    active = Column(Boolean, server_default="True", nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
