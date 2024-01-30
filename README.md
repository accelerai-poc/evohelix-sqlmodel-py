# Evohelix SQLModel Python wrapper

## Installation

```bash
pip install 'evohelix_sqlm @ git+https://github.com/accelerai-poc/evohelix-sqlmodel-py@main'
```

## Usage

- create data model: setup your data model classes in pydantic-like manner:
```python
from typing import Optional
from sqlmodel import Field, SQLModel

class MyModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    my_first_att: str
    my_second_optional_att:  Optional[int] = None
```

## Migrations using Alembic
1. prepare migrations by adding your data model classes to `alembic/env.py` and setting the `sqlalchemy.url` (see `evohelix-service-template`):
```python
from myapp.models import MyModel # <-- add this line in import section before running any code
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI) # need to set 'SQLALCHEMY_DATABASE_URI' in settings.py
```
3. run migration bash inside container or from host with docker compose:
```bash
alembic upgrade head
``` 
```bash
docker compose exec web alembic upgrade head
``` 