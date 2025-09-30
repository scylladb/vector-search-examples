from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config

class ScyllaClient():
    
    def __init__(self, keyspace: str = None):
        self.cluster = self._get_cluster(config.SCYLLADB_CONFIG)
        if keyspace:
            self.session = self.cluster.connect(keyspace)
        else:
            self.session = self.cluster.connect()
        
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
        
    def query_data(self, query, params=[]):
        rows = self.session.execute(query, params)
        return rows.all()