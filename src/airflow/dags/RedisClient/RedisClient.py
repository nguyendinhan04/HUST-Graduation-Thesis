import redis
import os
from default_config import DEFAULTS


class RedisClient:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST",DEFAULTS["REDIS_HOST"])
        self.redis_port = os.getenv("REDIS_PORT",DEFAULTS["REDIS_PORT"])
        self.redis_db = os.getenv("REDIS_DB",DEFAULTS["REDIS_DB"])
        self.pool = redis.ConnectionPool(host=self.redis_host, port=self.redis_port, db=self.redis_db)
        self.redis = redis.Redis(connection_pool=self.pool, charset="utf-8", decode_responses=True)

    def check_id_exist(self, id, set_name):
        """_summary_

        Args:
            id (_type_): id of data ( generate by url or id of data in website)
            set_name (_type_): name of set in redis

        Returns:
            _type_: False if id not exist and no add to set, True if id exist
        """
        # print(id)
        return self.redis.sismember(set_name, id)

    def add_id_to_set(self, id, set_name):
        """_summary_

        Args:
            id (_type_): id of data ( generate by url or id of data in website)
            set_name (_type_): name of set in redis

        Returns:
            _type_: False if add fail, True if add success
        """
        return self.redis.sadd(set_name, id)
    def add_process_path(self,csv_path: str) -> str:
        """_summary_

        Args:
            csv_path (str): path of csv file

        Returns:
            str: process id
        """
        process_id = str(self.redis.incr("process_id_counter"))
        self.redis.hset("process_paths", process_id, csv_path)
        return process_id