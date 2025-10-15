import os
import psutil
import time
import threading
from tqdm import tqdm
from multiprocessing import Event, Process, Value, cpu_count
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT, Session
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
from cassandra.concurrent import execute_concurrent_with_args


class ScyllaLoader:
    """ScyllaDB data ingestion class. Supports single and multi-threaded ingestion."""

    MAX_RETRIES = 5
    RETRY_DELAY = 0.5

    def __init__(self,
                host: str, 
                passwd: str, 
                keyspace: str,
                user="scylla", 
                port=9042, 
                dc=""):
        self.session = self.create_session(host, passwd, keyspace, user, port, dc)

    def create_session(self,
                       host: str, 
                       passwd: str, 
                       keyspace: str,
                       user="scylla", 
                       port=9042, 
                       dc="") -> Session:
        profile = ExecutionProfile(
            load_balancing_policy=TokenAwarePolicy(
                DCAwareRoundRobinPolicy(local_dc=dc)
            ),
            row_factory=dict_factory,
        )
        cluster = Cluster(
            execution_profiles={EXEC_PROFILE_DEFAULT: profile},
            contact_points=[host, ],
            port=port,
            auth_provider=PlainTextAuthProvider(username=user, password=passwd),
        )
        return cluster.connect(keyspace)

    def _start_monitor(self, counter, total_rows, event):
        """Start progress monitoring thread"""
        pbar = tqdm(total=total_rows, dynamic_ncols=True, unit="req")

        def monitor():
            last = 0
            while last < total_rows and not event.is_set():
                with counter.get_lock():
                    current = counter.value
                if current > last:
                    pbar.update(current - last)
                    last = current
                else:
                    time.sleep(0.1)
            pbar.close()

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        return thread

    def _worker(self, args):
        """Worker process function for data ingestion"""
        (worker_id, concurrency, data_chunk, event, insert_stmt, counter) = args

        try:
            p = psutil.Process(os.getpid())
            cpu_count = psutil.cpu_count(logical=True)
            p.cpu_affinity([worker_id % cpu_count])
        except Exception as e:
            pass
        # create new session for each worker
        session = self.create_session()
        prepared_stmt = session.prepare(insert_stmt)

        # Convert dictionaries to tuples for batch insertion
        batch_data = []
        for item in data_chunk:
            # Convert dict to tuple maintaining key order
            row_tuple = tuple(item.values())
            batch_data.append(row_tuple)

        # Insert data in batches
        batch_size = concurrency

        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i : i + batch_size]
            attempt = 0
            while attempt < self.MAX_RETRIES:
                try:
                    execute_concurrent_with_args(
                        session, prepared_stmt, batch, concurrency=concurrency
                    )
                    break
                except Exception as e:
                    print(e)
                    attempt += 1
                    if attempt >= self.MAX_RETRIES:
                        event.set()
                        session.shutdown()
                        return
                    time.sleep(self.RETRY_DELAY * (2**attempt))
            with counter.get_lock():
                counter.value += len(batch)
        session.shutdown()

    def _create_chunks(self, data: list[dict], process_count: int) -> list[list[dict]]:
        """Split data into chunks for multiprocessing"""
        chunk_size = len(data) // process_count
        remainder = len(data) % process_count
        data_chunks = []
        start_idx = 0
        for i in range(process_count):
            end_idx = start_idx + chunk_size + (1 if i < remainder else 0)
            data_chunks.append(data[start_idx:end_idx])
            start_idx = end_idx
        return data_chunks

    def _generate_insert_statement(
        self, keyspace: str, table: str, columns: list[str]
    ) -> str:
        """Generate dynamic INSERT statement"""
        column_names = ", ".join(columns)
        placeholders = ", ".join(["?" for _ in columns])
        insert_stmt = (
            f"INSERT INTO {keyspace}.{table} ({column_names}) VALUES ({placeholders});"
        )
        return insert_stmt

    def multi_ingest(self, data: list[dict], keyspace: str, table: str, concurrency=10):
        """
        Ingest data into ScyllaDB using the `multiprocessing` module.

        `data` must be a list of dicts and each key must match the
        corresponding column name in the ScyllaDB table

        Args:
            data: List of dictionaries where each dict represents a row in the table
            keyspace: Keyspace name
            table: Table name
            concurrency: Concurrent operations per process (default: 10)

        """
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            raise ValueError("Data must be a non-empty list of dictionaries")

        process_count = cpu_count()

        # Split data among processes
        event = Event()
        data_chunks = self._create_chunks(data, process_count)

        # Progress tracker counter
        counter = Value("i", 0)
        row_count = len(data)
        progress_thread = self._start_monitor(counter, row_count, event)

        # Prepare arguments for each worker
        columns = list(data[0].keys())
        insert_stmt = self._generate_insert_statement(keyspace, table, columns)
        worker_args_list = []
        for i, chunk in enumerate(data_chunks):
            if chunk:
                worker_args = (i, concurrency, chunk, event, insert_stmt, counter)
                worker_args_list.append(worker_args)

        # Start worker processes
        start_time = time.time()
        process_list = []
        for worker_args in worker_args_list:
            p = Process(target=self._worker, args=(worker_args,))
            p.start()
            process_list.append(p)

        # Wait for all workers to complete
        for p in process_list:
            p.join()

        # Stop progress monitoring
        event.set()
        progress_thread.join(timeout=1)

        duration = time.time() - start_time
        if counter.value < row_count:
            print(
                f"❌ Aborted due to repeated failures. Processed {counter.value}/{row_count} records."
            )
        else:
            print(f"✅ Done running {row_count} operations in {duration:.2f} seconds.")
            print(f"📈 Throughput: {row_count/duration:.0f} ops/sec")
            
    def single_ingest(self, table: str, data: dict):
        """
        Ingest a single row into ScyllaDB.

        `data` must be a dict and each key must match the
        corresponding column name in the ScyllaDB table

        Args:
            data: Dictionary that represents a row in the table
            keyspace: Keyspace name
            table: Table name
        """
        columns = list(data.keys())
        values = list(data.values())
        insert_query = f"""
        INSERT INTO {table} ({','.join(columns)}) 
        VALUES ({','.join(['%s' for c in columns])});
        """
        self.session.execute(insert_query, values)
