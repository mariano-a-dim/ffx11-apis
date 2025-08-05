import uuid
from typing import List, Optional
from sqlmodel import Session, select, func

from app.core.exceptions import DatabaseException, ValidationException, NotFoundException
from app.core.logging import get_logger
from app.models import Item, ItemCreate, ItemUpdate

# Inicializar logger
logger = get_logger(__name__)


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    logger.info("Creating item", owner_id=str(owner_id))
    try:
        db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        logger.info("Item created successfully", item_id=str(db_item.id))
        return db_item
    except Exception as e:
        session.rollback()
        logger.error("Failed to create item", error=str(e), owner_id=str(owner_id), exc_info=True)
        raise DatabaseException(f"Failed to create item: {str(e)}")


def get_item_by_id(*, session: Session, item_id: uuid.UUID) -> Optional[Item]:
    """
    Obtener un item por su ID.
    """
    return session.get(Item, item_id)


def get_items(
    *, 
    session: Session, 
    skip: int = 0, 
    limit: int = 100,
    owner_id: Optional[uuid.UUID] = None
) -> List[Item]:
    """
    Obtener items con filtros opcionales.
    """
    logger.debug("Getting items", skip=skip, limit=limit, owner_id=str(owner_id) if owner_id else None)
    
    # Validaciones de entrada
    if skip < 0:
        logger.warning("Invalid skip value", skip=skip)
        raise ValidationException("skip must be >= 0")
    if limit <= 0 or limit > 1000:
        logger.warning("Invalid limit value", limit=limit)
        raise ValidationException("limit must be between 1 and 1000")
    
    statement = select(Item)
    
    if owner_id:
        statement = statement.where(Item.owner_id == owner_id)
    
    statement = statement.offset(skip).limit(limit).order_by(Item.id)
    items = session.exec(statement).all()
    logger.debug("Items retrieved", count=len(items))
    return items


def count_items(*, session: Session, owner_id: Optional[uuid.UUID] = None) -> int:
    """
    Contar items con filtros opcionales.
    """
    statement = select(func.count(Item.id))
    
    if owner_id:
        statement = statement.where(Item.owner_id == owner_id)
    
    return session.exec(statement).first() or 0


def update_item(*, session: Session, db_item: Item, item_in: ItemUpdate) -> Item:
    """
    Actualizar un item.
    """
    try:
        update_dict = item_in.model_dump(exclude_unset=True)
        db_item.sqlmodel_update(update_dict)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Failed to update item: {str(e)}")


def delete_item(*, session: Session, item_id: uuid.UUID) -> bool:
    """
    Eliminar un item por su ID.
    """
    try:
        item = get_item_by_id(session=session, item_id=item_id)
        if not item:
            return False
        session.delete(item)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise DatabaseException(f"Failed to delete item: {str(e)}") 