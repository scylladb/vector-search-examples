import os
import psutil
import time
import threading
from tqdm import tqdm
from multiprocessing import Event, Process, Value, cpu_count
from cassandra.concurrent import execute_concurrent_with_args
from db.scylladb import ScyllaClient


class ScyllaLoader:
    """ScyllaDB data ingestion class with multiprocessing support"""
    
    MAX_RETRIES = 5
    RETRY_DELAY = 0.5

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
        (
            worker_id,
            concurrency,
            data_chunk, 
            event, 
            insert_stmt,
            counter
        ) = args
        

        try:
            p = psutil.Process(os.getpid())
            cpu_count = psutil.cpu_count(logical=True)
            p.cpu_affinity([worker_id % cpu_count])
        except Exception as e:
            pass
        session = ScyllaClient().get_session()
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
            batch = batch_data[i:i + batch_size]
            attempt = 0
            
            while attempt < self.MAX_RETRIES:
                try:
                    execute_concurrent_with_args(session, prepared_stmt, batch, concurrency=concurrency)
                    break
                except Exception as e:
                    print(e)
                    attempt += 1
                    if attempt >= self.MAX_RETRIES:
                        event.set()
                        session.shutdown()
                        return
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
            with counter.get_lock():
                counter.value += len(batch)
        
        session.shutdown()
        

    def _create_chunks(self, data: list[dict], processes: int) -> list[list[dict]]:
        """Split data into chunks for multiprocessing"""
        chunk_size = len(data) // processes
        remainder = len(data) % processes
        data_chunks = []
        start_idx = 0
        
        for i in range(processes):
            end_idx = start_idx + chunk_size + (1 if i < remainder else 0)
            data_chunks.append(data[start_idx:end_idx])
            start_idx = end_idx
        
        return data_chunks

    def _generate_insert_statement(self, keyspace: str, table: str, columns: list[str]) -> str:
        """Generate dynamic INSERT statement based on columns"""
        column_names = ', '.join(columns)
        placeholders = ', '.join(['?' for _ in columns])
        insert_stmt = f"INSERT INTO {keyspace}.{table} ({column_names}) VALUES ({placeholders});"
        return insert_stmt

    def ingest_data(self, data: list[dict], address=None, keyspace='test', dc='datacenter1', 
                   compression=False, concurrency=10, table='kv'):
        """
        Public API function to ingest data into ScyllaDB
        
        Args:
            data: List of dictionaries where each dict represents a row
            address: ScyllaDB address (uses config if None)
            keyspace: Keyspace name (default: 'test')
            dc: Datacenter name (default: 'datacenter1')
            compression: Enable LZ4 compression (default: False)
            concurrency: Concurrent operations per process (default: 10)
            table: Table name (default: 'kv')
        """
        if not isinstance(data, list) or not data:
            raise ValueError("Data must be a non-empty list of dictionaries")
        
        if not isinstance(data[0], dict):
            raise ValueError("Data must be a list of dictionaries")

        processes = cpu_count()
        
        # Split data among processes
        event = Event()
        data_chunks = self._create_chunks(data, processes)
        
        # Progress tracker counter
        counter = Value('i', 0)
        
        # Prepare arguments for each worker
        columns = list(data[0].keys())
        insert_stmt = self._generate_insert_statement(keyspace, table, columns)
        input_args = []
        
        for i, chunk in enumerate(data_chunks):
            if chunk:
                input_args.append((i, concurrency, chunk, event, insert_stmt, counter))
        
        row_count = len(data)
        progress_thread = self._start_monitor(counter, row_count, event)
        
        # Start worker processes
        start = time.time()
        plist = []
        for worker_args in input_args:
            p = Process(target=self._worker, args=(worker_args,))
            p.start()
            plist.append(p)
        
        # Wait for all workers to complete
        for p in plist:
            p.join()
        
        # Stop progress monitoring
        event.set()
        progress_thread.join(timeout=1)
        
        duration = time.time() - start
        if counter.value < row_count:
            print(f"❌ Aborted due to repeated failures. Processed {counter.value}/{row_count} records.")
        else:
            print(f"✅ Done running {row_count} operations in {duration:.2f} seconds.")
            print(f"📈 Throughput: {row_count/duration:.0f} ops/sec")
