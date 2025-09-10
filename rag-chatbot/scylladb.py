from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
import os
import config

class ScyllaClient():
    
    def __init__(self, migrate=False):
        if  os.getenv("scylla_host") is None:
            scylla_config = config.SCYLLADB_CONFIG
        else:
            scylla_config = {
                "host": os.getenv("scylla_host"),
                "port": int(os.getenv("scylla_port")),
                "username": os.getenv("scylla_user"),
                "password": os.getenv("scylla_password"),
                "keyspace": "rag", # hardcoded for simplicity, might change later
                "datacenter": os.getenv("scylla_datacenter")
            }
        
        self.cluster = self._get_cluster(scylla_config)
        if migrate:
            self.session = self.cluster.connect()
        else:
            self.session = self.cluster.connect(scylla_config["keyspace"])
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.shutdown()
        
    def shutdown(self):
        self.cluster.shutdown()

    def _get_cluster(self, config: dict) -> Cluster:
        profile = ExecutionProfile(
            load_balancing_policy=TokenAwarePolicy(
                    DCAwareRoundRobinPolicy(local_dc=config["datacenter"])
                ),
                row_factory=dict_factory
            )
        return Cluster(
            execution_profiles={EXEC_PROFILE_DEFAULT: profile},
            contact_points=[config["host"], ],
            port=config["port"],
            auth_provider = PlainTextAuthProvider(username=config["username"],
                                                  password=config["password"]))
    
    def print_metadata(self):
        for host in self.cluster.metadata.all_hosts():
            print(f"Datacenter: {host.datacenter}; Host: {host.address}; Rack: {host.rack}")
    
    def get_session(self):
        return self.session
    
    def insert_data(self, table, data: dict):
        columns = list(data.keys())
        values = list(data.values())
        insert_query = f"""
        INSERT INTO {table} ({','.join(columns)}) 
        VALUES ({','.join(['%s' for c in columns])});
        """
        self.session.execute(insert_query, values)
        
    def query_data(self, query, values=[]):
        rows = self.session.execute(query, values)
        return rows.all()