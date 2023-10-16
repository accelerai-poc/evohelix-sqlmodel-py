import re
import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from sqlmodel import col
from .db import DBEngine

router = APIRouter()
db = DBEngine()


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
                raise HTTPException(
                    status_code=400,
                    detail=f'Order key {v} is not part of the {model} model.'
                )
            order_by = v
        elif k == 'offset':
            offset = v
        elif k == 'limit':
            limit = v
        else:
            condition = parse_param(k, v)
            if condition["key"] not in model.__dict__.keys():
                raise HTTPException(
                    status_code=400,
                    detail=f'Filter key {condition["key"]} is not part of the {model} model.'
                )
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


def post(instance):
    db_object = db.create(instance)
    return Response(db_object.json(),
                    status_code=201,
                    media_type="application/json")


def read_all(model, r: Request):
    result = db.read(model, *parse_filters(model, r.query_params))
    if not result or len(result) == 0:
        return Response(status_code=204)
    result = "[" + ", ".join([m.json() for m in result]) + "]"
    return Response(result,
                    status_code=200,
                    media_type="application/json")


def read(model, id: uuid.UUID):
    result = db.read(model, [model.id == id])
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f'{model} object with id {id} not found.'
        )
    return Response(result[0].json(),
                    status_code=200,
                    media_type="application/json")


def patch(model, id: uuid.UUID, instance):
    db_object = db.exists(model, id)
    if not db_object:
        raise HTTPException(
            status_code=404,
            detail=f'{model} object with id {id} not found.'
        )

    if all([getattr(instance, k) == getattr(db_object, k)
            for k in instance.keys()]):
        return Response(status_code=304)

    db_object = db.update(db_object, instance)
    return Response(db_object.json(),
                    status_code=200,
                    media_type="application/json")


def put(model, instance):
    db_object = db.exists(model, id)
    if not db_object:
        return post(model)

    if db_object == instance:
        return Response(status_code=304)

    db_object = db.replace(db_object, instance)
    return Response(db_object.json(),
                    status_code=200,
                    media_type="application/json")


def delete(model, id: uuid.UUID):
    db_object = db.exists(model, id)
    if not db_object:
        raise HTTPException(
            status_code=404,
            detail=f'{model} object with id {id} not found.'
        )
    db.delete(db_object)
    return Response(status_code=204)
