"""
Database Transaction Management.
Provides context managers for safe database transactions.
"""
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@contextmanager
def transaction(db: Session) -> Generator[Session, None, None]:
    """
    Context manager for database transactions.

    Usage:
        with transaction(db) as tx:
            crud.create_plan(tx, plan_data)
            crud.update_device(tx, device_id, device_data)
        # Auto commits on success, rolls back on exception

    Args:
        db: SQLAlchemy database session

    Yields:
        The same database session

    Raises:
        Re-raises any exception that occurs during the transaction
    """
    try:
        yield db
        db.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back due to error: {e}", exc_info=True)
        raise


@contextmanager
def savepoint(db: Session, name: str = None) -> Generator[Session, None, None]:
    """
    Context manager for nested transactions using savepoints.

    Usage:
        with transaction(db) as tx:
            crud.create_plan(tx, plan_data)

            with savepoint(tx, "device_update"):
                crud.update_device(tx, device_id, device_data)
                # This can rollback independently

    Args:
        db: SQLAlchemy database session
        name: Optional savepoint name

    Yields:
        The same database session

    Raises:
        Re-raises any exception that occurs during the savepoint
    """
    savepoint_obj = db.begin_nested()
    try:
        yield db
        savepoint_obj.commit()
        logger.debug(f"Savepoint '{name or 'unnamed'}' committed")
    except Exception as e:
        savepoint_obj.rollback()
        logger.warning(f"Savepoint '{name or 'unnamed'}' rolled back: {e}")
        raise
