import re
from sqlmodel import col


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
