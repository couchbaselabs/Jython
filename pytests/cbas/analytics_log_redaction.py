from cbas.cbas_base import CBASBaseTest
from log_redaction_base import LogRedactionBase
from security_utils.audit_ready_functions import audit
from remote.remote_util import RemoteMachineShellConnection


class LogRedactionTests(CBASBaseTest, LogRedactionBase):

    def setUp(self):
        super(LogRedactionTests, self).setUp()
        self.analytics_log_files = ['analytics_debug.log', 'analytics_info.log', 'analytics_access.log', 'analytics_dcpdebug.log', 'analytics_error.log', 'analytics_shutdown.log',
                                    'analytics_warn.log']
        self.user_data_search_keys = ['Administrator', '@cbas-cbauth', '@cbas', 'id like \\"21st_amendment_brewery_cafe%\\"', 'select name from ds limit 1', '21st_amendment_brewery_cafe',
                                      'use dv1', 'SELECT name FROM ds where state=', 'Texas']
        self.system_metadata_search_keys = [self.cb_bucket_name, self.cbas_node.ip, self.master.ip, 'port:9110', 'port:8095', self.index_name]
        
        self.shell = RemoteMachineShellConnection(self.cbas_node)
        self.cbas_url = "http://{0}:{1}/analytics/service".format(self.cbas_node.ip, 8095)
        
        self.log.info('Enable partial redaction')
        self.set_redaction_level()

        self.log.info('Update log level to All for all loggers')
        self.update_log_level()

    def update_log_level(self):
        default_logger_config_dict = {'org.apache.asterix': 'ALL',
                                      'com.couchbase.client.dcp.conductor.DcpChannel': 'ALL',
                                      'com.couchbase.client.core.node': 'ALL',
                                      'com.couchbase.analytics': 'ALL',
                                      'org.apache.hyracks': 'ALL',
                                      'org.apache.hyracks.http.server.CLFLogger': 'ALL'}
        _, node_id, _ = self.cbas_util.retrieve_nodes_config()
        default_logger_config_dict['org.apache.hyracks.util.trace.Tracer.Traces.' + node_id] = 'ALL'

        self.log.info('Set logging level to ALL')
        status, content, response = self.cbas_util.set_log_level_on_cbas(default_logger_config_dict)
        self.assertTrue(status, msg='Response status incorrect for SET request')

    def generate_user_data(self):
        self.log.info('Load beer-sample bucket')
        self.load_sample_buckets(servers=[self.master], bucketName=self.cb_bucket_name, total_items=self.beer_sample_docs_count)
        self.cbas_util.createConn(self.cbas_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)
        
        self.log.info('Create secondary index')
        self.index_field = self.input.param('index_field', 'name:string')
        create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(self.index_name, self.cbas_dataset_name, self.index_field)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.beer_sample_docs_count)

        self.log.info('Execute a parameterized query')
        self.cbas_parameterized_query = 'SELECT name FROM ds where state=$1'
        self.param = [{"args": ["Texas"]}]
        status, _, errors, cbas_result, _ = self.cbas_util.execute_parameter_statement_on_cbas_util(self.cbas_parameterized_query, parameters=self.param)

        self.log.info('Execute query with incorrect user credentials')
        self.cbas_correct_query = 'select name from %s limit 1' % self.cbas_dataset_name
        output, _ = self.shell.execute_command('curl -X POST {0} -u {1}:{2} -d "statement=select * from ds limit 1"'.format(self.cbas_url, "Administrator", "pass"))

        self.log.info('Execute cbas query that is incorrect')
        self.cbas_incorrect_query = 'select meta().* from ds where meta().id like "21st_amendment_brewery_cafe%"'
        self.cbas_util.execute_statement_on_cbas_util(self.cbas_incorrect_query)

        self.log.info('Create custom dataverse')
        self.dataverse_name = 'dv1'
        self.cbas_util.create_dataverse_on_cbas(dataverse_name='dv1')

        self.log.info('Create dataset on dataverse')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name, dataverse=self.dataverse_name)

    def generate_system_and_metadata(self):
        self.log.info('Add a new analytics node and rebalance')
        self.add_node(self.cbas_servers[0], services=["cbas"], rebalance=True)
        
        self.log.info('Add some user data to backup')
        self.generate_user_data()
        
        self.log.info('Backup analytics metadata for beer-sample')
        response = self.cbas_util.backup_cbas_metadata(bucket_name=self.cb_bucket_name)
        self.assertEquals(response['status'], 'success', msg='Failed to backup analytics metadata')
        
        self.log.info('Restore Analytics metadata for beer-sample using API')
        response = self.cbas_util.restore_cbas_metadata(response, bucket_name=self.cb_bucket_name)
        self.assertEquals(response['status'], 'success', msg='Failed to restore analytics metadata')
        
        self.log.info('Access analytics cluster information')
        self.cbas_util.fetch_analytics_cluster_response(self.shell)
        
        self.log.info('Access analytics cluster configs information')
        self.cbas_util.fetch_service_parameter_configuration_on_cbas()
        
        self.log.info('Access analytics bucket information')
        self.cbas_util.fetch_bucket_state_on_cbas()
        
        self.log.info('Access analytics node diagnostics information')
        self.cbas_util.get_analytics_diagnostics(self.cbas_node)
        
        self.log.info('Fetch analytics stats')
        self.cbas_util.fetch_cbas_stats()

    def generate_audit_events(self):
        update_config_map = {'jobHistorySize': 11}
        status, _, _ = self.cbas_util.update_service_parameter_configuration_on_cbas(update_config_map)
        self.assertTrue(status, msg='Failed to update config')

    def enable_audit(self):
        audit_obj = audit(host=self.master)
        current_state = audit_obj.getAuditStatus()
        if current_state:
            audit_obj.setAuditEnable('false')
        audit_obj.setAuditEnable('true')

    def start_log_collection(self):
        self.start_logs_collection()
        result = self.monitor_logs_collection()
        logs_path = result['perNode']['ns_1@' + str(self.cbas_node.ip)]['path']
        redact_file_name = logs_path.split('/')[-1]
        non_redact_file_name = logs_path.split('/')[-1].replace('-redacted', '')
        remote_path = logs_path[0:logs_path.rfind('/') + 1]
        return non_redact_file_name, redact_file_name, remote_path

    def verify_audit_logs_are_not_redacted(self):
        self.log.info('Enable audit')
        self.enable_audit()

        self.log.info('Generate audit events')
        self.generate_audit_events()

        self.log.info('Verify audit log file is not redacted')
        output, _ = self.check_audit_logs_are_not_redacted(self.cbas_node)
        if len(output) != 0:
            self.fail(msg='Audit logs must not be redacted')

    def verify_user_data_is_redacted(self):
        self.log.info('Generate user data')
        self.generate_user_data()

        self.log.info('Collect logs')
        non_redact_file_name, redact_file_name, remote_path = self.start_log_collection()
        
        self.log.info('Verify redacted log file exist')
        self.verify_log_files_exist(server=self.cbas_node, remotepath=remote_path, redactFileName=redact_file_name, nonredactFileName=non_redact_file_name)

        self.log.info('Verify user data is redacted')
        for log_file in self.analytics_log_files:
            self.verify_log_redaction(server=self.cbas_node, remotepath=remote_path, redactFileName=redact_file_name, nonredactFileName=non_redact_file_name,
                                      logFileName='ns_server.{0}'.format(log_file))

        self.log.info('Verify user data is not displayed in any analytics logs') # The user data must be redacted in logs. We have bugs logged - MB-33110/MB-33109/MB-33093
        user_data_not_redacted = False
        for search_key in self.user_data_search_keys:
            output, _ = self.check_for_user_data_in_redacted_logs(search_key, redact_file_name, remote_path, server=self.cbas_node)
            if len(output) > 0:
                user_data_not_redacted = True
                self.log.info('`{0}` Occur\'s {1} times in analytics logs'.format(search_key, len(output)))
        if user_data_not_redacted:    
            self.fail(msg='User data is not redacted. Refer above logs for non redacted user data')
    
    def verify_user_errors_are_not_surrounded_by_ud_tags(self):
        user_error_queries = ['select 10000000000000000000', 'SELECT BITAND(3,6) AS BitAND']
        self.log.info('Execute queries that result in errors displayed on workbench UI')
        for query in user_error_queries:
            status, _, errors, _, _ = self.cbas_util.execute_statement_on_cbas_util(query)

            if errors :
                self.assertTrue("\<ud\>" not in errors[0]["msg"], msg='User error msg must not be surrounded by ud tags')

        
        self.log.info('Check user data is surrounded by ud tags in logs')
        for query in user_error_queries:
            self.check_user_data_in_server_logs(query.replace("(", "\(").replace(")", "\)"), server=self.cbas_node)

    def verify_system_and_metadata_is_not_redacted(self):
        self.log.info('Generate system and metadata')
        self.generate_system_and_metadata()
        
        self.log.info('Collect logs')
        non_redact_file_name, redact_file_name, remote_path = self.start_log_collection()
        
        self.log.info('Verify System/Metadata is not redacted')
        self.set_redacted_directory(server=self.cbas_node, remote_path=remote_path, redact_file_name=redact_file_name, log_file_name="couchbase.log")
        for search_key in self.system_metadata_search_keys:
            output, _ = self.check_for_user_data_in_redacted_logs(search_key, redact_file_name, remote_path, server=self.cbas_node)
            if len(output) == 0:
                self.fail(msg='%s - metadata/system data must not be redacted - ' % search_key)

    def tearDown(self):
        super(LogRedactionTests, self).tearDown()
