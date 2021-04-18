from itertools import chain


def get_loaders(items):
    return list(
        chain.from_iterable(
            item.get_loaders() for item in items if hasattr(item, "get_loaders")
        )
    )


def value_default(row, default="Ø"):
    return row if row["value"] else (row | {"value": default})
