from sqlmodel import SQLModel, Session
from sqlmodel import create_engine, select, or_, and_, not_
from python_settings import settings
from sqlalchemy.inspection import inspect
from sqlalchemy import true
import json


def _transform_query(model, query, key=None):
    if not query:  # [], {} or None
        return [true()]
    
    if type(query) is dict:
        conditions = []
        for k, v in query.items():
            match k:
                case '$and':
                    assert type(v) is list
                    conditions.append(and_(*_transform_query(model, v)))
                case '$or':
                    assert type(v) is list
                    conditions.append(or_(*_transform_query(model, v)))
                case '$nor':
                    assert type(v) is list
                    conditions.append(not_(and_(*_transform_query(model, v))))
                case '$not':
                    conditions.append(not_(_transform_query(model, v)))
                case '$eq':
                    conditions.append(getattr(model, key) == v)
                case '$ne':
                    conditions.append(getattr(model, key) != v)
                case '$lt':
                    conditions.append(getattr(model, key) < v)
                case '$lte':
                    conditions.append(getattr(model, key) <= v)
                case '$gt':
                    conditions.append(getattr(model, key) > v)
                case '$gte':
                    conditions.append(getattr(model, key) >= v)
                case '$in':
                    assert type(v) is list
                    conditions.append(getattr(model, key).in_(v))
                case '$nin':
                    assert type(v) is list
                    conditions.append(not_(getattr(model, key).in_(v)))
                case _:  # must be field name
                    conditions.append(_transform_query(model, v, k))
        return conditions if len(conditions) > 1 else conditions[0]
    elif type(query) is list:
        return [_transform_query(model, x) for x in query]
    else:  # must be shorthand for $eq
        return getattr(model, key) == query


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
            if type(where) is not list:
                where = [where]
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

    def fetch(self, model, filter, projection, options):
        result = self.read(
            model,
            _transform_query(model, filter),
            options.get("sort", None),
            options.get("limit", 25),
            options.get("skip", 0))
        if projection is None or len(projection) == 0:
            return [json.loads(r.json()) for r in result]
        return [{k: v for k, v in json.loads(r.json()).items() if k in projection} for r in result]
