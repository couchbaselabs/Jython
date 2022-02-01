import json

from cbas.cbas_base import CBASBaseTest
from remote.remote_util import RemoteMachineShellConnection
from Rbac_utils.Rbac_ready_functions import rbac_utils
from TestInput import TestInputSingleton


class MetadataBackup(CBASBaseTest):

    def setUp(self):
        self.input = TestInputSingleton.input
        if "set_cbas_memory_from_available_free_memory" not in self.input.test_params:
            self.input.test_params.update({"set_cbas_memory_from_available_free_memory": True})
        super(MetadataBackup, self).setUp()

        self.log.info('Metadata for Default dataverse')
        self.skip_ds_index_creation_default = self.input.param("skip_ds_index_creation_default", False)
        self.beer_sample_bucket = 'beer-sample'
        self.travel_sample_bucket = 'travel-sample'
        self.dataverse = 'Default'
        self.dataset = 'ds'
        self.index_name = 'idx'
        self.index_field_composite = 'geo.lon:double, geo.lat:double'

        self.log.info('Metadata for Custom dataverse dv1')
        self.skip_ds_index_creation_dv1 = self.input.param("skip_ds_index_creation_dv1", False)
        self.dataverse_1 = 'dv1'
        self.dataset_1 = 'ds1'
        self.index_name_1 = 'idx1'

        self.log.info('Metadata for Custom dataverse dv1')
        self.skip_ds_index_creation_dv2 = self.input.param("skip_ds_index_creation_dv2", False)
        self.dataverse_2 = 'dv2'
        self.dataset_2 = 'ds2'
        self.index_name_2 = 'idx2'
        self.index_field = 'country:string'

        self.log.info('Load beer-sample bucket')
        self.load_sample_buckets(servers=[self.master], bucketName=self.beer_sample_bucket, total_items=self.beer_sample_docs_count)
        self.cbas_util.createConn(self.beer_sample_bucket)

        self.log.info('Load travel-sample bucket')
        self.load_sample_buckets(servers=[self.master], bucketName=self.travel_sample_bucket, total_items=self.travel_sample_total_docs_count)
        self.cbas_util.createConn(self.travel_sample_bucket)

    def create_ds_index_and_validate_count(self):

        if not self.skip_ds_index_creation_default:
            self.log.info('Create dataset on %s bucket' % (self.beer_sample_bucket))
            self.cbas_util.create_dataset_on_bucket(self.beer_sample_bucket, self.dataset, compress_dataset=self.compress_dataset)

            self.log.info('Create secondary index on %s dataset and %s bucket' % (self.dataset, self.beer_sample_bucket))
            create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(self.index_name, self.dataset, self.index_field_composite)
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
            self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Create dataverse %s' % self.dataverse_1)
        self.cbas_util.create_dataverse_on_cbas(dataverse_name=self.dataverse_1)

        if not self.skip_ds_index_creation_dv1:
            self.log.info('Create dataset on %s dataverse and %s bucket' % (self.dataverse_1, self.beer_sample_bucket))
            self.cbas_util.create_dataset_on_bucket(self.beer_sample_bucket, self.dataset_1, dataverse=self.dataverse_1, compress_dataset=self.compress_dataset)

            self.log.info('Create secondary index on %s dataverse, %s dataset and %s bucket' % (self.dataverse_1, self.dataset_1, self.beer_sample_bucket))
            create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(self.index_name_1, self.dataverse_1 + "." + self.dataset_1, self.index_field)
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
            self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Create dataverse %s' % self.dataverse_2)
        self.cbas_util.create_dataverse_on_cbas(dataverse_name=self.dataverse_2)

        if not self.skip_ds_index_creation_dv2:
            self.log.info('Create dataset on %s dataverse and %s bucket' % (self.dataverse_2, self.travel_sample_bucket))
            self.cbas_util.create_dataset_on_bucket(self.travel_sample_bucket, self.dataset_2, dataverse=self.dataverse_2, compress_dataset=self.compress_dataset)

            self.log.info('Create secondary index on %s dataverse, %s dataset and %s bucket' % (self.dataverse_2, self.dataset_2, self.travel_sample_bucket))
            create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(self.index_name_2, self.dataverse_2 + "." + self.dataset_2, self.index_field)
            status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
            self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Connect to Local link on Default dataverse')
        self.cbas_util.connect_link()

        self.log.info('Connect to Local link on %s' % self.dataverse_1)
        self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')

        self.log.info('Connect to Local link on %s' % self.dataverse_2)
        self.cbas_util.connect_link(link_name=self.dataverse_2 + '.Local')

        self.log.info('Verify bucket state before backup')
        self.build_bucket_status_map()
        if not self.skip_ds_index_creation_default:
            self.assertEquals(self.dataverse_bucket_map[self.dataverse][self.beer_sample_bucket], 'connected', msg='Bucket state is incorrect for %s dataverse' % self.dataverse)

            self.log.info('Validate document count on CBAS')
            self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.dataverse + "." + self.dataset, self.beer_sample_docs_count), msg='Count mismatch on CBAS')

        if not self.skip_ds_index_creation_dv1:
            self.assertEquals(self.dataverse_bucket_map[self.dataverse_1][self.beer_sample_bucket], 'connected', msg='Bucket state is incorrect for %s dataverse' % self.dataverse_1)

            self.log.info('Validate document count on CBAS')
            self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.dataverse_1 + "." + self.dataset_1, self.beer_sample_docs_count), msg='Count mismatch on CBAS')

        if not self.skip_ds_index_creation_dv2:
            self.assertEquals(self.dataverse_bucket_map[self.dataverse_2][self.travel_sample_bucket], 'connected', msg='Bucket state is incorrect for %s dataverse' % self.dataverse_2)

            self.log.info('Validate document count on CBAS')
            self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.dataverse_2 + "." + self.dataset_2, self.travel_sample_docs_count), msg='Count mismatch on CBAS')

    def validate_dataverse_metadata_post_restore(self, dataverse_name='Default', expected_count=1):
        dataverse_query = 'select count(*) from Metadata.`Dataverse` where DataverseName = "{0}"'.format(dataverse_name)
        dataverse_count = self.cbas_util.execute_statement_on_cbas_util(dataverse_query)[3][0]['$1']
        self.assertEquals(dataverse_count, expected_count, msg='Dataverse count mismatch')

    def validate_dataset_metadata_post_restore(self, dataset_name, dataverse_name='Default', expected_count=1):
        dataset_query = 'select count(*) from Metadata.`Dataset` where DataverseName = "{0}" and DatasetName = "{1}"'.format(dataverse_name, dataset_name)
        dataset_count = self.cbas_util.execute_statement_on_cbas_util(dataset_query)[3][0]['$1']
        self.assertEquals(dataset_count, expected_count, msg='Dataset count mismatch')

    def validate_index_metadata_post_restore(self, dataset_name, index_name, dataverse_name='Default', expected_count=1):
        index_query = 'select count(*) from Metadata.`Index` where DataverseName = "{0}" and DatasetName="{1}" and IndexName="{2}"'.format(dataverse_name, dataset_name, index_name)
        index_count = self.cbas_util.execute_statement_on_cbas_util(index_query)[3][0]['$1']
        self.assertEquals(index_count, expected_count, msg='Index count mismatch')

    def validate_metadata(self, dataverse_name, dataset_name, index_name, dataverse_count=0, dataset_count=0, index_count=0):
        dataverse_name = dataverse_name.replace('`', '')
        dataset_name = dataset_name.replace('`', '')
        index_name = index_name.replace('`', '')
        self.validate_dataverse_metadata_post_restore(dataverse_name, dataverse_count)
        self.validate_dataset_metadata_post_restore(dataset_name, dataverse_name, dataset_count)
        self.validate_index_metadata_post_restore(dataset_name, index_name, dataverse_name, index_count)

    def build_bucket_status_map(self):
        self.log.info('Fetch bucket state')
        status, content, _ = self.cbas_util.fetch_bucket_state_on_cbas()
        self.assertTrue(status, msg='Fetch bucket state failed')

        self.dataverse_bucket_map = {}
        content = json.loads(content)
        for bucket in content['buckets']:
            curr_dataverse = bucket['dataverse']
            if isinstance(curr_dataverse, str) or isinstance(curr_dataverse, unicode):
                curr_dataverse = [curr_dataverse]
            for ds in curr_dataverse:
                if ds not in self.dataverse_bucket_map:
                    self.dataverse_bucket_map[ds] = dict()
                self.dataverse_bucket_map[ds][bucket['name']] = bucket['state']

    def test_disabling_analytics_with_cbbackupmgr_backup(self):

        self.log.info('Load documents in KV, create dataverse\'s, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup using cbbackupmgr with analytics disabled')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master, disable_analytics=True)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop dataset on default bucket')
        self.assertTrue(self.cbas_util.drop_dataset(self.dataset), msg='Failed to drop dataset')

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Verify bucket state post restore')
        self.build_bucket_status_map()
        self.assertFalse(self.dataverse in self.dataverse_bucket_map)
        self.assertEquals(self.dataverse_bucket_map[self.dataverse_1][self.beer_sample_bucket], 'connected')
        self.assertEquals(self.dataverse_bucket_map[self.dataverse_2][self.travel_sample_bucket], 'connected')

        self.log.info('Validate metadata for default dataverse')
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=0, index_count=0)

    def test_disabling_analytics_with_cbbackupmgr_restore(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop custom dataverse')
        self.cbas_util.disconnect_link(link_name=self.dataverse_1 + '.Local')
        self.cbas_util.drop_dataverse_on_cbas(dataverse_name=self.dataverse_1)

        self.log.info('Restore Analytics metadata using cbbackupmgr with analytics disabled')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node, disable_analytics=True)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Verify bucket state')
        self.build_bucket_status_map()
        self.assertEqual(self.dataverse_bucket_map[self.dataverse][self.beer_sample_bucket], 'connected')
        self.assertFalse(self.dataverse_1 in self.dataverse_bucket_map)
        self.assertEqual(self.dataverse_bucket_map[self.dataverse_2][self.travel_sample_bucket], 'connected')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)

    def test_cbbackupmgr_allways_backsup_full_metadata(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Create additional dataset on Default bucket')
        self.dataset_1_post_backup = self.dataset + "_1"
        self.cbas_util.create_dataset_on_bucket(self.beer_sample_bucket, self.dataset_1_post_backup)

        self.log.info('Create secondary index on %s dataset and %s bucket' % (self.dataset_1_post_backup, self.beer_sample_bucket))
        create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(self.index_name, self.dataset_1_post_backup, self.index_field)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Again backup Analytics metadata - This will backup everything and not just newly created dataset & index')
        o = shell.create_backup(self.master, skip_configure_bkup=True)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backing up again was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Connect to Local link')
        self.cbas_util.connect_link()

        self.log.info('Connect to Local link on custom dataverse')
        self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')
        self.cbas_util.connect_link(link_name=self.dataverse_2 + '.Local')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)
        self.validate_metadata(self.dataverse, self.dataset_1_post_backup, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)

    def test_analytics_backup_restore_using_api(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata for beer-sample using API')
        response = self.cbas_util.backup_cbas_metadata(bucket_name=self.beer_sample_bucket)
        self.assertEquals(response['status'], 'success', msg='Failed to backup analytics metadata')

        self.log.info('Drop dataset\'s on %s bucket' % self.beer_sample_bucket)
        self.cbas_util.disconnect_link(self.dataverse_1 + ".Local")
        self.assertTrue(self.cbas_util.drop_dataset(self.dataset), msg='Failed to drop dataset %s' % self.dataset)
        self.assertTrue(self.cbas_util.drop_dataverse_on_cbas(self.dataverse_1), msg='Failed to drop dataverse %s' % self.dataverse_1)

        self.log.info('Restore Analytics metadata for beer-sample using API')
        response = self.cbas_util.restore_cbas_metadata(response, bucket_name=self.beer_sample_bucket)
        self.assertEquals(response['status'], 'success', msg='Failed to restore analytics metadata')

        self.log.info('Verify bucket state')
        self.build_bucket_status_map()
        self.assertEqual(self.dataverse_bucket_map[self.dataverse][self.beer_sample_bucket], 'disconnected')
        self.assertEqual(self.dataverse_bucket_map[self.dataverse_1][self.beer_sample_bucket], 'disconnected')
        self.assertEqual(self.dataverse_bucket_map[self.dataverse_2][self.travel_sample_bucket], 'connected')

        self.log.info('Verify data is not re-ingested on non-impacted dataset')
        self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(self.dataverse_2 + "." + self.dataset_2, self.travel_sample_docs_count, num_tries=1), msg='Count mismatch on CBAS')

        self.log.info('Connect to Local link')
        self.cbas_util.connect_link()

        self.log.info('Connect to Local link on dataverse')
        self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)

    def test_analytics_backup_restore_using_cbbackupmgr(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Verify bucket state')
        self.build_bucket_status_map()
        if not self.skip_ds_index_creation_default:
            self.assertEqual(self.dataverse_bucket_map[self.dataverse][self.beer_sample_bucket], 'disconnected')
            self.cbas_util.connect_link()

        if not self.skip_ds_index_creation_dv1:
            self.assertEqual(self.dataverse_bucket_map[self.dataverse_1][self.beer_sample_bucket], 'disconnected')
            self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')

        if not self.skip_ds_index_creation_dv2:
            self.assertEqual(self.dataverse_bucket_map[self.dataverse_2][self.travel_sample_bucket], 'disconnected')
            self.cbas_util.connect_link(link_name=self.dataverse_2 + '.Local')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        if not self.skip_ds_index_creation_default:
            self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)
        else:
            self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=0, index_count=0)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        if not self.skip_ds_index_creation_dv1:
            self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)
        else:
            self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=0, index_count=0)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        if not self.skip_ds_index_creation_dv2:
            self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)
        else:
            self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=0, index_count=0)

        if self.compress_dataset:
            self.assertEqual(self.cbas_util.get_ds_compression_type(self.dataset), "snappy",
                             "ds1 dataset not compressed with type snappy")
            self.assertEqual(self.cbas_util.get_ds_compression_type(self.dataset_1), "snappy",
                             "ds1 dataset not compressed with type snappy")
            self.assertEqual(self.cbas_util.get_ds_compression_type(self.dataset_2), "snappy",
                             "ds1 dataset not compressed with type snappy")

    def test_analytics_single_bucket_backup_and_restore_using_cbbackupmgr(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master, exclude_bucket=[self.travel_sample_bucket])
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Connect to Local link')
        self.cbas_util.connect_link()

        self.log.info('Connect to Local link on dataverse')
        self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=0, index_count=0)

    def test_analytics_multiple_bucket_backup_and_restore_using_cbbackupmgr(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master, include_buckets=[self.beer_sample_bucket, self.travel_sample_bucket])
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Connect to Local link')
        self.cbas_util.connect_link()

        self.log.info('Connect to Local link on dataverse')
        self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)

    def test_cbbackupmgr_restore_with_dataverse_already_present(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        for x in range(2):
            self.log.info('Restore Analytics metadata using cbbackupmgr')
            shell = RemoteMachineShellConnection(self.master)
            o = shell.restore_backup(self.cbas_node)
            self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

            self.log.info('Verify bucket state')
            self.build_bucket_status_map()
            self.assertEqual(self.dataverse_bucket_map[self.dataverse][self.beer_sample_bucket], 'disconnected')
            self.assertEqual(self.dataverse_bucket_map[self.dataverse_1][self.beer_sample_bucket], 'disconnected')
            self.assertEqual(self.dataverse_bucket_map[self.dataverse_2][self.travel_sample_bucket], 'disconnected')

            self.log.info('Connect to Local link')
            self.cbas_util.connect_link()

            self.log.info('Connect to Local link on custom dataverse')
            self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')
            self.cbas_util.connect_link(link_name=self.dataverse_2 + '.Local')

            self.log.info('Validate metadata for %s dataverse' % self.dataverse)
            self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

            self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
            self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)

            self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
            self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)

    def test_analytics_backup_restore_fails_while_rebalance_is_in_progress(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata for beer-sample using API')
        successful_bkup_response = self.cbas_util.backup_cbas_metadata(bucket_name=self.beer_sample_bucket)
        self.assertEquals(successful_bkup_response['status'], 'success', msg='Failed to backup analytics metadata')

        self.log.info('Add a new analytics node and rebalance')
        self.add_node(self.cbas_servers[0], services=["cbas"], rebalance=True, wait_for_rebalance_completion=False)
        while True:
            status, progress = self.rest._rebalance_status_and_progress()
            if status == "running" and progress > 30:
                break

        self.log.info('Verify backup analytics must pass while rebalance is in progress')
        response = self.cbas_util.backup_cbas_metadata(bucket_name=self.beer_sample_bucket)
        self.assertEquals(response['status'], 'success', msg='Backup must pass during rebalance')

        self.log.info('Verify restore analytics must fail while rebalance is in progress')
        response = self.cbas_util.restore_cbas_metadata(successful_bkup_response, bucket_name=self.beer_sample_bucket)
        self.assertEquals(response['errors'][0]['msg'], 'Operation cannot be performed during rebalance', msg='Restore must fail during rebalance')

    def test_cbbackupmgr_backup_bucket_only_if_user_has_bucket_permission(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Create user with backup permission on beer-sample')
        user = 'user_with_bkup_restore_permission_beer_sample'
        self.rbac_util = rbac_utils(self.master)
        self.rbac_util._create_user_and_grant_role(user, 'data_backup[beer-sample]')
        self.sleep(2)

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.cbas_node, username=user)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node, username=user)

        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Verify bucket state')
        self.build_bucket_status_map()
        self.assertEqual(self.dataverse_bucket_map[self.dataverse][self.beer_sample_bucket], 'disconnected')
        self.assertEqual(self.dataverse_bucket_map[self.dataverse_1][self.beer_sample_bucket], 'disconnected')
        self.assertFalse(self.dataverse_2 in self.dataverse_bucket_map)

        self.log.info('Connect to Local link')
        self.cbas_util.connect_link()

        self.log.info('Connect to Local link on dataverse')
        self.cbas_util.connect_link(link_name=self.dataverse_1 + '.Local')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=0, index_count=0)

    def test_empty_dataverses_are_imported(self):

        self.log.info('Create dataverse\'s')
        self.cbas_util.create_dataverse_on_cbas(self.dataverse_1)
        self.cbas_util.create_dataverse_on_cbas(self.dataverse_2)

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=0, index_count=0)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=0, index_count=0)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=0, index_count=0)

    def test_backup_restore_empty_analytics_metadata(self):

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=0, index_count=0)

    def test_backuprestore_on_node_having_no_analytics_service(self):

        self.log.info('Add an extra KV node')
        self.add_node(self.servers[1], rebalance=True)

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Restore Analytics metadata using cbbackupmgr on KV node')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.servers[1])
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

    def test_cbbackupmgr_fail_if_impacted_kv_bucket_is_deleted(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Delete %s bucket on KV' % self.beer_sample_bucket)
        self.delete_bucket_or_assert(self.master, bucket=self.beer_sample_bucket)

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node)
        self.assertTrue('Error restoring cluster' in ''.join(o), msg='Restore must fail')

    def test_cbbackupmgr_does_not_fail_if_non_impacted_kv_bucket_is_deleted(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Delete %s bucket on KV' % self.beer_sample_bucket)
        self.delete_bucket_or_assert(self.master, bucket=self.beer_sample_bucket)

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.cbas_node, exclude_bucket=[self.beer_sample_bucket])
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)

    def test_cbbackupmgr_metadata_with_escape_characters_and_dataset_conflicts(self):

        self.log.info('Create dataset on default dataverse')
        dataset_name_escape_characters = '`ds-beer`'
        index_name_escape_characters = '`idx-name`'
        dataverse_name_escape_characters = '`dataverse-custom`'
        self.cbas_util.create_dataset_on_bucket(self.beer_sample_bucket, dataset_name_escape_characters, where_field='type', where_value='beer')

        self.log.info('Create index on default dataverse')
        create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(index_name_escape_characters, dataset_name_escape_characters, self.index_field_composite)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Connect link Local')
        self.cbas_util.connect_link()

        self.log.info("Create primary index")
        query = "CREATE PRIMARY INDEX ON `{0}` using gsi".format(self.beer_sample_bucket)
        self.rest.query_tool(query)

        self.log.info('Validate dataset count on default bucket')
        count_n1ql = self.rest.query_tool('select count(*) from `%s` where type = "beer"' % self.beer_sample_bucket)['results'][0]['$1']
        self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(dataset_name_escape_characters, count_n1ql), msg='Count mismatch on CBAS')

        self.log.info('Create custom dataverse')
        self.cbas_util.create_dataverse_on_cbas(dataverse_name_escape_characters)

        self.log.info('Create dataset on custom dataverse')
        self.cbas_util.create_dataset_on_bucket(self.beer_sample_bucket, dataset_name_escape_characters, dataverse=dataverse_name_escape_characters)

        self.log.info('Create index on default dataverse')
        create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(index_name_escape_characters,
                                                                                   dataverse_name_escape_characters + "." + dataset_name_escape_characters,
                                                                                   self.index_field)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Connect link Local')
        self.cbas_util.execute_statement_on_cbas_util('connect link %s.Local' % dataverse_name_escape_characters)

        self.log.info('Validate dataset count on custom bucket')
        self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(dataverse_name_escape_characters + "." + dataset_name_escape_characters, self.beer_sample_docs_count),
                        msg='Count mismatch on CBAS')

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Verify bucket state')
        self.build_bucket_status_map()

        self.assertEqual(self.dataverse_bucket_map[self.dataverse][self.beer_sample_bucket], 'connected')
        self.assertEqual(self.dataverse_bucket_map[self.dataverse_1][self.beer_sample_bucket], 'connected')
        self.assertEqual(self.dataverse_bucket_map[self.dataverse_2][self.travel_sample_bucket], 'connected')

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.master)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Connect link Local')
        self.cbas_util.execute_statement_on_cbas_util('connect link %s.Local' % dataverse_name_escape_characters)

        self.log.info('Connect link Local')
        self.cbas_util.connect_link()

        self.log.info('Validate dataset count post restore')
        self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(dataset_name_escape_characters, count_n1ql), msg='Count mismatch on CBAS')
        self.assertTrue(self.cbas_util.validate_cbas_dataset_items_count(dataverse_name_escape_characters + "." + dataset_name_escape_characters, self.beer_sample_docs_count),
                        msg='Count mismatch on CBAS')

        self.log.info('drop dataset on default dataverse')
        self.cbas_util.drop_dataset(dataset_name_escape_characters)

        self.log.info('create a dataset on Default dataverse')
        dataset_name = 'ds'
        self.cbas_util.create_dataset_on_bucket(self.beer_sample_bucket, dataset_name)

        self.log.info('Create index on default dataverse')
        create_idx_statement = 'create index {0} if not exists on {1}({2})'.format(self.index_name, dataset_name, self.index_field_composite)
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(create_idx_statement)
        self.assertTrue(status == 'success', 'Create Index query failed')

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.master)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, dataset_name_escape_characters, index_name_escape_characters, dataverse_count=1, dataset_count=1, index_count=1)
        self.validate_metadata(self.dataverse, dataset_name, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

    def test_cbbackupmgr_while_analytics_node_unreachable(self):

        self.log.info('Load documents in KV, create dataverse, datasets, index and validate')
        self.create_ds_index_and_validate_count()

        self.log.info('Backup Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.create_backup(self.master)
        self.assertTrue('Backup completed successfully' in ''.join(o), msg='Backup was unsuccessful')

        self.log.info('Drop all analytics data - Dataverses, Datasets, Indexes')
        self.cleanup_cbas()

        self.log.info('Shutdown analytics node')
        shell = RemoteMachineShellConnection(self.cbas_node)
        shell.stop_couchbase()

        self.log.info('Verify restore metadata fails')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.master)
        self.assertTrue('Error restoring cluster' in ''.join(o), msg='Restore must be unsuccessful')

        self.log.info('Start back analytics node')
        shell = RemoteMachineShellConnection(self.cbas_node)
        shell.start_couchbase()
        self.cbas_util.wait_for_cbas_to_recover()

        self.log.info('Restore Analytics metadata using cbbackupmgr')
        shell = RemoteMachineShellConnection(self.master)
        o = shell.restore_backup(self.master)
        self.assertTrue('Restore completed successfully' in ''.join(o), msg='Restore was unsuccessful')

        self.log.info('Validate metadata for %s dataverse' % self.dataverse)
        self.validate_metadata(self.dataverse, self.dataset, self.index_name, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_1)
        self.validate_metadata(self.dataverse_1, self.dataset_1, self.index_name_1, dataverse_count=1, dataset_count=1, index_count=1)

        self.log.info('Validate metadata for %s dataverse' % self.dataverse_2)
        self.validate_metadata(self.dataverse_2, self.dataset_2, self.index_name_2, dataverse_count=1, dataset_count=1, index_count=1)

    def tearDown(self):
        super(MetadataBackup, self).tearDown()
