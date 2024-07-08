import re
from sqlmodel import col, or_, and_, not_


# Parse complex query parameters into a filter system
def parse_filters(model, params):
    where = []
    order_by = None
    offset = None
    limit = None

    def parse_param(param, value):
        if m := re.search(r"(?P<key>.*)\[(?P<op>.*)\]", param):
            return {"key": m.group("key"), "op": m.group("op"), "val": value}
        return {"key": param, "op": "eq", "val": value}

    for k, v in params.items():
        if k == 'order_by':
            if v not in model.__dict__.keys():
                raise KeyError(f'Order key {v} is not part of the {model} model.')
            order_by = v
        elif k == 'offset':
            offset = v
        elif k == 'limit':
            limit = v
        else:
            condition = parse_param(k, v)
            if condition["key"] not in model.__dict__.keys():
                raise KeyError(f'Filter key {condition["key"]} is not part of the {model} model.')
            if condition["op"] == "gt":
                where.append(getattr(model, condition["key"]) > condition["val"])
            elif condition["op"] == "gte":
                where.append(getattr(model, condition["key"]) >= condition["val"])
            elif condition["op"] == "lt":
                where.append(getattr(model, condition["key"]) < condition["val"])
            elif condition["op"] == "lte":
                where.append(getattr(model, condition["key"]) <= condition["val"])
            elif condition["op"] == "eq":
                where.append(getattr(model, condition["key"]) == condition["val"])
            elif condition["op"] == "neq":
                where.append(getattr(model, condition["key"]) != condition["val"])
            elif condition["op"] == "like":
                where.append(col(getattr(model, condition["key"])).contains(condition["val"]))
    return where, order_by, limit, offset


def _transform_query(model, query, key=None):
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
