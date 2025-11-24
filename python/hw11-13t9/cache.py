import redis

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
)


def invalidate_students_cache() -> None:
    pattern = "students:*"
    for key in redis_client.scan_iter(pattern):
        redis_client.delete(key)
