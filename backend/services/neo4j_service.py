from functools import lru_cache

from neo4j import GraphDatabase

from backend.core.config import settings


@lru_cache(maxsize=1)
def get_neo4j_driver():
    return GraphDatabase.driver(settings.neo4j_uri, auth=settings.neo4j_auth)


def close_neo4j_driver() -> None:
    driver = get_neo4j_driver()
    driver.close()
    get_neo4j_driver.cache_clear()
