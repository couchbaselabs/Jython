'''
Created on Sep 25, 2017

@author: riteshagarwal
'''
from memcached.helper.kvstore import KVStore

class Bucket():
    def __init__(self, bucket_size='', name="", num_replicas=0, port=11211, master_id=None,
                 type='', eviction_policy="valueOnly", bucket_priority=None, uuid="", lww=False,
                 storageBackend="couchstore"):
        self.name = name
        self.port = port
        self.type = type
        self.nodes = None
        self.stats = None
        self.servers = []
        self.vbuckets = []
        self.forward_map = []
        self.numReplicas = num_replicas
        self.bucket_size = bucket_size
        self.kvs = {1:KVStore()}
        self.master_id = master_id
        self.eviction_policy = eviction_policy
        self.bucket_priority = bucket_priority
        self.uuid = uuid
        self.lww = lww
        self.storageBackend = storageBackend

    def __str__(self):
        return self.name

class vBucket():
    def __init__(self):
        self.master = ''
        self.replica = []
        self.id = -1

class BucketStats():
    def __init__(self):
        self.opsPerSec = 0
        self.itemCount = 0
        self.diskUsed = 0
        self.memUsed = 0
        self.ram = 0
        
