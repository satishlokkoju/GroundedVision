"""
Ground Truth Store — S3 + Parquet + Athena
------------------------------------------
  - S3 + Parquet as immutable source of truth (versioned)
  - Athena for SQL queries on top of the data
  - Local in-memory cache (pandas) for fast access during a session
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

import awswrangler as wr
import boto3
import pandas as pd

from loguru import logger

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class GroundTruthConfig:
    """Central config"""

    def __init__(
        self,
        bucket: str,
        prefix: str = "ground-truth/",
        athena_database: str = "ground_truth_db",
        athena_table: str = "ground_truth",
        athena_output_bucket: str = None,  # defaults to same bucket under /athena-results/
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        self.athena_database = athena_database
        self.athena_table = athena_table
        self.athena_output_bucket = athena_output_bucket or bucket
        self.athena_output_prefix = "athena-results/"
        self.region = region

    @property
    def s3_base_path(self) -> str:
        return f"s3://{self.bucket}/{self.prefix}"

    @property
    def athena_output_path(self) -> str:
        return f"s3://{self.athena_output_bucket}/{self.athena_output_prefix}"


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

# Expected schema for ground truth records.
# Extend this to match your actual columns.
SCHEMA = {
    "id": str,                  # unique identifier
    "folder_name": str,         # string column folder name
    "old_video_frame_name": str,      # string column old video frame name
    "new_video_frame_name": str,      # string column new video frame name
    "metadata": dict,           # video frame metadata
    "annotated_by": str,        # string column annotated by
    "label": str,               # string column label
    "created_at": str,          # ISO timestamp
    "updated_at": str,
}


def _serialize_record(record: dict) -> dict:
    """Prepare a record for storage — converts dicts to JSON strings."""
    out = dict(record)
    for key, expected_type in SCHEMA.items():
        if key in out and expected_type is dict:
            if isinstance(out[key], dict):
                out[key] = json.dumps(out[key])
    return out


def _deserialize_record(record: dict) -> dict:
    """Restore a record from storage — parses JSON strings back to dicts."""
    out = dict(record)
    for key, expected_type in SCHEMA.items():
        if key in out and expected_type is dict:
            if isinstance(out[key], str):
                try:
                    out[key] = json.loads(out[key])
                except (json.JSONDecodeError, TypeError):
                    pass
    return out


# ---------------------------------------------------------------------------
# Core store
# ---------------------------------------------------------------------------

class GroundTruthStore:
    """
    Manages ground truth data on S3 as partitioned Parquet files.

    Partition scheme:  s3://<bucket>/<prefix>/year=YYYY/month=MM/day=DD/
    This makes Athena queries on date ranges very efficient.

    Usage:
        config = GroundTruthConfig(bucket="my-bucket")
        store = GroundTruthStore(config)

        # Write
        store.put_record({"id": "abc", "label": "cat", "score": 0.95, "metadata": {"src": "cam1"}})

        # Read
        record = store.get_record("abc")

        # SQL
        df = store.query("SELECT label, AVG(score) FROM ground_truth GROUP BY label")
    """

    def __init__(self, config: GroundTruthConfig):
        self.config = config
        self.session = boto3.Session(region_name=config.region)
        self._cache: dict[str, dict] = {}  # in-memory cache keyed by record id

    # ------------------------------------------------------------------
    # Partition helpers
    # ------------------------------------------------------------------

    def _partition_path(self, dt: datetime = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return (
            f"{self.config.s3_base_path}"
            f"year={dt.year}/month={dt.month:02d}/day={dt.day:02d}/"
        )

    # ------------------------------------------------------------------
    # Setters (write)
    # ------------------------------------------------------------------

    def put_record(self, record: dict, partition_dt: datetime = None) -> str:
        """
        Write a single record to S3 as Parquet.

        Args:
            record:       dict matching SCHEMA. 'id' is required.
            partition_dt: override partition date (defaults to now).

        Returns:
            The S3 path where the record was written.
        """
        if "id" not in record:
            raise ValueError("Record must contain an 'id' field.")

        now = datetime.now(timezone.utc).isoformat()
        record.setdefault("created_at", now)
        record["updated_at"] = now

        serialized = _serialize_record(record)
        df = pd.DataFrame([serialized])

        path = self._partition_path(partition_dt)
        wr.s3.to_parquet(
            df=df,
            path=path,
            dataset=True,           # enables partitioned dataset mode
            database=self.config.athena_database,
            table=self.config.athena_table,
            boto3_session=self.session,
            mode="append",
            schema_evolution=True,
        )

        # Update local cache
        self._cache[record["id"]] = record
        logger.info("Written record id=%s to %s", record["id"], path)
        return path

    def put_records(self, records: list[dict], partition_dt: datetime = None) -> str:
        """
        Batch write multiple records in a single Parquet file (more efficient).

        Args:
            records: list of dicts, each matching SCHEMA with an 'id' field.

        Returns:
            The S3 path written to.
        """
        now = datetime.now(timezone.utc).isoformat()
        serialized_rows = []
        for rec in records:
            if "id" not in rec:
                raise ValueError(f"Every record must have an 'id'. Got: {rec}")
            rec.setdefault("created_at", now)
            rec["updated_at"] = now
            serialized_rows.append(_serialize_record(rec))

        df = pd.DataFrame(serialized_rows)
        path = self._partition_path(partition_dt)

        wr.s3.to_parquet(
            df=df,
            path=path,
            dataset=True,
            database=self.config.athena_database,
            table=self.config.athena_table,
            boto3_session=self.session,
            mode="append",
            schema_evolution=True,
        )

        for rec in records:
            self._cache[rec["id"]] = rec
        logger.info("Written %d records to %s", len(records), path)
        return path

    # ------------------------------------------------------------------
    # Getters (read)
    # ------------------------------------------------------------------

    def get_record(self, record_id: str, use_cache: bool = True) -> Optional[dict]:
        """
        Fetch a single record by id.
        Checks local cache first, then queries Athena.

        Args:
            record_id: the 'id' value to look up.
            use_cache: if False, always hits Athena.

        Returns:
            dict or None if not found.
        """
        if use_cache and record_id in self._cache:
            logger.debug("Cache hit for id=%s", record_id)
            return self._cache[record_id]

        df = self.query(
            f"SELECT * FROM {self.config.athena_table} WHERE id = '{record_id}' LIMIT 1"
        )

        if df.empty:
            return None

        record = _deserialize_record(df.iloc[0].to_dict())
        self._cache[record_id] = record
        return record

    def get_records(
        self,
        filters: dict = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Fetch multiple records with optional column filters and date range.

        Args:
            filters:    {column: value} equality filters (ANDed together).
            start_date: filter partition >= this date.
            end_date:   filter partition <= this date.
            limit:      max rows returned.

        Returns:
            pandas DataFrame with JSON columns already deserialized.
        """
        where_clauses = []

        if filters:
            for col, val in filters.items():
                if isinstance(val, str):
                    where_clauses.append(f"{col} = '{val}'")
                else:
                    where_clauses.append(f"{col} = {val}")

        if start_date:
            where_clauses.append(
                f"(year > {start_date.year} OR "
                f"(year = {start_date.year} AND month >= {start_date.month}))"
            )
        if end_date:
            where_clauses.append(
                f"(year < {end_date.year} OR "
                f"(year = {end_date.year} AND month <= {end_date.month}))"
            )

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT * FROM {self.config.athena_table} {where_sql} LIMIT {limit}"

        df = self.query(sql)

        # Deserialize JSON columns
        json_cols = [k for k, v in SCHEMA.items() if v is dict and k in df.columns]
        for col in json_cols:
            df[col] = df[col].apply(
                lambda x: json.loads(x) if isinstance(x, str) else x
            )

        return df

    def get_dataframe(self, partition_dt: datetime = None) -> pd.DataFrame:
        """
        Load ground truth data directly from S3 into a DataFrame.
        Faster than Athena for full-partition reads.

        Args:
            partition_dt: the date partition to load. If None, loads ALL data
                          across every partition.

        Returns:
            pandas DataFrame.
        """
        if partition_dt:
            path = self._partition_path(partition_dt)
        else:
            path = self.config.s3_base_path
        logger.info("Reading data from %s", path)
        df = wr.s3.read_parquet(path=path, boto3_session=self.session)

        json_cols = [k for k, v in SCHEMA.items() if v is dict and k in df.columns]
        for col in json_cols:
            df[col] = df[col].apply(
                lambda x: json.loads(x) if isinstance(x, str) else x
            )
        return df

    # ------------------------------------------------------------------
    # SQL queries via Athena
    # ------------------------------------------------------------------

    def query(self, sql: str) -> pd.DataFrame:
        """
        Run any SQL query against the ground truth table using Athena.

        The table is automatically registered in the Glue catalog when you
        use put_record / put_records with dataset=True.

        Args:
            sql: standard SQL string. Table name = config.athena_table.

        Returns:
            pandas DataFrame with results.

        Examples:
            store.query("SELECT * FROM ground_truth LIMIT 10")
            store.query("SELECT label, COUNT(*) as cnt FROM ground_truth GROUP BY label")
            store.query(\"\"\"
                SELECT id, label, score,
                       json_extract_scalar(metadata, '$.src') AS source
                FROM ground_truth
                WHERE score > 0.9
            \"\"\")
        """
        logger.info("Running Athena query: %s", sql[:200])
        df = wr.athena.read_sql_query(
            sql=sql,
            database=self.config.athena_database,
            s3_output=self.config.athena_output_path,
            boto3_session=self.session,
            ctas_approach=False,    # set True for very large result sets
        )
        return df

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.info("Cache cleared.")

    def warm_cache(self, record_ids: list[str]):
        """Pre-load specific records into cache via a single Athena query."""
        id_list = ", ".join(f"'{rid}'" for rid in record_ids)
        df = self.query(
            f"SELECT * FROM {self.config.athena_table} WHERE id IN ({id_list})"
        )
        for _, row in df.iterrows():
            record = _deserialize_record(row.to_dict())
            self._cache[record["id"]] = record
        logger.info("Warmed cache with %d records.", len(df))
