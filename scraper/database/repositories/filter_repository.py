"""Repository for maintaining the unified movie_filters collection."""

from app.db.collections import MOVIES, MOVIE_FILTERS

# Fields that are arrays on movie documents
_ARRAY_FIELDS: dict[str, str] = {
    "actors": "actor",
    "tags": "tag",
}

# Fields that are scalars on movie documents
_SCALAR_FIELDS: dict[str, str] = {
    "director": "director",
    "maker": "maker",
    "series": "series",
}

# All fields to project from movies collection
_PROJECT_FIELDS = {f: 1 for f in list(_ARRAY_FIELDS) + list(_SCALAR_FIELDS)}


def sync_movie_filters(db) -> dict[str, int]:
    """Scan all movies, deduplicate filter values, and write to movie_filters.

    Args:
        db: MongoDB database instance from get_mongo_db().

    Returns:
        Dict with counts per filter type: actors, tags, directors, makers, series.
    """
    col = db[MOVIES]

    accumulators: dict[str, set[str]] = {v: set() for v in _ARRAY_FIELDS.values()}
    accumulators.update({v: set() for v in _SCALAR_FIELDS.values()})

    for doc in col.find({}, _PROJECT_FIELDS):
        # Array fields
        for field, filter_type in _ARRAY_FIELDS.items():
            for val in doc.get(field, []):
                if isinstance(val, str) and val.strip():
                    accumulators[filter_type].add(val.strip())
        # Scalar fields
        for field, filter_type in _SCALAR_FIELDS.items():
            val = doc.get(field, "")
            if isinstance(val, str) and val.strip():
                accumulators[filter_type].add(val.strip())

    db[MOVIE_FILTERS].drop()

    docs_to_insert = []
    for filter_type, names in accumulators.items():
        for name in sorted(names):
            docs_to_insert.append({"type": filter_type, "name": name})

    if docs_to_insert:
        db[MOVIE_FILTERS].insert_many(docs_to_insert)

    return {
        "actors": len(accumulators.get("actor", set())),
        "tags": len(accumulators.get("tag", set())),
        "directors": len(accumulators.get("director", set())),
        "makers": len(accumulators.get("maker", set())),
        "series": len(accumulators.get("series", set())),
    }
