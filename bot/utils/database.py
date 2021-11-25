import functools
import os
from contextlib import contextmanager
from typing import List

import loguru
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, scoped_session, sessionmaker

logger = loguru.logger

DATABASE_URL = os.environ["DATABASE_URL"]
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

Base = declarative_base()


def get_session():
    return scoped_session(sessionmaker(bind=engine))()


@contextmanager
def db_session(commit):
    session = get_session()
    try:
        yield session
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        logger.exception(e)
    finally:
        if session:
            session.close()


def func_session(commit: bool = False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with db_session(commit) as session:
                return func(session, *args, **kwargs)

        return wrapper

    return decorator


def same_as(column_name):
    def default_function(context):
        return context.current_parameters.get(column_name)

    return default_function


class GenshinCharacter(Base):
    __tablename__ = "genshin_characters"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    alias_name = Column(
        String, default=same_as("name")
    )  # another name, like 刻晴|keqing|阿晴

    def __repr__(self) -> str:
        return f"GenshinCharacter(id={self.id}, name={self.name})"


Base.metadata.create_all(engine)


@func_session()
def get_character_by_name(session: Session, name: str) -> List[GenshinCharacter]:
    return (
        session.execute(
            select(GenshinCharacter).where(
                GenshinCharacter.alias_name.ilike(f"%{name}%")
            )
        )
        .scalars()
        .all()
    )


@func_session()
def get_all_character_name(session: Session) -> List[str]:
    return session.execute(select(GenshinCharacter.alias_name)).scalars().all()


@func_session()
def get_character_name_by_id(session: Session, id: int) -> GenshinCharacter:
    (name,) = session.execute(
        select(GenshinCharacter).where(GenshinCharacter.id == id)
    ).first()
    return name
