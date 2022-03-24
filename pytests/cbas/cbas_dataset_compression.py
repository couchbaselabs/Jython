from cbas.cbas_base import CBASBaseTest

class CBASDatasetCompression(CBASBaseTest):
    def setUp(self):
        super(CBASDatasetCompression, self).setUp()

        self.log.info("Load Travel-Sample bucket")
        self.assertTrue(self.load_sample_buckets(servers=[self.master], bucketName=self.cb_bucket_name,
                                                 total_items=self.travel_sample_total_docs_count),
                        msg="Failed to load Travel-Sample bucket")

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

    def test_create_dataset_with_snappy_compression(self):

        self.log.info("Disconnect Local link")
        self.cbas_util.disconnect_link()

        self.log.info("Drop dataset if exists")
        drop_dataset_query = 'drop dataset %s if exists' % self.cbas_dataset_name
        self.cbas_util.execute_statement_on_cbas_util(drop_dataset_query)

        self.log.info("Create dataset with compression")
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
            "create dataset ds1 with {'storage-block-compression': {'scheme': 'snappy'}} on `travel-sample`")
        self.assertEqual(status, "success", "Dataset creation with compression failed")

        self.cbas_util.create_dataset_on_bucket("travel-sample", "ds2")

        self.cbas_util.connect_link()

        self.cbas_util.validate_cbas_dataset_items_count("ds1", 31591)

        self.cbas_util.validate_cbas_dataset_items_count("ds2", 31591)

        self.assertEqual(self.cbas_util.get_ds_compression_type("ds1"), "snappy",
                         "ds1 dataset not compressed with type snappy")
        self.assertEqual(self.cbas_util.get_ds_compression_type("ds2"), "snappy",
                         "ds2 dataset compression type is snappy")

    def test_create_dataset_with_none_compression(self):

        self.log.info("Disconnect Local link")
        self.cbas_util.disconnect_link()

        self.log.info("Drop dataset if exists")
        drop_dataset_query = 'drop dataset %s if exists' % self.cbas_dataset_name
        self.cbas_util.execute_statement_on_cbas_util(drop_dataset_query)

        self.log.info("Create dataset with compression")
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
            "create dataset ds1 with {'storage-block-compression': {'scheme': 'none'}} on `travel-sample`")
        self.assertEqual(status, "success", "Dataset creation with compression failed")

        self.cbas_util.create_dataset_on_bucket("travel-sample", "ds2")

        self.cbas_util.connect_link()

        self.cbas_util.validate_cbas_dataset_items_count("ds1", 31591)

        self.cbas_util.validate_cbas_dataset_items_count("ds2", 31591)

        self.assertIsNone(self.cbas_util.get_ds_compression_type("ds1"), "ds1 dataset compression type is not None")
        self.assertEqual(self.cbas_util.get_ds_compression_type("ds2"), "snappy",
                         "ds2 dataset compression type is not snappy")
        self.sleep(10, "Waiting for dataset compression to finish")

        # Fetch storage/stats
        _, results, _ = self.cbas_util.fetch_cbas_storage_stats()

        ds1_totalSize = 0
        ds2_totalSize = 0

        for result in results:
            if result["dataset"] == "ds1":
                ds1_totalSize = result["totalSize"]
            if result["dataset"] == "ds2":
                ds2_totalSize = result["totalSize"]

        self.log.info("Size of ds1 (uncompressed dataset) : %s" % str(ds1_totalSize))
        self.log.info("Size of ds2 (compressed dataset) : %s" % str(ds2_totalSize))
        self.assertTrue(ds1_totalSize > ds2_totalSize,
                        "Size of compressed dataset is not less than size of uncompressed dataset")

    def test_create_dataset_with_invalid_compression_type(self):

        self.log.info("Disconnect Local link")
        self.cbas_util.disconnect_link()

        self.log.info("Drop dataset if exists")
        drop_dataset_query = 'drop dataset %s if exists' % self.cbas_dataset_name
        self.cbas_util.execute_statement_on_cbas_util(drop_dataset_query)

        self.log.info("Create dataset with compression")
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
            "create dataset ds1 with {'storage-block-compression': {'scheme': 'junk'}} on `travel-sample`")
        self.assertNotEqual(status, "success", "Able to create a dataset using an invalid scheme name")

    def test_global_compression_type(self):
        # Set snappy as the global compression type
        self.cbas_util.set_global_compression_type("snappy")

        # Restart node for the setting to take impact
        self.log.info('Restart cbas node to apply the parameter change')
        status, _, _ = self.cbas_util.restart_analytics_cluster_uri()
        self.assertTrue(status, msg='Failed to restart cbas node')
        self.cbas_util.wait_for_cbas_to_recover()

        # Create a dataset without specifying compression type and validate
        self.log.info("Disconnect Local link")
        self.cbas_util.disconnect_link()

        self.log.info("Drop dataset if exists")
        drop_dataset_query = 'drop dataset %s if exists' % self.cbas_dataset_name
        self.cbas_util.execute_statement_on_cbas_util(drop_dataset_query)

        self.log.info("Create dataset without specifying compression")
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
            "create dataset ds1 on `travel-sample`")
        self.assertEqual(status, "success", "Dataset creation failed")

        self.cbas_util.connect_link()

        self.cbas_util.validate_cbas_dataset_items_count("ds1", 31591)

        self.assertEqual(self.cbas_util.get_ds_compression_type("ds1"), "snappy",
                         "ds1 dataset not compressed with type snappy")

    def test_global_compression_type_invalid(self):
        # Set snappy as the global compression type
        self.assertFalse(self.cbas_util.set_global_compression_type("junk"),
                         "Able to set invalid value for compression")

    def test_global_compression_type_override_with_none(self):
        # Set snappy as the global compression type
        self.cbas_util.set_global_compression_type("snappy")

        # Restart node for the setting to take impact
        self.log.info('Restart cbas node to apply the parameter change')
        status, _, _ = self.cbas_util.restart_analytics_cluster_uri()
        self.assertTrue(status, msg='Failed to restart cbas node')
        self.cbas_util.wait_for_cbas_to_recover()

        # Create a dataset without specifying compression type and validate
        self.log.info("Disconnect Local link")
        self.cbas_util.disconnect_link()

        self.log.info("Drop dataset if exists")
        drop_dataset_query = 'drop dataset %s if exists' % self.cbas_dataset_name
        self.cbas_util.execute_statement_on_cbas_util(drop_dataset_query)

        self.log.info("Create dataset with compression type = none")
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
            "create dataset ds1 with {'storage-block-compression': {'scheme': 'none'}} on `travel-sample`")
        self.assertEqual(status, "success", "Dataset creation with compression failed")

        self.cbas_util.connect_link()

        self.cbas_util.validate_cbas_dataset_items_count("ds1", 31591)

        self.assertIsNone(self.cbas_util.get_ds_compression_type("ds1"), "ds1 dataset compression type is not None")

    def test_global_compression_type_override_with_snappy(self):
        # Set snappy as the global compression type
        self.cbas_util.set_global_compression_type("none")

        # Restart node for the setting to take impact
        self.log.info('Restart cbas node to apply the parameter change')
        status, _, _ = self.cbas_util.restart_analytics_cluster_uri()
        self.assertTrue(status, msg='Failed to restart cbas node')
        self.cbas_util.wait_for_cbas_to_recover()

        self.log.info("Disconnect Local link")
        self.cbas_util.disconnect_link()

        self.log.info("Drop dataset if exists")
        drop_dataset_query = 'drop dataset %s if exists' % self.cbas_dataset_name
        self.cbas_util.execute_statement_on_cbas_util(drop_dataset_query)

        self.log.info("Create dataset with compression type = snappy")
        status, metrics, errors, results, _ = self.cbas_util.execute_statement_on_cbas_util(
            "create dataset ds1 with {'storage-block-compression': {'scheme': 'snappy'}} on `travel-sample`")
        self.assertEqual(status, "success", "Dataset creation with compression failed")

        self.cbas_util.connect_link()

        self.cbas_util.validate_cbas_dataset_items_count("ds1", 31591)

        self.assertEqual(self.cbas_util.get_ds_compression_type("ds1"), "snappy",
                         "ds1 dataset not compressed with type snappy")

    def tearDown(self):
        super(CBASDatasetCompression, self).tearDown()
