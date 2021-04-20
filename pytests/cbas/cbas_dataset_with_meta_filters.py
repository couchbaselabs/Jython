from cbas.cbas_base import CBASBaseTest


class CBASDatasetMetaFilters(CBASBaseTest):

    def setUp(self):
        super(CBASDatasetMetaFilters, self).setUp()

        self.log.info("Load Travel-Sample bucket")
        self.assertTrue(self.load_sample_buckets(
            servers=[self.master], bucketName=self.cb_bucket_name,
            total_items=self.travel_sample_total_docs_count), 
            msg="Failed to load Travel-Sample bucket")

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

    """
    cbas.cbas_dataset_with_meta_filters.CBASDatasetMetaFilters.test_create_data_set_with_meta_filters,default_bucket=False,cb_bucket_name=travel-sample,cbas_dataset_name=ds,remove_bucket_name_from_meta=True
    """
    def test_create_data_set_with_meta_filters(self):
        
        failed_test_count = 0
        failed_test_cases = []
        remove_bucket_name_from_meta = self.input.param('remove_bucket_name_from_meta', False)
        for queries in CBASMetaQueries.META_QUERIES:
            
            if remove_bucket_name_from_meta:
                queries['cbas_query'] = queries['cbas_query'].replace('meta(`travel-sample`).id', 'meta().id') 
            
            test_failed = False
            self.log.info("---------- Running test with id : %s ----------" % queries['id'])
            
            self.log.info("Disconnect Local link")
            self.cbas_util.disconnect_link()
            
            self.log.info("Drop dataset if exists")
            drop_dataset_query = 'drop dataset %s if exists' % self.cbas_dataset_name
            self.cbas_util.execute_statement_on_cbas_util(drop_dataset_query)
    
            self.log.info("Create dataset with meta-filters")
            if not self.cbas_util.execute_statement_on_cbas_util(queries['cbas_query']):
                test_failed = True
                self.log.info("Failed to create dataset for id : %s" % queries['id'])
            
            self.log.info("Connect Local link")
            if not self.cbas_util.connect_link():
                test_failed = True
                self.log.info("Failed to connect link for id : %s" % queries['id'])
            
            self.log.info("Fetch count on N1QL")
            count_n1ql = self.rest.query_tool(queries['n1ql_query'])['results'][0]['$1']
    
            self.log.info("Validate count on CBAS")
            if not self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, count_n1ql):
                test_failed = True
                self.log.info("Count mismatch for id : %s" % queries['id'])
            
            if test_failed:
                failed_test_count += 1
                failed_test_cases.append(queries['id'])
        
        self.log.info("--------- Test run summary ---------")
        self.log.info("Total : %d Passed : %d Failed :%d" %(len(CBASMetaQueries.META_QUERIES), len(CBASMetaQueries.META_QUERIES)-failed_test_count, failed_test_count))
        
        if failed_test_count:
            self.log.info("Logging failed test case Id's")
            for failed_test in failed_test_cases:
                self.log.info(failed_test)
            

    def tearDown(self):
        super(CBASDatasetMetaFilters, self).tearDown()

class CBASMetaQueries:
    META_QUERIES = [
        {
            'id' : 'STARTS WITH ON META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id like "airline%"',
            'n1ql_query': 'select count(*) from `travel-sample` where meta().id like "airline%"'
        },
        {
            'id' : 'ENDS WITH ON META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id like "%airport%"',
            'n1ql_query': 'select count(*) from `travel-sample` where meta().id like "%airport%"',
        },
        {
            'id' : 'CONTAINS ON META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where contains(split(meta(`travel-sample`).id, "_")[0], "hotel")',
            'n1ql_query': 'select count(*) from `travel-sample` where contains(split(meta().id, "_")[0], "hotel")'
        },
        {   
            'id' : 'LIKE WITH WILDCARD ON META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id like "airline_1__"',
            'n1ql_query': 'select count(*) from `travel-sample` where meta().id like "airline_1__"'
        },
        {   
            'id' : 'NOT LIKE ON META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id not like "airline_1__"',
            'n1ql_query': 'select count(*) from `travel-sample` where meta().id not like "airline_1__"'
        },
        {   
            'id' : 'LENGTH ON META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where length(meta(`travel-sample`).id) > 12',
            'n1ql_query': 'select count(*) from `travel-sample` where length(meta().id) > 12'
        },
        {   
            'id' : 'SUBSTRING ON META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where SUBSTR(meta(`travel-sample`).id, 0, 7) = "airline"',
            'n1ql_query': 'select count(*) from `travel-sample` where SUBSTR(meta().id, 0, 7) = "airline"'
        },
        {   
            'id' : 'AND PREDICATE META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id like "airline%" and length(meta(`travel-sample`).id) > 12',
            'n1ql_query': 'select count(*) from `travel-sample` where meta().id like "airline%" and length(meta().id) > 12'
        },
        {   
            'id' : 'OR PREDICATE META().ID',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id like "airline%" or length(meta(`travel-sample`).id) > 15',
            'n1ql_query': 'select count(*) from `travel-sample` where meta().id like "airline%" or length(meta().id) > 15'
        },
        {   
            'id' : 'AND PREDICATE ON META().ID & Document Field',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id like "airline%" and country = "United States"',
            'n1ql_query': 'select count(*) from `travel-sample`  where meta(`travel-sample`).id like "airline%" and country = "United States"'
        },
        {   
            'id' : 'OR PREDICATE ON META().ID & Document Field',
            'cbas_query': 'create dataset ds on `travel-sample` where meta(`travel-sample`).id like "airline%" or name = "Atifly"',
            'n1ql_query': 'select count(*) from `travel-sample` where meta(`travel-sample`).id like "airline%" or name = "Atifly"'
        },
        {   
            'id' : 'FILTER ON META().CAS',
            'cbas_query': 'create dataset ds on `travel-sample` where META(`travel-sample`).cas % 10 = 0',
            'n1ql_query': 'select count(*) from `travel-sample` where META().cas % 10 = 0'
        },
        {   
            'id' : 'FILTER ON META().EXPIRATION',
            'cbas_query': 'create dataset ds on `travel-sample` where META(`travel-sample`).expiration = 0 and `type` = "hotel"',
            'n1ql_query': 'select count(*) from `travel-sample` where META().expiration == 0 and `type` = "hotel"'
        },
    ]
    
    def __init__(self):
        pass
