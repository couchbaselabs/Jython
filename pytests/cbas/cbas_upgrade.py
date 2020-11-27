import logger
import testconstants

from threading import Thread
from lib.couchbase_helper.analytics_helper import AnalyticsHelper
from lib.membase.api.rest_client import RestConnection, RestHelper
from sdk_client import SDKClient
from testconstants import FTS_QUOTA, CBAS_QUOTA, INDEX_QUOTA, MIN_KV_QUOTA, JAVA_RUN_TIMES
from cbas_utils import cbas_utils
from cluster_utils.cluster_ready_functions import cluster_utils

from remote.remote_util import RemoteMachineShellConnection
from newupgradebasetest import NewUpgradeBaseTest


class CbasUpgrade(NewUpgradeBaseTest):

    def setUp(self):
        self.log = logger.Logger.get_logger()
        if self._testMethodDoc:
            self.log.info("\n\nStarting Test: %s \n%s"%(self._testMethodName,self._testMethodDoc))
        else:
            self.log.info("\n\nStarting Test: %s"%(self._testMethodName))
        super(CbasUpgrade, self).setUp()
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
        self.travel_sample_docs_count = 31591
        self.beer_sample_docs_count = 7303
        invalid_ip = '10.111.151.109'
        self.add_default_cbas_node = self.input.param('add_default_cbas_node', True)
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
        self.index_name = self.input.param('index_name', "NoName")
        self.index_fields = self.input.param('index_fields', None)
        if self.index_fields:
            self.index_fields = self.index_fields.split("-")
        self.otpNodes = []
        self.cbas_path = server.cbas_path

        self.rest = RestConnection(self.master)
        self.log.info("Setting the min possible memory quota so that adding more nodes to the cluster wouldn't be a problem.")
        self.rest.set_service_memoryQuota(service='memoryQuota', memoryQuota=MIN_KV_QUOTA)
        self.rest.set_service_memoryQuota(service='ftsMemoryQuota', memoryQuota=FTS_QUOTA)
        self.rest.set_service_memoryQuota(service='indexMemoryQuota', memoryQuota=INDEX_QUOTA)

        self.set_cbas_memory_from_available_free_memory = self.input.param('set_cbas_memory_from_available_free_memory', False)
        if self.set_cbas_memory_from_available_free_memory:
            info = self.rest.get_nodes_self()
            self.cbas_memory_quota = int((info.memoryFree // 1024 ** 2) * 0.9)
            self.log.info("Setting %d memory quota for CBAS" % self.cbas_memory_quota)
            self.rest.set_service_memoryQuota(service='cbasMemoryQuota', memoryQuota=self.cbas_memory_quota)
        else:
            self.log.info("Setting %d memory quota for CBAS" % CBAS_QUOTA)
            self.cbas_memory_quota = CBAS_QUOTA
            self.rest.set_service_memoryQuota(service='cbasMemoryQuota', memoryQuota=CBAS_QUOTA)

        self.cbas_util = None
        if self.cbas_node:
            self.cbas_util = cbas_utils(self.master, self.cbas_node)
            self.cleanup_cbas()

        if not self.cbas_node and len(self.cbas_servers)>=1:
            self.cbas_node = self.cbas_servers[0]
            self.cbas_util = cbas_utils(self.master, self.cbas_node)
            if "cbas" in self.master.services:
                self.cleanup_cbas()
            if self.add_default_cbas_node:
                if self.master.ip != self.cbas_node.ip:
                    self.otpNodes.append(cluster_utils(self.master).add_node(self.cbas_node))
                else:
                    self.otpNodes = self.rest.node_statuses()
                ''' This cbas cleanup is actually not needed.
                    When a node is added to the cluster, it is automatically cleaned-up.'''
                self.cleanup_cbas()
                self.cbas_servers.remove(self.cbas_node)

        self.log.info("==============  CBAS_BASE setup was finished for test #{0} {1} ==============".format(self.case_number, self._testMethodName))

        if self.add_default_cbas_node:
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

    def cleanup_cbas(self):
        """
        Drops all connections, dataverse, datasets and buckets from CBAS
        """
        try:
            self.log.info("Disconnect from all connected buckets")
            cmd_get_buckets = "select Name from Metadata.`Bucket`;"
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(cmd_get_buckets)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.disconnect_from_bucket(row['Name'], disconnect_if_connected=True)
                    self.log.info("********* Disconnected all buckets *********")
            else:
                self.log.info("********* No buckets to disconnect *********")

            self.log.info("Drop all datasets")
            cmd_get_datasets = "select DatasetName from Metadata.`Dataset` where DataverseName != \"Metadata\";"
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(cmd_get_datasets)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.drop_dataset(row['DatasetName'])
                    self.log.info("********* Dropped all datasets *********")
            else:
                self.log.info("********* No datasets to drop *********")

            self.log.info("Drop all buckets")
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(cmd_get_buckets)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.drop_cbas_bucket(row['Name'])
                    self.log.info("********* Dropped all buckets *********")
            else:
                self.log.info("********* No buckets to drop *********")

            self.log.info("Drop Dataverse other than Default and Metadata")
            cmd_get_dataverse = 'select DataverseName from Metadata.`Dataverse` where DataverseName != "Metadata" and DataverseName != "Default";'
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(cmd_get_dataverse)
            if (results != None) & (len(results) > 0):
                for row in results:
                    self.cbas_util.drop_dataverse_on_cbas(dataverse_name=row['DataverseName'])
                    self.log.info("********* Dropped all dataverse except Default and Metadata *********")
            else:
                self.log.info("********* No Dataverse to drop *********")
        except Exception as e:
            self.log.info(e.message)

    def verify_index_used(self, statement, index_used=False, index_name=None):
            statement = 'EXPLAIN %s' % statement
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(statement)
            self.assertEquals(status, "success")
            if status == 'success':
                self.assertEquals(errors, None)
                if index_used:
                    self.assertTrue("index-search" in str(results))
                    self.assertFalse("data-scan" in str(results))
                    self.log.info("INDEX-SEARCH is found in EXPLAIN hence indexed data will be scanned to serve %s" % statement)
                    if index_name:
                        self.assertTrue(index_name in str(results))
                else:
                    self.assertTrue("data-scan" in str(results))
                    self.assertFalse("index-search" in str(results))
                    self.log.info("DATA-SCAN is found in EXPLAIN hence index is not used to serve %s" % statement)

    def pre_upgrade_analytics_setup(self):

        self.log.info("Create default bucket")
        self.create_default_bucket()

        self.log.info("Load documents in the default bucket")
        self.perform_doc_ops_in_all_cb_buckets(self.num_items, "create", 0, self.num_items)

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info("Create dataset")
        cbas_dataset_name = self.cbas_dataset_name + "0"
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, cbas_dataset_name)

        self.log.info("Create secondary index on default bucket")
        self.index_field = self.input.param('index_field', 'profession:string')
        create_idx_statement = "create index {0} if not exists on {1}({2})".format(self.index_name, cbas_dataset_name, self.index_field)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == "success", "Create Index query failed")

        self.log.info("Verify secondary index is created")
        self.assertTrue(self.cbas_util.verify_index_created(self.index_name, [self.index_field], cbas_dataset_name)[0])

        self.log.info("Connect to Local link")
        self.cbas_util.connect_link()

        self.log.info("Validate count on CBAS")
        count_n1ql = self.rest.query_tool('select count(*) from %s' % (self.cb_bucket_name))['results'][0]['$1']
        self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(cbas_dataset_name, count_n1ql), msg="Count mismatch on CBAS and KV")

        self.log.info("Verify secondary index is used in queries")
        statement = 'select value v from ' + cbas_dataset_name + ' v where v.profession = "doctor"'
        self.verify_index_used(statement, True, self.index_name)

        self.log.info("Fetch and validate replica information")
        replicas = self.cbas_util.get_replicas_info(RemoteMachineShellConnection(self.master))
        self.replicas_before_rebalance = len(replicas)
        self.log.info("Replica's before upgrade {0}".format(self.replicas_before_rebalance))

        for replica in replicas:
            self.assertEqual(replica['status'], "IN_SYNC", "Replica state is incorrect: %s" % replica['status'])

    def post_upgrade_analytics_validation(self):

        self.log.info("Verify count before adding more documents")
        datasets = self.cbas_util.execute_statement_on_cbas_util('SELECT count(*) FROM Metadata.`Dataset` ds WHERE ds.DataverseName = "Default"')[3][0]["$1"]
        for x in range(datasets):
            self.log.info("Validate count on CBAS")
            count_n1ql = self.rest.query_tool('select count(*) from %s' % self.cb_bucket_name)['results'][0]['$1']
            self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name + str(x), count_n1ql), msg="Count mismatch on CBAS and KV")

        self.log.info("Load documents in the default bucket")
        self.num_items = self.num_items * 2
        self.perform_doc_ops_in_all_cb_buckets(self.num_items, "create", self.num_items / 2, self.num_items)

        self.log.info("Disconnect Local link")
        self.assertTrue(self.cbas_util.disconnect_link(), "Failed to disconnect link post upgrade")

        self.log.info("Create dataset post upgrade")
        cbas_dataset_name = self.cbas_dataset_name + str(datasets)
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, cbas_dataset_name)

        self.log.info("Create secondary index on default bucket")
        self.index_field = self.input.param('index_field', 'profession:string')
        create_idx_statement = "create index {0} if not exists on {1}({2})".format(self.index_name, cbas_dataset_name, self.index_field)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == "success", "Create Index query failed")

        self.log.info("Verify secondary index is created")
        self.assertTrue(self.cbas_util.verify_index_created(self.index_name, [self.index_field], cbas_dataset_name)[0])

        self.log.info("Connect to Local link")
        self.assertTrue(self.cbas_util.connect_link(), "Failed to disconnect link post upgrade")

        for x in range(datasets + 1):
            self.log.info("Validate count on CBAS")
            count_n1ql = self.rest.query_tool('select count(*) from %s' % (self.cb_bucket_name))['results'][0]['$1']
            self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name + str(x), count_n1ql), msg="Count mismatch on CBAS and KV")

            self.log.info("Verify secondary index is used in queries")
            statement = 'select value v from ' + self.cbas_dataset_name + str(x) + ' v where v.profession = "doctor"'
            self.verify_index_used(statement, True, self.index_name)

        self.log.info("Fetch and validate replica information post upgrade")
        replicas = self.cbas_util.get_replicas_info(RemoteMachineShellConnection(self.master))
        self.replicas_after_rebalance = len(replicas)

        self.log.info("Validate replica count after upgrade")
        self.assertEqual(self.replicas_before_rebalance, self.replicas_after_rebalance, msg="Replica's before {0} Replica's after {1}. Replica's mismatch".format(
                             self.replicas_before_rebalance, self.replicas_after_rebalance))

        for replica in replicas:
            self.assertEqual(replica['status'], "IN_SYNC", "Replica state is incorrect: %s" % replica['status'])

    def update_jre_on_node(self, node):

        if self.input.param('use_custom_jdk', False):
            shell = RemoteMachineShellConnection(node)
            info = shell.extract_remote_info().type.lower()
            shell.disconnect()

            self.log.info("Setting custom JRE path on node {0}".format(node.ip))
            jdk_version = self.input.param('jdk_version', 'jre8')
            if info == 'linux':
                path = testconstants.LINUX_JDK_PATH + jdk_version
            elif info == 'windows':
                path = testconstants.WIN_JDK_PATH + jdk_version
            else:
                self.fail(msg="Unsupported OS type for setting custom JRE path")
            rest = RestConnection(node)
            self.assertTrue(rest.set_jre_path(jre_path=path), msg="Failed to set custom JRE path {0} on node {1}".format(path, node.ip))

    def async_load_data_till_upgrade_completes(self):
        self.log.info("Started doc operations on KV, will continue until upgrade is in progress")
        client = SDKClient(hosts=[self.master.ip], bucket=self.cb_bucket_name, password=self.master.rest_password)
        i = 0
        while not self._STOP_INGESTION:
            client.insert_document("key-id" + str(i), '{"name":"James_' + str(i) + '", "profession":"Pilot"}')
            i += 1

    def recover_from_rebalance_failure(self, remove_nodes):
        self.cbas_util.wait_for_cbas_to_recover()
        self.cbas_util.disconnect_link()
        # TODO Replace the dataset name with query to fetch dataset from UI logs
        cbas_dataset_name = self.cbas_dataset_name + "0"
        self.cbas_util.drop_dataset(cbas_dataset_name)
        self.remove_node(remove_nodes, wait_for_rebalance=True)

        self.log.info("Re-create dataset")
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, cbas_dataset_name)

        self.log.info("Re-create secondary index on default bucket")
        self.index_field = self.input.param('index_field', 'profession:string')
        create_idx_statement = "create index {0} if not exists on {1}({2})".format(self.index_name, cbas_dataset_name, self.index_field)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == "success", "Create Index query failed")

        self.cbas_util.connect_link()
        self.cbas_util.wait_for_cbas_to_recover()

    def test_offline_upgrade(self):

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster")
        self.add_all_nodes_then_rebalance(self.servers[1:len(self.servers)], wait_for_completion=True)

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Disable auto failover on cluster")
        status = self.rest.update_autofailover_settings(False, 60)
        self.assertTrue(status, 'failed to disable auto fail over!')

        self.log.info("Shutdown node before offline upgrade")
        for node in self.servers:
            RemoteMachineShellConnection(node).stop_couchbase()

        self.log.info("Starting offline upgrade")
        for upgrade_version in self.upgrade_versions:
            for node in reversed(self.servers):
                self.log.info("Upgrade to {0} version of Couchbase on node {1}".format(upgrade_version, node.ip))
                self._upgrade(upgrade_version=upgrade_version, server=node)
                self.sleep(self.sleep_time, "Installation of new version is done".format(upgrade_version))
                self.update_jre_on_node(node)

        self.log.info("Rebalance cluster after offline upgrade (See MB-33756)")
        self.rebalance(wait_for_completion=True)

        self.log.info("Wait for analytics service to be ready")
        analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
        self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

        self.log.info("Post upgrade analytics validation")
        self.post_upgrade_analytics_validation()

    def test_online_upgrade_swap_rebalance(self):

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster except last cbas node") # Last node will be used for swapping
        cbas_nodes = []
        otp_nodes = []
        node_services = self.input.param('node_services', "cbas").split("-")
        extra_node = self.servers[len(self.servers) - 1]

        for server in self.servers[1:len(self.servers) - 1]:  # Leave out the first node that is KV master node and the last node we will use to swap with active nodes
            otp_nodes.append(self.add_node(server, services=node_services, rebalance=True))
            cbas_nodes.append(server)

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Starting online swap rebalance upgrade")
        for upgrade_version in self.upgrade_versions:
            for idx in range(len(cbas_nodes) - 1, -1, -1):
                self.log.info("Install {0} version of Couchbase on node {1}".format(upgrade_version, extra_node.ip))
                self._install(servers=[extra_node], version=upgrade_version)
                self.sleep(self.sleep_time, "Installation of new version {0} is done".format(upgrade_version))
                self.update_jre_on_node(extra_node)

                self.log.info("Swap rebalance node")
                self.add_node(node=extra_node, services=node_services, rebalance=False)
                self.remove_node(otpnode=[otp_nodes[idx]], wait_for_rebalance=True)

                self.log.info("Re-initialise cbas utils")
                self.cbas_util.closeConn()
                self.cbas_util = cbas_utils(self.master, extra_node)
                self.cbas_util.createConn(self.cb_bucket_name)

                self.log.info("Wait for analytics service to be ready")
                analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
                self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

                self.log.info("Select the new extra rebalance node - rebalanced out node")
                extra_node = cbas_nodes[idx]

                self.log.info("Post upgrade analytics validation")
                self.dataset_count = len(cbas_nodes) - idx
                self.post_upgrade_analytics_validation()

        self.log.info("Upgrade KV node")
        for upgrade_version in self.upgrade_versions:
            self.log.info("Install {0} version of Couchbase on node {1}".format(upgrade_version, extra_node.ip))
            self._install(servers=[extra_node], version=upgrade_version)
            self.sleep(self.sleep_time, "Installation of new version {0} is done".format(upgrade_version))

            self.log.info("Swap rebalance master KV node and wait for rebalance to complete")
            self.cluster.async_rebalance(self.servers, [extra_node], [self.master], services=["kv,n1ql"], check_vbucket_shuffling=False)
            self.sleep(message="Wait for rebalance to start")
            rest = RestConnection(self.servers[len(self.servers) - 1])
            reached = RestHelper(rest).rebalance_reached(wait_step=120)
            self.assertTrue(reached, "rebalance failed, stuck or did not complete")
        
        self.log.info("Rebalancing the cluster")
        self.master = extra_node
        self.assertTrue(cluster_utils(self.master).rebalance(), "Rebalancing cluster failed")

        self.log.info("Verify document count")
        rest = RestConnection(extra_node)
        for x in range(self.dataset_count):
            self.log.info("Validate count on CBAS")
            count_n1ql = rest.query_tool('select count(*) from %s' % self.cb_bucket_name)['results'][0]['$1']
            self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name + str(x), count_n1ql), msg="Count mismatch on CBAS and KV")

    def test_online_upgrade_swap_rebalance_multiple_nodes(self):

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add cbas nodes to cluster and then swap them with equal upgraded nodes")
        swap_node_count = self.input.param('swap_node_count', 2)
        cbas_active_nodes = self.servers[1:len(self.servers) - swap_node_count]
        cbas_upgrade_nodes = self.servers[len(self.servers) - swap_node_count:]
        node_services = self.input.param('node_services', "cbas").split("-")
        otp_nodes = []

        # Leave out the first node that is KV master node. We will add first 2 CBAS node and then swap them with upgraded 2 nodes
        for server in cbas_active_nodes:
            otp_nodes.append(self.add_node(server, services=node_services, rebalance=True))

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Starting online swap rebalance upgrade multiple nodes")
        for upgrade_version in self.upgrade_versions:
            self.log.info("Install {0} version on Couchbase on nodes {1}".format(upgrade_version, [node.ip for node in cbas_upgrade_nodes]))
            self._install(servers=cbas_upgrade_nodes, version=upgrade_version)
            self.sleep(self.sleep_time, "Installation of new version {0} is done on nodes {1}".format(upgrade_version, [node.ip for node in cbas_upgrade_nodes]))

            for node in cbas_upgrade_nodes:
                self.update_jre_on_node(node)
                self.add_node(node=node, services=node_services, rebalance=False)

            self.log.info("Swap rebalance multiple nodes")
            self.remove_node(otp_nodes, wait_for_rebalance=True)

            self.log.info("Re-initialise cbas utils")
            self.cbas_util.closeConn()
            self.cbas_util = cbas_utils(self.master, cbas_upgrade_nodes[0])
            self.cbas_util.createConn(self.cb_bucket_name)

            self.log.info("Wait for analytics service to be ready")
            analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
            self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

            self.log.info("Post upgrade analytics validation")
            self.post_upgrade_analytics_validation()

    def test_online_upgrade_swap_rebalance_busy_system(self):

        self.log.info("Declare variable to control KV document load")
        self._STOP_INGESTION = False

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster except last cbas node")
        cbas_nodes = []
        otp_nodes = []
        node_services = self.input.param('node_services', "cbas").split("-")
        extra_node = self.servers[len(self.servers) - 1]
        util_node = extra_node
        for server in self.servers[1:len(self.servers) - 1]:
            otp_nodes.append(self.add_node(server, services=node_services, rebalance=True))
            cbas_nodes.append(server)

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Async load data in KV until upgrade is complete")
        async_load_data = Thread(target=self.async_load_data_till_upgrade_completes, args=())
        async_load_data.start()

        self.log.info("Run concurrent queries to simulate busy system")
        statement = "select sleep(count(*), 5000) from {0} where mutated=0;".format(self.cbas_dataset_name + "0")
        self.cbas_util._run_concurrent_queries(statement, "async", 20, batch_size=10)

        self.log.info("Starting online swap rebalance upgrade")
        for upgrade_version in self.upgrade_versions:
            for idx in range(len(cbas_nodes) - 1, -1, -1):
                self.log.info("Install {0} version of Couchbase on node {1}".format(upgrade_version, extra_node.ip))
                self._install(servers=[extra_node], version=upgrade_version)
                self.sleep(self.sleep_time, "Installation of new version {0} is done".format(upgrade_version))
                self.update_jre_on_node(extra_node)

                self.log.info("Swap rebalance node")
                self.add_node(node=extra_node, services=node_services, rebalance=False)
                self.remove_node(otpnode=[otp_nodes[idx]], wait_for_rebalance=True)

                self.log.info("Select the new extra rebalance node - rebalanced out node")
                extra_node = cbas_nodes[idx]

        self.log.info("Stop ingestion on KV")
        self._STOP_INGESTION = True

        self.log.info("Re-initialise cbas utils")
        self.cbas_util.closeConn()
        self.cbas_util = cbas_utils(self.master, util_node)
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info("Wait for analytics service to be ready")
        analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
        self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

        self.log.info("Post upgrade analytics validation")
        self.post_upgrade_analytics_validation()

    def test_online_upgrade_swap_rebalance_multiple_nodes_busy_system(self):

        self.log.info("Declare variable to control KV document load")
        self._STOP_INGESTION = False

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        # Leave out the first node that is KV master node. We will add first 2 CBAS node and then swap them with upgraded 2 nodes
        self.log.info("Add cbas nodes to cluster and then swap them with equal upgraded nodes")
        swap_node_count = self.input.param('swap_node_count', 2)
        cbas_active_nodes = self.servers[1:len(self.servers) - swap_node_count]
        cbas_upgrade_nodes = self.servers[len(self.servers) - swap_node_count:]
        node_services = self.input.param('node_services', "cbas").split("-")
        otp_nodes = []
        for server in cbas_active_nodes:
            otp_nodes.append(self.add_node(server, services=node_services, rebalance=True))

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Async load data in KV until upgrade is complete")
        async_load_data = Thread(target=self.async_load_data_till_upgrade_completes, args=())
        async_load_data.start()

        self.log.info("Run concurrent queries to simulate busy system")
        statement = "select sleep(count(*), 5000) from {0} where mutated=0;".format(self.cbas_dataset_name + "0")
        self.cbas_util._run_concurrent_queries(statement, "async", 20, batch_size=10)

        self.log.info("Starting online swap rebalance upgrade multiple nodes")
        for upgrade_version in self.upgrade_versions:
            self.log.info("Install {0} version on Couchbase on nodes {1}".format(upgrade_version, [node.ip for node in cbas_upgrade_nodes]))
            self._install(servers=cbas_upgrade_nodes, version=upgrade_version)
            self.sleep(self.sleep_time, "Installation of new version {0} is done on nodes {1}".format(upgrade_version, [node.ip for node in cbas_upgrade_nodes]))

            for node in cbas_upgrade_nodes:
                self.update_jre_on_node(node)
                self.add_node(node=node, services=node_services, rebalance=False)

            self.log.info("Swap rebalance multiple nodes")
            self.remove_node(otp_nodes, wait_for_rebalance=True)

        self.log.info("Stop ingestion on KV")
        self._STOP_INGESTION = True

        self.log.info("Re-initialise cbas utils")
        self.cbas_util.closeConn()
        self.cbas_util = cbas_utils(self.master, cbas_upgrade_nodes[0])
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info("Wait for analytics service to be ready")
        analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
        self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

        self.log.info("Post upgrade analytics validation")
        self.post_upgrade_analytics_validation()

    def test_online_upgrade_remove_and_rebalance(self):

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster")
        cbas_nodes = []
        node_services = self.input.param('node_services', "cbas").split("-")
        for server in self.servers[1:len(self.servers)]:
            self.add_node(server, services=node_services, rebalance=True)
            cbas_nodes.append(server)

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Start online remove and rebalance upgrade")
        for upgrade_version in self.upgrade_versions:
            for idx, node in enumerate(reversed(cbas_nodes)):

                self.log.info("Rebalance out node {0}".format(node.ip))
                self.cluster.rebalance(servers=self.servers, to_add=[], to_remove=[node])

                self.log.info("Install {0} version of Couchbase on node {1}".format(upgrade_version, node.ip))
                self._install(servers=[node], version=upgrade_version)
                self.sleep(self.sleep_time, "Installation of {0} version of Couchbase on node {1} completed".format(upgrade_version, node.ip))
                self.update_jre_on_node(node)

                self.log.info("Rebalance in node {0}".format(node.ip))
                self.add_node(node, services=node_services, rebalance=True)

                self.log.info("Re-initialise cbas utils")
                self.cbas_util.closeConn()
                self.cbas_util = cbas_utils(self.master, node)
                self.cbas_util.createConn(self.cb_bucket_name)

                self.log.info("Wait for analytics service to be ready")
                analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
                self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

                self.log.info("Post upgrade analytics validation")
                self.post_upgrade_analytics_validation()

    def test_online_upgrade_remove_and_rebalance_multiple_nodes(self):

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster and then remove specified nodes 'rebalance_out_node_count' upgrade and add back")
        rebalance_out_node_count = self.input.param('rebalance_out_node_count', 2)
        rebalance_node = 0
        cbas_active_nodes = self.servers[1:len(self.servers)]
        node_services = self.input.param('node_services', "cbas").split("-")
        otp_nodes = []

        for server in cbas_active_nodes:
            otp_nodes.append(self.add_node(server, services=node_services, rebalance=True))

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Starting online rebalance out upgrade multiple nodes")
        for upgrade_version in self.upgrade_versions:
            for idx in range(rebalance_node, len(cbas_active_nodes), rebalance_out_node_count): # Will handle even number of CBAS nodes, if odd number of nodes add logic to handle the last remaining node

                self.log.info("Rebalance out node {0}".format([node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                try:
                    self.remove_node(otp_nodes[idx:idx + rebalance_out_node_count], wait_for_rebalance=True)
                except Exception as e:
                    self.log.info("Rebalance failed. Known issue - https://issues.couchbase.com/browse/MB-32435")
                    self.recover_from_rebalance_failure(otp_nodes[idx:idx + rebalance_out_node_count])

                self.log.info("Install {0} version on Couchbase on nodes {1}".format(upgrade_version, [node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                self._install(servers=cbas_active_nodes[idx:idx + rebalance_out_node_count], version=upgrade_version)
                self.sleep(self.sleep_time, "Installation of new version {0} is done on nodes {1}".format(upgrade_version, [node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                rebalance_node += rebalance_out_node_count

                self.log.info("Rebalance in node {0}".format([node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]:
                    self.update_jre_on_node(node)
                self.add_all_nodes_then_rebalance(cbas_active_nodes[idx:idx + rebalance_out_node_count], wait_for_completion=True)

                self.log.info("Re-initialise cbas utils")
                self.cbas_util.closeConn()
                self.cbas_util = cbas_utils(self.master, cbas_active_nodes[idx:idx + rebalance_out_node_count][0])
                self.cbas_util.createConn(self.cb_bucket_name)

                self.log.info("Wait for analytics service to be ready")
                analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
                self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

                self.log.info("Post upgrade analytics validation")
                self.post_upgrade_analytics_validation()

    def test_online_upgrade_remove_and_rebalance_busy_system(self):

        self.log.info("Declare variable to control KV document load")
        self._STOP_INGESTION = False

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster")
        cbas_nodes = []
        node_services = self.input.param('node_services', "cbas").split("-")
        for server in self.servers[1:len(self.servers)]:
            self.add_node(server, services=node_services, rebalance=True)
            cbas_nodes.append(server)

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Async load data in KV until upgrade is complete")
        async_load_data = Thread(target=self.async_load_data_till_upgrade_completes, args=())
        async_load_data.start()

        self.log.info("Run concurrent queries to simulate busy system")
        statement = "select sleep(count(*), 5000) from {0} where mutated=0;".format(self.cbas_dataset_name + "0")
        self.cbas_util._run_concurrent_queries(statement, "async", 20, batch_size=10)

        self.log.info("Start online remove and rebalance upgrade")
        for upgrade_version in self.upgrade_versions:
            for idx, node in enumerate(reversed(cbas_nodes)):

                self.log.info("Rebalance out node {0}".format(node.ip))
                self.cluster.rebalance(servers=self.servers, to_add=[], to_remove=[node])

                self.log.info("Install {0} version of Couchbase on node {1}".format(upgrade_version, node.ip))
                self._install(servers=[node], version=upgrade_version)
                self.sleep(self.sleep_time, "Installation of {0} version of Couchbase on node {1} completed".format(upgrade_version, node.ip))
                self.update_jre_on_node(node)

                self.log.info("Rebalance in node {0}".format(node.ip))
                self.add_node(node, services=node_services, rebalance=True)

        self.log.info("Stop ingestion on KV")
        self._STOP_INGESTION = True

        self.log.info("Wait for analytics service to be ready")
        analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
        self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

        self.log.info("Post upgrade analytics validation")
        self.post_upgrade_analytics_validation()

    def test_online_upgrade_remove_and_rebalance_multiple_nodes_busy_system(self):

        self.log.info("Declare variable to control KV document load")
        self._STOP_INGESTION = False

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster and then remove specified nodes 'rebalance_out_node_count' upgrade and add back")
        rebalance_out_node_count = self.input.param('rebalance_out_node_count', 2)
        rebalance_node = 0
        cbas_active_nodes = self.servers[1:len(self.servers)]
        node_services = self.input.param('node_services', "cbas").split("-")
        otp_nodes = []
        for server in cbas_active_nodes:
            otp_nodes.append(self.add_node(server, services=node_services, rebalance=True))

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Async load data in KV until upgrade is complete")
        async_load_data = Thread(target=self.async_load_data_till_upgrade_completes, args=())
        async_load_data.start()

        self.log.info("Run concurrent queries to simulate busy system")
        statement = "select sleep(count(*), 5000) from {0} where mutated=0;".format(self.cbas_dataset_name + "0")
        self.cbas_util._run_concurrent_queries(statement, "async", 20, batch_size=10)

        self.log.info("Starting online rebalance out upgrade multiple nodes")
        for upgrade_version in self.upgrade_versions:
            for idx in range(rebalance_node, len(cbas_active_nodes), rebalance_out_node_count): # Will handle even number of CBAS nodes, if odd number of nodes add logic to handle the last remaining node

                self.log.info("Rebalance out node {0}".format([node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                try:
                    self.remove_node(otp_nodes[idx:idx + rebalance_out_node_count], wait_for_rebalance=True)
                except Exception as e:
                    self.log.info("Rebalance failed. Known issue - https://issues.couchbase.com/browse/MB-32435")
                    self.recover_from_rebalance_failure(otp_nodes[idx:idx + rebalance_out_node_count])

                self.log.info("Install {0} version on Couchbase on nodes {1}".format(upgrade_version, [node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                self._install(servers=cbas_active_nodes[idx:idx + rebalance_out_node_count], version=upgrade_version)
                self.sleep(self.sleep_time, "Installation of new version {0} is done on nodes {1}".format(upgrade_version, [node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                rebalance_node += rebalance_out_node_count

                self.log.info("Rebalance in node {0}".format([node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
                for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]:
                    self.update_jre_on_node(node)
                self.add_all_nodes_then_rebalance(cbas_active_nodes[idx:idx + rebalance_out_node_count], wait_for_completion=True)

        self.log.info("Stop ingestion on KV")
        self._STOP_INGESTION = True

        self.log.info("Wait for analytics service to be ready")
        analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
        self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

        self.log.info("Post upgrade analytics validation")
        self.post_upgrade_analytics_validation()

    def test_graceful_failover_upgrade_single_node_idle_system(self):

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster")
        cbas_nodes = []
        node_services = self.input.param('node_services', "kv-cbas-n1ql").split("-")
        for server in self.servers[1:len(self.servers)]:
            self.add_node(server, services=node_services, rebalance=True)
            cbas_nodes.append(server)

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Start online graceful failover upgrade and then full recovery add back")
        for upgrade_version in self.upgrade_versions:
            for idx, node in enumerate(reversed(cbas_nodes)):

                self.log.info("graceful failover node {0}".format(node.ip))
                self.rest.fail_over('ns_1@' + node.ip, graceful=True)
                self.sleep(timeout=120)
                self.rest.set_recovery_type('ns_1@' + node.ip, "full")
                
                self.log.info('Stop couchbase server before upgrade')
                shell = RemoteMachineShellConnection(node)
                shell.stop_couchbase()
                shell.disconnect()

                self.log.info("Upgrade {0} version of Couchbase on node {1}".format(upgrade_version, node.ip))
                self._upgrade(upgrade_version=upgrade_version, server=node)
                self.sleep(self.sleep_time, "Installation of new version is done".format(upgrade_version))
                self.update_jre_on_node(node)
                
                self.log.info('Start couchbase server after upgrade')
                shell = RemoteMachineShellConnection(node)
                shell.start_couchbase()
                shell.disconnect()

                self.log.info("Rebalance node {0}".format(node.ip))
                self.cluster.rebalance(self.servers, [], [])

                self.log.info("Wait for analytics service to be ready")
                analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
                self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

                self.log.info("Post upgrade analytics validation")
                self.post_upgrade_analytics_validation()

    def test_graceful_failover_upgrade_single_node_busy_system(self):

        self.log.info("Declare variable to control KV document load")
        self._STOP_INGESTION = False

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers)

        self.log.info("Add all cbas nodes to cluster")
        cbas_nodes = []
        node_services = self.input.param('node_services', "kv-cbas-n1ql").split("-")
        for server in self.servers[1:len(self.servers)]:
            self.add_node(server, services=node_services, rebalance=True)
            cbas_nodes.append(server)

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Async load data in KV until upgrade is complete")
        async_load_data = Thread(target=self.async_load_data_till_upgrade_completes, args=())
        async_load_data.start()

        self.log.info("Run concurrent queries to simulate busy system")
        statement = "select sleep(count(*), 5000) from {0} where mutated=0;".format(self.cbas_dataset_name + "0")
        self.cbas_util._run_concurrent_queries(statement, "async", 20, batch_size=10)

        self.log.info("Start online graceful failover upgrade and then full recovery add back")
        for upgrade_version in self.upgrade_versions:
            for idx, node in enumerate(reversed(cbas_nodes)):

                self.log.info("graceful failover node {0}".format(node.ip))
                self.rest.fail_over('ns_1@' + node.ip, graceful=True)
                self.sleep(timeout=120)
                self.rest.set_recovery_type('ns_1@' + node.ip, "full")
                
                self.log.info('Stop couchbase server before upgrade')
                shell = RemoteMachineShellConnection(node)
                shell.stop_couchbase()
                shell.disconnect()

                self.log.info("Upgrade {0} version of Couchbase on node {1}".format(upgrade_version, node.ip))
                self._upgrade(upgrade_version=upgrade_version, server=node)
                self.sleep(self.sleep_time, "Installation of new version is done".format(upgrade_version))
                self.update_jre_on_node(node)
                
                self.log.info('Start couchbase server after upgrade')
                shell = RemoteMachineShellConnection(node)
                shell.start_couchbase()
                shell.disconnect()

                self.log.info("Rebalance node {0}".format(node.ip))
                self.cluster.rebalance(self.servers, [], [])
        
        self.log.info("Stop ingestion on KV")
        self._STOP_INGESTION = True

        self.log.info("Wait for analytics service to be ready")
        analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
        self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

        self.log.info("Post upgrade analytics validation")
        self.post_upgrade_analytics_validation()

    def test_remove_and_rebalance_multiple_nodes_non_upgrade(self):

        self.log.info("Install pre-upgrade version of couchbase on all server nodes")
        self._install(self.servers, version=self.upgrade_versions[len(self.upgrade_versions) - 1])

        self.log.info("Add all cbas nodes to cluster and then remove specified nodes 'rebalance_out_node_count' upgrade and add back")
        rebalance_out_node_count = self.input.param('rebalance_out_node_count', 2)
        rebalance_node = 0
        cbas_active_nodes = self.servers[1:len(self.servers)]
        node_services = self.input.param('node_services', "cbas").split("-")
        otp_nodes = []

        for server in cbas_active_nodes:
            otp_nodes.append(self.add_node(server, services=node_services, rebalance=True))

        self.log.info("Load documents, create datasets and verify count before upgrade")
        self.pre_upgrade_analytics_setup()

        self.log.info("Starting online rebalance out upgrade multiple nodes")
        for idx in range(rebalance_node, len(cbas_active_nodes), rebalance_out_node_count): # Will handle even number of CBAS nodes, if odd number of nodes add logic to handle the last remaining node

            self.log.info("Rebalance out node {0}".format([node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
            self.remove_node(otp_nodes[idx:idx + rebalance_out_node_count], wait_for_rebalance=True)
            rebalance_node += rebalance_out_node_count

            self.log.info("Rebalance in node {0}".format([node.ip for node in cbas_active_nodes[idx:idx + rebalance_out_node_count]]))
            self.add_all_nodes_then_rebalance(cbas_active_nodes[idx:idx + rebalance_out_node_count], wait_for_completion=True)

            self.log.info("Re-initialise cbas utils")
            self.cbas_util.closeConn()
            self.cbas_util = cbas_utils(self.master, cbas_active_nodes[idx:idx + rebalance_out_node_count][0])
            self.cbas_util.createConn(self.cb_bucket_name)

            self.log.info("Wait for analytics service to be ready")
            analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
            self.assertTrue(analytics_recovered, msg="Analytics failed to recover")

            self.log.info("Post upgrade analytics validation")
            self.post_upgrade_analytics_validation()
    
    def tearDown(self):
        self._STOP_INGESTION = True
