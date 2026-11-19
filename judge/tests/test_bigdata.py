from pathlib import Path

from judge.specialized import RUNNERS


def test_bigdata_runner_covers_spark_and_mapreduce_contracts():
    source = (Path(RUNNERS) / "bigdata_runner.py").read_text()
    assert 'config["kind"] == "mapreduce_function"' in source
    assert 'SparkSession.builder.master("local[1]")' in source
    assert 'config("spark.ui.enabled", "false")' in source
