from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# engine = create_engine("sqlite://")
engine = create_engine("sqlite:///file:messages/db.sqlite?mode=rwc&uri=true", echo=True)


@contextmanager
def enter_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
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


Base.metadata.create_all(engine)


def get_set_wh_row(session: Session, webhook_url: str) -> Webhook:
    stmt = select(Webhook).filter(Webhook.url == webhook_url)
    res = session.scalars(stmt).one_or_none()

    if res is None:
        res = Webhook(url=webhook_url)
        session.add(res)
    return res


def save_message_ids_by_key(webhook_url: str, key: str, value: int):
    with enter_session() as session:
        wh = get_set_wh_row(session=session, webhook_url=webhook_url)
        wh[key] = value


def save_message_ids(
    webhook_url: str,
    header: int = 0,
    gamestate: int = 0,
    map_rotation: int = 0,
    player_stats: int = 0,
):
    with enter_session() as session:
        wh = get_set_wh_row(session=session, webhook_url=webhook_url)
        if wh is None:
            # wh = Webhook(
            #     url=webhook_url,
            #     header=header,
            #     gamestate=gamestate,
            #     map_rotation=map_rotation,
            #     player_stats=player_stats,
            # )
            wh = Webhook()
        wh.header = header
        wh.gamestate = gamestate
        wh.map_rotation = map_rotation
        wh.player_stats = player_stats
