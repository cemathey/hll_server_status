from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engines = {}


def init_engine(db_name):
    if db_name in engines:
        # We already have an engine entry, pass
        pass
    try:
        engine_string = f"sqlite:///file:messages/{db_name}.sqlite?mode=rwc&uri=true"
        engine = create_engine(engine_string, echo=True)
        Base.metadata.create_all(engine)
        engines[db_name] = engine
    except Exception as e:
       raise e 


@contextmanager
def enter_session(db_name: str) -> Generator[Session, None, None]:
    with Session(engines[db_name]) as session:
        session.begin()
        try:
            yield session
        except:
            session.rollback()
            raise
        else:
            session.commit()


class Base(DeclarativeBase):
    pass


class Webhook(Base):
    __tablename__ = "webhooks"

    url: Mapped[str] = mapped_column(primary_key=True)
    header: Mapped[int] = mapped_column(default=0)
    gamestate: Mapped[int] = mapped_column(default=0)
    map_rotation: Mapped[int] = mapped_column(default=0)
    player_stats: Mapped[int] = mapped_column(default=0)

    def __getitem__(self, key: str) -> int:
        if key == "header":
            return self.header
        elif key == "gamestate":
            return self.gamestate
        elif key == "map_rotation":
            return self.map_rotation
        elif key == "player_stats":
            return self.player_stats
        else:
            raise KeyError(f"{self!r} {key=}")

    def __setitem__(self, key: str, value: int):
        session = Session.object_session(self)
        if key == "header":
            self.header = value
        elif key == "gamestate":
            self.gamestate = value
        elif key == "map_rotation":
            self.map_rotation = value
        elif key == "player_stats":
            self.player_stats = value
        else:
            raise KeyError(f"{self!r} {key=}")


def get_set_wh_row(session: Session, webhook_url: str) -> Webhook:
    stmt = select(Webhook).filter(Webhook.url == webhook_url)
    res = session.scalars(stmt).one_or_none()

    if res is None:
        res = Webhook(url=webhook_url)
        session.add(res)
    return res


def save_message_ids_by_key(db_name: str, webhook_url: str, key: str, value: int):
    with enter_session(db_name) as session:
        wh = get_set_wh_row(session=session, webhook_url=webhook_url)
        wh[key] = value


def save_message_ids(
    db_name: str,
    webhook_url: str,
    header: int = 0,
    gamestate: int = 0,
    map_rotation: int = 0,
    player_stats: int = 0,
):
    with enter_session(db_name) as session:
        wh = get_set_wh_row(session=session, webhook_url=webhook_url)
        if wh is None:
            wh = Webhook()
        wh.header = header
        wh.gamestate = gamestate
        wh.map_rotation = map_rotation
        wh.player_stats = player_stats
