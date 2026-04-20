import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session

# Используем новый способ для SQLAlchemy 2.0+
SqlAlchemyBase = orm.declarative_base()

__factory = None


def global_init(db_file):
    """Инициализация БД (как в уроке WEB 3)"""
    global __factory

    if __factory:
        return

    if not db_file or not db_file.strip():
        raise Exception("Необходимо указать файл базы данных.")

    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'
    print(f"Подключение к базе данных по адресу {conn_str}")

    engine = sa.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    # Импортируем все модели перед созданием таблиц
    from . import __all_models

    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    """Создание сессии для работы с БД"""
    global __factory
    return __factory()