import contextlib
import importlib.util
import io
import json

payload = json.loads(open("/source/input.json", encoding="utf-8").read())
config = json.loads(open("/source/config.json", encoding="utf-8").read())
spec = importlib.util.spec_from_file_location("solution", "/source/solution.py")
module = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(module)
    if config["kind"] == "mapreduce_function":
        grouped = {}
        mapper = getattr(module, config["map_function"])
        reducer = getattr(module, config["reduce_function"])
        for line in payload["lines"]:
            for key, value in mapper(line):
                grouped.setdefault(key, []).append(value)
        result = [list(reducer(key, grouped[key])) for key in sorted(grouped)]
    else:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.master("local[1]").appName("eklavya").config("spark.ui.enabled", "false").getOrCreate()
        try:
            frame = spark.createDataFrame(payload["rows"], payload["columns"])
            result_frame = getattr(module, config["function"])(frame)
            if config.get("sort"):
                result_frame = result_frame.orderBy(*config["sort"])
            result = {"columns": result_frame.columns, "rows": [list(row) for row in result_frame.collect()]}
        finally:
            spark.stop()
print("__EKLAVYA_RESULT__" + json.dumps(result, separators=(",", ":")))
