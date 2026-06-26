"""Repository for maintaining actor and tag filter collections."""

from app.db.collections import MOVIES, MOVIE_ACTORS, MOVIE_TAGS


def sync_movie_filters(db) -> dict[str, int]:
    """Scan all movies, deduplicate actors/tags, and write to movie_actors/movie_tags.

    Args:
        db: MongoDB database instance from get_mongo_db().

    Returns:
        Dict with 'actors' and 'tags' counts.
    """
    col = db[MOVIES]

    actors_set: set[str] = set()
    tags_set: set[str] = set()

    for doc in col.find({}, {"actors": 1, "tags": 1}):
        for actor in doc.get("actors", []):
            if isinstance(actor, str) and actor.strip():
                actors_set.add(actor.strip())
        for tag in doc.get("tags", []):
            if isinstance(tag, str) and tag.strip():
                tags_set.add(tag.strip())

    db[MOVIE_ACTORS].drop()
    db[MOVIE_TAGS].drop()

    if actors_set:
        db[MOVIE_ACTORS].insert_many(
            [{"name": name} for name in sorted(actors_set)]
        )
    if tags_set:
        db[MOVIE_TAGS].insert_many(
            [{"name": name} for name in sorted(tags_set)]
        )

    return {"actors": len(actors_set), "tags": len(tags_set)}
