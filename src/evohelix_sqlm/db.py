from sqlmodel import SQLModel, Session
from sqlmodel import create_engine, select
from python_settings import settings
from sqlalchemy.inspection import inspect


class DBEngine(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBEngine, cls).__new__(cls)
            db_url = 'postgresql://{}:{}@{}:{}/{}'.format(
                settings.POSTGRES_USERNAME,
                settings.POSTGRES_PASSWORD,
                settings.POSTGRES_HOST,
                settings.POSTGRES_PORT,
                settings.POSTGRES_DATABASE
            )
            cls._instance.engine = create_engine(db_url, echo=True)
            SQLModel.metadata.create_all(cls._instance.engine)
        return cls._instance

    def exists(self, model, id):
        with Session(self.engine) as session:
            sql = select(model).where(model.id == id)
            return session.exec(sql).first()

    def create(self, instance):
        with Session(self.engine) as session:
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance

    def read(self, model, where=[], order_by=None, limit=None, offset=0):
        with Session(self.engine) as session:
            sql = select(model) \
                .order_by(order_by) \
                .where(*where) \
                .offset(offset) \
                .limit(limit)
            return session.exec(sql).all()

    def update(self, db_object, instance):
        for key, value in instance.dict(exclude_unset=True).items():
            keys = [key.name for key in inspect(db_object.__class__).primary_key]
            if key in keys:
                continue
            setattr(db_object, key, value)
        with Session(self.engine) as session:
            session.add(db_object)
            session.commit()
            session.refresh(db_object)
        return db_object

    def replace(self, db_object, instance):
        db_object = instance
        with Session(self.engine) as session:
            session.add(db_object)
            session.commit()
            session.refresh(db_object)
        return db_object

    def delete(self, db_object):
        with Session(self.engine) as session:
            session.delete(db_object)
            session.commit()
