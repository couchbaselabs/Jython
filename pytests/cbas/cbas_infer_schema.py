import json

from cbas.cbas_infer_base import CBASInferBase
from cbas.cbas_infer_base import CBASInferCompareJson
from sdk_client import SDKClient


class CBASInferSchema(CBASInferBase):

    def setUp(self):
        super(CBASInferSchema, self).setUp()

    """
    cbas.cbas_infer_schema.CBASInferSchema.verify_analytics_supports_infer_schema,default_bucket=True,cbas_dataset_name=ds,cb_bucket_name=default,items=10,validate_response=True
    """

    def verify_analytics_supports_infer_schema(self):
        self.log.info('Execute INFER schema on dataset that does not exist')
        status, _, error, _, _ = self.cbas_util.execute_statement_on_cbas_util(
            'array_infer_schema((%s),{"similarity_metric":0.6})' % self.cb_bucket_name)
        self.assertTrue(status == "fatal", msg='Infer schema must fail as dataset does not exist')
        expected_error = "Cannot find analytics collection {0} in analytics scope Default nor an alias with name {1}".format(
            self.cb_bucket_name, self.cb_bucket_name)
        self.assertTrue(expected_error in error[0]['msg'], msg='Error message mismatch')
        self.assertEqual(error[0]['code'], 24045, msg='Error code mismatch')

        self.log.info('Create dataset')
        self.cbas_util.createConn(self.cb_bucket_name)
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Execute INFER schema on dataset with link disconnected')
        status, _, error, _, _ = self.cbas_util.execute_statement_on_cbas_util(
            'array_infer_schema((%s),{"similarity_metric":0.6})' % self.cbas_dataset_name)
        self.assertTrue(status == "success", msg='Infer schema failed')

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Execute INFER schema on an empty dataset')
        status, _, error, _, _ = self.cbas_util.execute_statement_on_cbas_util(
            'array_infer_schema((%s),{"similarity_metric":0.6})' % self.cbas_dataset_name)
        self.assertTrue(status == "success", msg='Infer schema fails on an empty dataset')

        self.log.info('Execute INFER schema on single value input')
        status, _, error, _, _ = self.cbas_util.execute_statement_on_cbas_util(
            'SELECT Value array_infer_schema(({"a":1}),{"similarity_metric":0.6})')
        self.assertTrue(status == "fatal", msg='Infer schema works only on array')
        # Below might fail if this is resolved - MB-33681 
        self.assertTrue("Type mismatch" in error[0]['msg'], msg='Error message mismatch')
        self.assertEqual(error[0]['code'], 23023, msg='Error code mismatch')

        self.log.info('Load documents in default bucket')
        self.perform_doc_ops_in_all_cb_buckets(self.num_items, "create", 0, self.num_items, batch_size=200)

        self.log.info('Execute INFER schema on dataset with documents')
        status, _, _, result, _ = self.cbas_util.execute_statement_on_cbas_util(
            'array_infer_schema((%s),{"similarity_metric":0.6})' % self.cbas_dataset_name)
        self.assertTrue(status == "success", msg='Failed to run infer schema')

        self.log.info('Fetch INFER response from N1QL')
        result_n1ql = self.rest.query_tool('INFER %s' % self.cb_bucket_name)['results']
        infer_dictionary_n1ql = result_n1ql[0][0]
        property_dictionary_n1ql = infer_dictionary_n1ql['properties']
        document_properties_n1ql = sorted(property_dictionary_n1ql.keys())

        self.log.info('Validate INFER result')
        infer_dictionary = result[0][0]
        property_dictionary = infer_dictionary['properties']
        document_properties = sorted(property_dictionary.keys())

        self.log.info('Verify total document count in INFER response')
        self.assertEqual(infer_dictionary['#docs'], self.num_items, msg='Document count incorrect')

        self.log.info('Verify document properties in INFER response')
        self.assertEqual(document_properties_n1ql, document_properties, msg='Properties mismatch')

        self.log.info('Compare result with golden JSON')
        infer_dictionary = self.remove_samples_from_response(infer_dictionary)
        response_json = json.dumps(infer_dictionary, sort_keys=True, indent=2)
        expected_json = json.dumps(CBASInferCompareJson.get_json('analytics_supports_infer_schema'), sort_keys=True,
                                   indent=2)

        self.assertEqual(response_json, expected_json, msg='response mismatch')

    def verify_infer_schema_on_array(self):
        single_array_query = 'SELECT Value array_infer_schema(([{"a":1},{"a":"aval"},{"a":[1,2]},{"a":{"b":1,"c":"aval","d":"[1,2]","e":{"f":1}}}]),{"similarity_metric":0.6})'
        status, _, _, result, _ = self.cbas_util.execute_statement_on_cbas_util(single_array_query)
        self.assertTrue(status == "success", msg='Failed to run infer schema')

        self.log.info('Compare JSON results')
        response = result[0]
        response = self.remove_samples_from_response(response)

        compare_responses = CBASInferCompareJson.get_json('infer_schema_on_array')
        for index, value in enumerate(compare_responses):
            response_json = json.dumps(response[index], sort_keys=True, indent=2)
            expected_json = json.dumps(compare_responses[index], sort_keys=True, indent=2)

            self.log.info("====")
            self.log.info(response_json)
            self.log.info(expected_json)

            self.assertEqual(response_json, expected_json, msg='response mismatch')

    def verify_infer_schema_on_beer_sample_dataset(self):
        self.log.info('Load beer-sample bucket')
        self.load_sample_buckets(servers=[self.master], bucketName=self.cb_bucket_name,
                                 total_items=self.beer_sample_docs_count)
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.beer_sample_docs_count)

        self.validate_infer_schema_response(self.beer_sample_docs_count, compare_with_n1ql=False)

    def verify_infer_schema_on_travel_sample_dataset(self):
        self.log.info('Load travel-sample bucket')
        self.load_sample_buckets(servers=[self.master], bucketName=self.cb_bucket_name,
                                 total_items=self.travel_sample_docs_count)
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.travel_sample_docs_count)

        self.validate_infer_schema_response(self.travel_sample_docs_count, compare_with_n1ql=False)

    def verify_infer_schema_on_large_dataset_compare_n1ql(self):
        self.log.info('Create dataset')
        self.cbas_util.createConn(self.cb_bucket_name)
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Load documents in default bucket')
        self.perform_doc_ops_in_all_cb_buckets(self.num_items, "create", 0, self.num_items)

        self.log.info('Load more documents with same json property but different property value type')
        gen_load = self.generate_document_with_type_array_and_object()
        self.perform_doc_ops_in_all_cb_buckets(self.num_items, "create", 0, self.num_items, gen_load=gen_load)

        self.log.info('Create primary index on %s' % self.cb_bucket_name)
        self.rest.query_tool('CREATE PRIMARY INDEX idx on %s' % self.cb_bucket_name)

        self.validate_infer_schema_response(self.num_items * 2)

    def verify_infer_schema_on_unique_nested_documents(self):
        self.log.info('Create unique documents')
        client = SDKClient(hosts=[self.master.ip], bucket=self.cb_bucket_name, password=self.master.rest_password)
        documents = [
            '{"from": "user_512", "to": "user_768", "text": "Hey, that Beer you recommended is pretty fab, thx!", "sent_timestamp":476560}',
            '{"user_id": 512, "name": "Bob Likington", "email": "bob.like@gmail.com", "sign_up_timestamp": 1224612317, "last_login_timestamp": 1245613101}',
            '{"user_id": 768, "name": "Simon Neal", "email": "sneal@gmail.com", "sign_up_timestamp": 1225554317, "last_login_timestamp": 1234166701, "country": "Scotland", "pro_account": true, "friends": [512, 666, 742, 1111]}',
            '{"photo_id": "ccbcdeadbeefacee", "size": { "w": 500, "h": 320, "unit": "px" }, "exposure": "1/1082", "aperture": "f/2.4", "flash": false, "camera": { "name": "iPhone 4S", "manufacturer": {"Company":"Apple", "Location": {"City":"California", "Country":"USA"} } }, "user_id": 512, "timestamp": [2011, 12, 13, 16, 31, 7]}'
            ]
        for index, document in enumerate(documents):
            client.insert_document(str(index), document)

        self.log.info('Create primary index on %s' % self.cb_bucket_name)
        self.rest.query_tool('CREATE PRIMARY INDEX idx on %s' % self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.createConn(self.cb_bucket_name)
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, len(documents))

        self.validate_infer_schema_response(len(documents), compare_with_n1ql=False)

    def verify_infer_schema_on_same_type_missing_fields(self):
        self.log.info('Create unique documents')
        client = SDKClient(hosts=[self.master.ip], bucket=self.cb_bucket_name, password=self.master.rest_password)
        documents = [
            '{ "array": [1,2,3,4,5,6], "integer": 10, "float":10.12, "boolean":true, "null":null, "object":{"array": [1,2,3,4,5,6], "integer": 10, "float":10.12, "boolean":true, "null":null}}',
            '{ "array": null, "integer": 10, "float":10.12, "boolean":true, "null":null, "object":{"array": [1,2,3,4,5,6], "integer": 10, "float":10.12, "boolean":true, "null":"null value"}}',
            '{ "array": [1,2,3,4,5,6], "integer": 10, "float":10.12, "boolean":true, "null":null, "object":{"array": null, "integer": null, "float":null, "boolean":null, "null":null}}'
            ]
        for index, document in enumerate(documents):
            client.insert_document(str(index), document)

        self.log.info('Create primary index on %s' % self.cb_bucket_name)
        self.rest.query_tool('CREATE PRIMARY INDEX idx on %s' % self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.createConn(self.cb_bucket_name)
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, len(documents))

        self.validate_infer_schema_response(len(documents))

    def verify_infer_schema_on_documents_with_overlapping_types_same_keys(self):
        self.log.info('Create unique documents')
        client = SDKClient(hosts=[self.master.ip], bucket=self.cb_bucket_name, password=self.master.rest_password)
        documents = [
            '{ "array": 20, "integer": 300.34345, "float":false, "boolean":["a", "b", "c"], "null":null, "string":"300"}'
            '{ "array": 300, "integer": ["a", "b", "c"], "float":1012.56756, "boolean":300, "null":null, "string":10345665}'
            '{ "array": [1, 2, 3], "integer": 10345665, "float":"Steve", "boolean":[[1, 2], [3, 4], []], "null":null, "string":20.343}'
            '{ "array": 20.343, "integer": [[1, 2], [3, 4], []], "float":0.00011, "boolean":[1, 1.1, 1.0, 0], "null":null, "string":[1, 1.1, 1.0, 0]}'
            '{ "array": 10345665, "integer": 1012.56756, "float":1012.56756, "boolean":false, "null":null, "string":[1, "hello", ["a", 1], 2.22]}'
            '{ "array": "Steve", "integer": 1, "float":[1, 2, 3], "boolean":false, "null":null, "string":1}'
            '{ "array": true, "integer": 1.1, "float":20.343, "boolean":["a", "b", "c"], "null":null, "string":300}'
            '{ "array": true, "integer": "Alex", "float":10345665, "boolean":1.1, "null":null, "string":0.00011}'
            '{ "array": 20.343, "integer": 20.343, "float":300, "boolean":true, "null":null, "string":true}'
            '{ "array": 1, "integer": 10345665, "float":300.34345, "boolean":1, "null":null, "string":true}'
        ]
        for index, document in enumerate(documents):
            client.insert_document(str(index), document)

        self.log.info('Create primary index on %s' % self.cb_bucket_name)
        self.rest.query_tool('CREATE PRIMARY INDEX idx on %s' % self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.createConn(self.cb_bucket_name)
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, len(documents))

        self.validate_infer_schema_response(len(documents))

    '''
    Common method to validate the response from Infer Schema
    '''
    def validate_infer_schema_response(self, num_items, compare_with_n1ql=True):
        # Fetch response from N1QL
        self.log.info('Fetch INFER response from N1QL')
        result_n1ql = self.rest.query_tool('INFER `%s`' % self.cb_bucket_name)['results']
        infer_dictionary_n1ql = result_n1ql[0]
        self.log.info("N1QL Infer schema response:")
        self.log.info(infer_dictionary_n1ql)

        document_flavor_properties_n1ql = []
        for flavor_n1ql in infer_dictionary_n1ql:
            property_dictionary_n1ql = flavor_n1ql['properties']
            document_properties_n1ql = sorted(property_dictionary_n1ql.keys())
            document_flavor_properties_n1ql.append({flavor_n1ql["Flavor"]: document_properties_n1ql})

        # Fetch response from Analytics
        self.log.info('Execute INFER schema on dataset with documents')
        status, _, _, result, _ = self.cbas_util.execute_statement_on_cbas_util(
            'array_infer_schema((%s),{"similarity_metric":0.6})' % self.cbas_dataset_name)
        self.log.info('Verify INFER response')
        self.assertTrue(status == "success", msg='Failed to run infer schema')
        infer_dictionary = result[0]
        self.log.info("Analytics Infer schema response:")
        self.log.info(infer_dictionary)

        # Count total docs in the response & segregate document properties by flavors
        totaldocs = 0
        document_flavor_properties = []
        for flavor in infer_dictionary:
            totaldocs += flavor['#docs']
            property_dictionary = flavor['properties']
            document_properties = sorted(property_dictionary.keys())
            flavor_name = flavor["Flavor"].replace("\'", "`")
            document_flavor_properties.append({flavor_name: document_properties})

        # Validate total doc count
        self.log.info('Verify total document count in INFER response')
        self.assertEqual(totaldocs, num_items, msg='Document count incorrect')

        if compare_with_n1ql:
            # Print the N1QL & Analytics Doc Properties per flavor for debugging purposes
            self.log.info("N1QL Doc Properties per flavor")
            self.log.info(document_flavor_properties_n1ql)

            self.log.info("Analytics Doc Properties per flavor")
            self.log.info(document_flavor_properties)

            # Compare N1QL and Analytics Doc Properties.
            self.log.info('Verify document properties in INFER response')
            self.assertEqual(sorted(document_flavor_properties_n1ql), sorted(document_flavor_properties),
                             msg='Properties mismatch')

    def tearDown(self):
        super(CBASInferSchema, self).tearDown()
