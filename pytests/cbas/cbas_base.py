import json
from TestInput import TestInputSingleton
from remote.remote_util import RemoteMachineShellConnection
from basetestcase import BaseTestCase
from lib.couchbase_helper.analytics_helper import AnalyticsHelper
from couchbase_helper.documentgenerator import DocumentGenerator
from lib.membase.api.rest_client import RestConnection, RestHelper, Bucket
from lib.couchbase_helper.cluster import *
from testconstants import FTS_QUOTA, CBAS_QUOTA, INDEX_QUOTA, MIN_KV_QUOTA, JAVA_RUN_TIMES

from cbas_utils import cbas_utils
import logger
from cluster_utils.cluster_ready_functions import cluster_utils


class CBASBaseTest(BaseTestCase):
    
    def setUp(self, add_defualt_cbas_node = True):
        self.log = logger.Logger.get_logger()
        if self._testMethodDoc:
            self.log.info("\n\nStarting Test: %s \n%s"%(self._testMethodName,self._testMethodDoc))
        else:
            self.log.info("\n\nStarting Test: %s"%(self._testMethodName))
        super(CBASBaseTest, self).setUp()
        self.cbas_node = self.input.cbas
        self.cbas_servers = []
        self.kv_servers = []
 
        for server in self.servers:
            if "cbas" in server.services:
                self.cbas_servers.append(server)
            if "kv" in server.services:
                self.kv_servers.append(server)
            rest = RestConnection(server)
            rest.set_data_path(data_path=server.data_path,index_path=server.index_path,cbas_path=server.cbas_path)
            
        self.analytics_helper = AnalyticsHelper()
        self._cb_cluster = self.cluster
        self.travel_sample_total_docs_count = 63182
        self.travel_sample_docs_count = 31591
        self.beer_sample_docs_count = 7303
        invalid_ip = '10.111.151.109'
        self.cb_bucket_name = self.input.param('cb_bucket_name', 'travel-sample')
        self.cbas_bucket_name = self.input.param('cbas_bucket_name', 'travel')
        self.cb_bucket_password = self.input.param('cb_bucket_password', None)
        self.expected_error = self.input.param("error", None)
        if self.expected_error:
            self.expected_error = self.expected_error.replace("INVALID_IP",invalid_ip)
            self.expected_error = self.expected_error.replace("PORT",self.master.port)
        self.cb_server_ip = self.input.param("cb_server_ip", None)
        self.cb_server_ip = self.cb_server_ip.replace('INVALID_IP',invalid_ip) if self.cb_server_ip is not None else None
        self.cbas_dataset_name = self.input.param("cbas_dataset_name", 'travel_ds')
        self.cbas_bucket_name_invalid = self.input.param('cbas_bucket_name_invalid', self.cbas_bucket_name)
        self.cbas_dataset2_name = self.input.param('cbas_dataset2_name', None)
        self.skip_create_dataset = self.input.param('skip_create_dataset', False)
        self.disconnect_if_connected = self.input.param('disconnect_if_connected', False)
        self.cbas_dataset_name_invalid = self.input.param('cbas_dataset_name_invalid', self.cbas_dataset_name)
        self.skip_drop_connection = self.input.param('skip_drop_connection',False)
        self.skip_drop_dataset = self.input.param('skip_drop_dataset', False)
        self.query_id = self.input.param('query_id',None)
        self.mode = self.input.param('mode',None)
        self.num_concurrent_queries = self.input.param('num_queries', 5000)
        self.concurrent_batch_size = self.input.param('concurrent_batch_size', 100)
        self.compiler_param = self.input.param('compiler_param', None)
        self.compiler_param_val = self.input.param('compiler_param_val', None)
        self.expect_reject = self.input.param('expect_reject', False)
        self.expect_failure = self.input.param('expect_failure', False)
        self.compress_dataset = self.input.param('compress_dataset', False)
        self.index_name = self.input.param('index_name', "NoName")
        self.index_fields = self.input.param('index_fields', None)
        if self.index_fields:
            self.index_fields = self.index_fields.split("-")
        self.otpNodes = []
        self.cbas_path = server.cbas_path

        self.retry_time = self.input.param("retry_time", 300)
        self.num_retries = self.input.param("num_retries", 1)
        
        self.set_cbas_memory_from_available_free_memory = self.input.param('set_cbas_memory_from_available_free_memory', False)
        self.rest = RestConnection(self.master)
        
        if not self.set_cbas_memory_from_available_free_memory:
            self.log.info("Setting the min possible memory quota so that adding more nodes to the cluster wouldn't be a problem.")
            self.rest.set_service_memoryQuota(service='memoryQuota', memoryQuota=MIN_KV_QUOTA)
            self.rest.set_service_memoryQuota(service='ftsMemoryQuota', memoryQuota=FTS_QUOTA)
            self.rest.set_service_memoryQuota(service='indexMemoryQuota', memoryQuota=INDEX_QUOTA)
            self.log.info("Setting %d memory quota for CBAS" % CBAS_QUOTA)
            self.cbas_memory_quota = CBAS_QUOTA
            self.rest.set_service_memoryQuota(service='cbasMemoryQuota', memoryQuota=CBAS_QUOTA)
        
        self.cbas_util = None
        # Drop any existing buckets and datasets
        if self.cbas_node:
            self.cbas_util = cbas_utils(self.master, self.cbas_node)
            self.cleanup_cbas()
                    
        if not self.cbas_node and len(self.cbas_servers)>=1:
            self.cbas_node = self.cbas_servers[0]
            if self.set_cbas_memory_from_available_free_memory:
                self.set_memory_for_services(
                    self.rest, self.cbas_node, self.cbas_node.services)
            self.cbas_util = cbas_utils(self.master, self.cbas_node)
            if "cbas" in self.master.services:
                self.cleanup_cbas()
            if add_defualt_cbas_node:
                if self.master.ip != self.cbas_node.ip:
                    self.otpNodes.append(cluster_utils(self.master).add_node(self.cbas_node))
                else:
                    self.otpNodes = self.rest.node_statuses()
                ''' This cbas cleanup is actually not needed.
                    When a node is added to the cluster, it is automatically cleaned-up.'''
                self.cleanup_cbas()
                self.cbas_servers.remove(self.cbas_node)
        
        self.log.info("==============  CBAS_BASE setup was finished for test #{0} {1} ==============" \
                          .format(self.case_number, self._testMethodName))
        
        if add_defualt_cbas_node and False:
            self.log.info("************************* Validate Java runtime *************************")
            analytics_node = []
            analytics_node.extend(self.cbas_servers)
            analytics_node.append(self.cbas_node)
            for server in analytics_node:
                self.log.info('Validating java runtime info for :' + server.ip)
                util = cbas_utils(self.master, server)
                diag_res = util.get_analytics_diagnostics(self.cbas_node)
                java_home = diag_res['runtime']['systemProperties']['java.home']
                self.log.info('Java Home : ' + java_home)
                
                java_runtime_name = diag_res['runtime']['systemProperties']['java.runtime.name']
                self.log.info('Java runtime : ' + java_runtime_name)
                
                java_runtime_version = diag_res['runtime']['systemProperties']['java.runtime.version']
                self.log.info('Java runtime version: ' + java_runtime_version)
                
                jre_info = JAVA_RUN_TIMES[self.jre_path]
                self.assertTrue(jre_info['java_home'] in java_home, msg='Incorrect java home value')
                self.assertEqual(java_runtime_name, jre_info['java_runtime_name'], msg='Incorrect java runtime name')
                self.assertTrue(java_runtime_version.startswith(jre_info['java_runtime_version']), msg='Incorrect java runtime version')
                util.closeConn()
        
        
    def tearDown(self):
        self.cbas_util.closeConn()
        super(CBASBaseTest, self).tearDown()
    
    def cleanup_cbas(self):
        """
        Drops all connections, datasets and buckets from CBAS
        """
        try:
            # Disconnect from all connected buckets
            cmd_get_buckets = "select Name from Metadata.`Bucket`;"
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
                cmd_get_buckets)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.disconnect_from_bucket(row['Name'],
                                                disconnect_if_connected=True)
                    self.log.info(
                        "********* Disconnected all buckets *********")
            else:
                self.log.info("********* No buckets to disconnect *********")

            # Drop all datasets
            cmd_get_datasets = "select DatasetName from Metadata.`Dataset` where DataverseName != \"Metadata\";"
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
                cmd_get_datasets)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.drop_dataset("`" +row['DatasetName'] + "`")
                    self.log.info("********* Dropped all datasets *********")
            else:
                self.log.info("********* No datasets to drop *********")

            # Drop all buckets
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
                cmd_get_buckets)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.drop_cbas_bucket("`" + row['Name'] + "`")
                    self.log.info("********* Dropped all buckets *********")
            else:
                self.log.info("********* No buckets to drop *********")
            
            self.log.info("Drop Dataverse other than Default and Metadata")
            cmd_get_dataverse = 'select DataverseName from Metadata.`Dataverse` where DataverseName != "Metadata" and DataverseName != "Default";'
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(cmd_get_dataverse)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.disconnect_link("`" + row['DataverseName'] + "`" + ".Local")
                    self.cbas_util.drop_dataverse_on_cbas(dataverse_name="`" + row['DataverseName'] + "`")
                self.log.info("********* Dropped all dataverse except Default and Metadata *********")
            else:
                self.log.info("********* No dataverse to drop *********")
                
        except Exception as e:
            self.log.info(e.message)
    
    def set_memory_for_services(self, master_rest, server, services):
        services = services.split(",")
        if len(services) > 0:
            service_mem_dict = {
                "kv": ["memoryQuota",MIN_KV_QUOTA],
                "fts": ["ftsMemoryQuota",FTS_QUOTA],
                "index": ["indexMemoryQuota",INDEX_QUOTA],
                "cbas": ["cbasMemoryQuota",CBAS_QUOTA]}
            
            if "n1ql" in services:
                services.remove("n1ql")
            
            # Get all services that are already running in cluster
            cluster_services = self.node_util.get_services_map(master=self.master)
            cluster_info = master_rest.get_nodes_self()
            
            rest = RestConnection(server)
            info = rest.get_nodes_self()
            memory_quota_available = info.mcdMemoryReserved
            
            if len(services) == 1:
                service = services[0]
                if service in cluster_services.keys():
                    if service is not "kv":
                        self.log.info("Setting {0} memory quota for {1}".format(memory_quota_available, service))
                        property_name = service_mem_dict[service][0]
                        service_mem_in_cluster = cluster_info.__getattribute__(property_name)
                        # if service is already in cluster we cannot increase the RAM allocation, but we can reduce the RAM allocation if needed.
                        if memory_quota_available < service_mem_in_cluster:
                            if memory_quota_available > service_mem_dict[service][1]:
                                master_rest.set_service_memoryQuota(service=property_name, memoryQuota=memory_quota_available)
                            else:
                                self.fail("Error while setting service memory quota {0} for {1}".format(service_mem_dict[service][1], service))                                    
                else:
                    self.log.info("Setting {0} memory quota for {1}".format(memory_quota_available, service))
                    if memory_quota_available > service_mem_dict[service][1]:
                        master_rest.set_service_memoryQuota(service=service_mem_dict[service][0], memoryQuota=memory_quota_available)
                    else:
                        self.fail("Error while setting service memory quota {0} for {1}".format(service_mem_dict[service][1], service))
            else:
                # if KV is present, then don't change the KV memory quota
                # It is assumed that KV node will always be present in the master node of cluster.
                if "kv" in services:
                    services.remove("kv")
                    memory_quota_available -= cluster_info.__getattribute__("memoryQuota")
                
                set_cbas_mem = False
                if "cbas" in services:
                    services.remove("cbas")
                    set_cbas_mem = True
                
                for service in services:
                    # setting minimum possible memory for other services.
                    self.log.info("Setting {0} memory quota for {1}".format(service_mem_dict[service][1], service))
                    if memory_quota_available >= service_mem_dict[service][1]:
                        master_rest.set_service_memoryQuota(service=service_mem_dict[service][0], memoryQuota=service_mem_dict[service][1])
                        memory_quota_available -= service_mem_dict[service][1]
                    else:
                        self.fail("Error while setting service memory quota {0} for {1}".format(service_mem_dict[service][1], service))
                
                if set_cbas_mem and memory_quota_available >= service_mem_dict["cbas"][1]:
                    if "cbas" in cluster_services.keys():
                        if cluster_info.__getattribute__("cbasMemoryQuota") >= memory_quota_available:
                            self.log.info("Setting {0} memory quota for CBAS".format(memory_quota_available))
                            master_rest.set_service_memoryQuota(service="cbasMemoryQuota", memoryQuota=memory_quota_available) 
                    else: 
                        self.log.info("Setting {0} memory quota for CBAS".format(memory_quota_available))
                        master_rest.set_service_memoryQuota(service="cbasMemoryQuota", memoryQuota=memory_quota_available)
                else:
                    self.fail("Error while setting service memory quota {0} for CBAS".format(memory_quota_available))
