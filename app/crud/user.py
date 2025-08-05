import uuid
from typing import Any, List, Optional
from sqlmodel import Session, select, func

from app.core.security import get_password_hash, verify_password
from app.core.exceptions import DatabaseException, ValidationException, NotFoundException
from app.models import User, UserCreate, UserUpdate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    try:
        db_obj = User.model_validate(
            user_create, update={"hashed_password": get_password_hash(user_create.password)}
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Failed to create user: {str(e)}")


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    try:
        user_data = user_in.model_dump(exclude_unset=True)
        extra_data = {}
        if "password" in user_data:
            password = user_data["password"]
            hashed_password = get_password_hash(password)
            extra_data["hashed_password"] = hashed_password
        db_user.sqlmodel_update(user_data, update=extra_data)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Failed to update user: {str(e)}")


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email).order_by(User.id)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def get_user_by_id(*, session: Session, user_id: uuid.UUID) -> Optional[User]:
    """
    Obtener un usuario por su ID.
    """
    return session.get(User, user_id)


def get_users(
    *, 
    session: Session, 
    skip: int = 0, 
    limit: int = 100
) -> List[User]:
    """
    Obtener usuarios con paginación.
    """
    # Validaciones de entrada
    if skip < 0:
        raise ValidationException("skip must be >= 0")
    if limit <= 0 or limit > 1000:
        raise ValidationException("limit must be between 1 and 1000")
    
    statement = select(User).offset(skip).limit(limit).order_by(User.id)
    return session.exec(statement).all()


def count_users(*, session: Session) -> int:
    """
    Contar usuarios.
    """
    statement = select(func.count(User.id))
    return session.exec(statement).first() or 0


def update_user_me(*, session: Session, db_user: User, user_in: UserUpdate) -> User:
    """
    Actualizar usuario propio.
    """
    try:
        user_data = user_in.model_dump(exclude_unset=True)
        db_user.sqlmodel_update(user_data)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Failed to update user: {str(e)}")


def update_user_password(*, session: Session, db_user: User, new_password: str) -> User:
    """
    Actualizar contraseña de usuario.
    """
    try:
        hashed_password = get_password_hash(new_password)
        db_user.hashed_password = hashed_password
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Failed to update user password: {str(e)}")


def delete_user(*, session: Session, user_id: uuid.UUID) -> bool:
    """
    Eliminar un usuario por su ID.
    """
    try:
        user = get_user_by_id(session=session, user_id=user_id)
        if not user:
            return False
        session.delete(user)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Failed to delete user: {str(e)}") 