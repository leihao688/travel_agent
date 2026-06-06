import os
import yaml


def load_config(config_path: str, encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "yamlConfig")
rag_config = load_config(os.path.join(config_dir, "rag.yaml"))

chorma_config = load_config(os.path.join(config_dir, "chorma.yaml"))
prompts_config = load_config(os.path.join(config_dir, "prompt.yaml"))
redis_config = load_config(os.path.join(config_dir, "redis.yaml"))
mysql_config = load_config(os.path.join(config_dir, "mysql.yaml"))
if __name__ == "__main__":
    print(prompts_config["rag_weather_path"])
    print(chorma_config["collection_name"])
    print(redis_config)
