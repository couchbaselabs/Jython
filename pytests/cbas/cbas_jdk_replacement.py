from random import shuffle

from threading import Thread
from cbas.cbas_base import CBASBaseTest
from sdk_client import SDKClient
from remote.remote_util import RemoteMachineShellConnection
from lib.membase.api.rest_client import RestConnection
from testconstants import JAVA_RUN_TIMES, WIN_JDK_PATH, LINUX_JDK_PATH
from cbas_utils import cbas_utils


class CBASJdkReplacement(CBASBaseTest):

    def setUp(self):
        super(CBASJdkReplacement, self).setUp()

        self.log.info("Add remaining analytics node to cluster")
        self.analytics_servers = []
        self.analytics_servers.append(self.cbas_node)

        self.add_node(self.cbas_servers[0], rebalance=True)
        self.analytics_servers.append(self.cbas_servers[0])

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
        self.replicas_before_jdk_replacement = len(replicas)
        self.log.info("Replica's before upgrade {0}".format(self.replicas_before_jdk_replacement))

        for replica in replicas:
            self.assertEqual(replica['status'], "IN_SYNC", "Replica state is incorrect: %s" % replica['status'])

        self.log.info("Fetch number of partitions before replacing JDK")
        response = self.cbas_util.fetch_analytics_cluster_response(RemoteMachineShellConnection(self.master))
        self.partitions_before_jdk_replacement = 0
        if 'partitions' in response:
            self.partitions_before_jdk_replacement = len(response['partitions'])
        self.log.info("Number of data partitions on cluster %d" % self.partitions_before_jdk_replacement)

    def post_jre_replacement_validation(self, count=1):

        self.log.info("Disconnect Local link")
        self.assertTrue(self.cbas_util.disconnect_link(), "Failed to disconnect link post upgrade")

        self.log.info("Create dataset")
        cbas_dataset_name = self.cbas_dataset_name + str(count)
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

        for x in range(count + 1):
            self.log.info("Verify secondary index is used in queries")
            statement = 'select value v from ' + self.cbas_dataset_name + str(x) + ' v where v.profession = "doctor"'
            self.verify_index_used(statement, True, self.index_name)

        self.log.info("Fetch and validate replica information post JDK replacement")
        replicas = self.cbas_util.get_replicas_info(RemoteMachineShellConnection(self.master))
        self.replicas_after_jdk_replacement = len(replicas)

        self.log.info("Validate replica count after JDK replacement")
        self.assertEqual(self.replicas_before_jdk_replacement, self.replicas_after_jdk_replacement, msg="Replica's before {0} Replica's after {1}. Replica's mismatch".format(self.replicas_before_jdk_replacement, self.replicas_after_jdk_replacement))

        for replica in replicas:
            self.assertEqual(replica['status'], "IN_SYNC", "Replica state is incorrect: %s" % replica['status'])

        self.log.info("Fetch number of partitions after upgrade and compare")
        response = self.cbas_util.fetch_analytics_cluster_response(RemoteMachineShellConnection(self.master))
        self.partitions_after_jdk_replace = 0
        if 'partitions' in response:
            self.partitions_after_jdk_replace = len(response['partitions'])
        self.log.info("Number of data partitions on cluster %d" % self.partitions_after_jdk_replace)
        self.assertEqual(self.partitions_before_jdk_replacement, self.partitions_after_jdk_replace, msg="partitions before {0}, after {1}. Partition's mismatch".format(self.partitions_before_jdk_replacement, self.partitions_after_jdk_replace))

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

    def update_jre_on_node(self, node, jdk_version):

        self.log.info("Fetch machine information")
        shell = RemoteMachineShellConnection(node)
        info = shell.extract_remote_info().type.lower()
        shell.disconnect()

        self.log.info("Setting custom JRE path on node {0}".format(node.ip))
        if info == 'linux':
            # Todo: Replace the hard-coded jdk11 path and change in the testconstants file instead
            if jdk_version == "openjdk11":
                shell = RemoteMachineShellConnection(node)
                output, error = shell.execute_command("sudo yum install -y java-11-openjdk")
                shell.log_command_output(output, error)
                output_1, error_1 = shell.execute_command("ls /usr/lib/jvm")
                shell.log_command_output(output_1, error_1)
                if output_1:
                    for item in output_1:
                        if "java-11-openjdk" in item:
                            path = item.strip("\n")
                path = "/usr/lib/jvm/{0}".format(path)
            else:
                path = LINUX_JDK_PATH + jdk_version
        elif info == 'windows':
            path = WIN_JDK_PATH + jdk_version
        else:
            self.fail(msg="Unsupported OS type for setting custom JRE path")
        rest = RestConnection(node)
        self.assertTrue(rest.set_jre_path(jre_path=path), msg="Failed to set custom JRE path {0} on node {1}".format(path, node.ip))

    """
    cbas.cbas_jdk_replacement.CBASJdkReplacement.test_cbas_jdk_replacement,default_bucket=True,cb_bucket_name=default,cbas_dataset_name=ds_,items=100,index_field=profession:string,index_name=idx_,use_cli=True
    """
    def test_cbas_jdk_replacement(self):
        
        self.log.info("Declare variable to control KV document load")
        _STOP_INGESTION = False

        self.log.info("Run pre JDK replacement setup")
        self.pre_upgrade_analytics_setup()
        
        def async_load_data():
            self.log.info("Performing doc operations on KV until upgrade is in progress")
            client = SDKClient(hosts=[self.master.ip], bucket=self.cb_bucket_name, password=self.master.rest_password)
            i = 0
            while not _STOP_INGESTION:
                client.insert_document("key-id" + str(i), '{"name":"James_' + str(i) + '", "profession":"Pilot"}')
                i += 1
        
        self.log.info("Async load data in KV until upgrade is complete")
        async_load_data = Thread(target=async_load_data, args=())
        async_load_data.start()
        
        self.log.info("Run concurrent CBAS queries")
        statement = "select sleep(count(*), 50000) from {0} where mutated=0;".format(self.cbas_dataset_name + "0")
        self.cbas_util._run_concurrent_queries(statement, "async", 1000, batch_size=100)
        
        self.log.info("Replace JRE on each node")
        available_jdks = list(JAVA_RUN_TIMES.keys())
        available_jdks.remove(None)
        shuffle(available_jdks)
        times = 1
        try:
            for jdk in available_jdks:
                if jdk == "openjdk11":
                    for node in self.analytics_servers:
                        if not self.input.param('use_cli', False):
                            self.log.info("Replacing JRE using REST")
                            self.update_jre_on_node(node, jdk)
                        else:
                            self.log.info("Replacing JRE using CLI")
                            shell = RemoteMachineShellConnection(node)
                            shell.set_jre_path_cli(jdk)
                            shell.disconnect()
                        self.sleep(message="Wait for node to restart")
        
                        self.log.info("Wait for analytics service to be up and running")
                        analytics_recovered = self.cbas_util.wait_for_cbas_to_recover()
                        self.assertTrue(analytics_recovered, msg="Analytics failed to recover")
        
                        self.log.info("Validate JRE is replaced for node {0}".format(node.ip))
                        util = cbas_utils(self.master, node)
                        diag_res = util.get_analytics_diagnostics(self.cbas_node)
                        java_home = diag_res['runtime']['systemProperties']['java.home']
                        java_runtime_name = diag_res['runtime']['systemProperties']['java.runtime.name']
                        java_runtime_version = diag_res['runtime']['systemProperties']['java.runtime.version']
                        jre_info = JAVA_RUN_TIMES[jdk]
                        self.assertTrue(jre_info['java_home'] in java_home, msg='Incorrect java home value')
                        self.assertEqual(java_runtime_name, jre_info['java_runtime_name'], msg='Incorrect java runtime name')
                        self.assertTrue(java_runtime_version.startswith(jre_info['java_runtime_version']), msg='Incorrect java runtime version')
                        util.closeConn()
        
                        self.log.info("Validate post jre replacement for node {0}".format(node.ip))
                        self.post_jre_replacement_validation(count=times)
                        times += 1
            
            self.log.info("Stop ingestion on KV")
            _STOP_INGESTION = True
            self.sleep(timeout=300, message="Wait for data loading to stop")
    
            self.log.info("Verify count post JDK replacements")
            for x in range(times):
                self.log.info("Validate count on CBAS")
                count_n1ql = self.rest.query_tool('select count(*) from %s' % self.cb_bucket_name)['results'][0]['$1']
                self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name + str(x), count_n1ql, num_tries=30), msg="Count mismatch on CBAS and KV")
        except Exception as e:
            _STOP_INGESTION = True
            self.assertTrue(False, str(e))