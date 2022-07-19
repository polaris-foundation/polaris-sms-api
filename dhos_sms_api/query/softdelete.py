from typing import Any

from flask_sqlalchemy import BaseQuery


class QueryWithSoftDelete(BaseQuery):
    def __new__(cls, *args: Any, **kwargs: Any) -> "QueryWithSoftDelete":
        obj: "QueryWithSoftDelete" = super(QueryWithSoftDelete, cls).__new__(cls)
        with_deleted: bool = kwargs.pop("_with_deleted", False)
        if len(args) > 0:
            super(QueryWithSoftDelete, obj).__init__(*args, **kwargs)
            return obj.filter_by(deleted=None) if not with_deleted else obj
        return obj

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass
