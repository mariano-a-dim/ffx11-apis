import uuid
from typing import Any

from fastapi import APIRouter, Query
from app.core.exceptions import NotFoundException, ForbiddenException

from app.api.deps import CurrentUser, SessionDep
from app.models import Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message
from app.crud.item import get_items, get_item_by_id, create_item as crud_create_item, update_item as crud_update_item, delete_item as crud_delete_item, count_items

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=ItemsPublic)
def read_items(
    session: SessionDep, 
    current_user: CurrentUser, 
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
) -> Any:
    """
    Retrieve items.
    """

    if current_user.is_superuser:
        count = count_items(session=session)
        items = get_items(session=session, skip=skip, limit=limit)
    else:
        count = count_items(session=session, owner_id=current_user.id)
        items = get_items(session=session, skip=skip, limit=limit, owner_id=current_user.id)

    return ItemsPublic(data=items, count=count)


@router.get("/{id}", response_model=ItemPublic)
def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    item = get_item_by_id(session=session, item_id=id)
    if not item:
        raise NotFoundException("Item")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise ForbiddenException("Not enough permissions")
    return item


@router.post("/", response_model=ItemPublic)
def create_item(
    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> Any:
    """
    Create new item.
    """
    item = crud_create_item(session=session, item_in=item_in, owner_id=current_user.id)
    return item


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item.
    """
    item = get_item_by_id(session=session, item_id=id)
    if not item:
        raise NotFoundException("Item")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise ForbiddenException("Not enough permissions")
    updated_item = crud_update_item(session=session, db_item=item, item_in=item_in)
    return updated_item


@router.delete("/{id}")
def delete_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an item.
    """
    item = get_item_by_id(session=session, item_id=id)
    if not item:
        raise NotFoundException("Item")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise ForbiddenException("Not enough permissions")
    success = crud_delete_item(session=session, item_id=id)
    if not success:
        raise NotFoundException("Item")
    return Message(message="Item deleted successfully")
