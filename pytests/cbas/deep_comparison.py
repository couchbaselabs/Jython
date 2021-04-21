from cbas.cbas_base import CBASBaseTest
import json

class DeepComparison(CBASBaseTest):

    def setUp(self):
        super(DeepComparison, self).setUp()

    def test_deep_comparision_on_array(self):

        self.log.info('Execute query on SQL++')
        sql_query = """FROM OBJECT_VALUES(
                    {
                    "t1": {"c":"[9,2] = null", "r":[9,2] = null},
                    "t2": {"c":"[9,2] = missing", "r":[9,2] = missing},
                    "t3": {"c":"[9,2] > null", "r":[9,2] > null},
                    "t4": {"c":"[9,2] > missing", "r":[9,2] > missing},
                    "t5": {"c":"['red', null] < ['red', null]", "r":['red', null] < ['red', null]},
                    "t7": {"c":"[1,2] < [1,2,missing]", "r":[1,2] < [1,2,missing]},
                    "t8": {"c":"[1,2] < [1,2,null]", "r":[1,2] < [1,2,null]},
                    "t9": {"c":"[null,5] >= [null,5]", "r":[null,5] >= [null,5]},
                    "t10": {"c":"[null,8] < [4, 9]", "r":[null,8] < [4, 9]},
                    "t11": {"c":"[null,1] > [1,1,3]", "r":[null,1] > [1,1,3]},
                    "t12": {"c":"[null, null, null] = [null, null, null]", "r": [null, null, null] = [null, null, null]},
                    "t13": {"c":"[1, null, 3] = [1, 2, 3]", "r":[1, null, 3] = [1, 2, 3]},
                    "t14": {"c":"[1, null, 3] != [1, 2, 3]", "r":[1, null, 3] != [1, 2, 3]},
                    "t15": {"c":"[1, null, 3] < [1, 2, 3]", "r":[1, null, 3] < [1, 2, 3]},
                    "t16": {"c":"[1, null, missing, 4] < [1, 2, 3, 4]", "r":[1, null, missing, 4] < [1, 2, 3, 4]},
                    "t17": {"c":"[1, null, 3] < [1, 2, 99]", "r":[1, null, 3] < [1, 2, 99]},
                    "t18": {"c":"[1, null, 99] < [1, 2, 3]", "r":[1, null, 99] < [1, 2, 3]},
                    "t19": {"c":"[[1.0,4], [5,9,11,14]] = [[1.0,4], [5,9,11,14]]", "r":[[1.0,4], [5,9,11,14]] = [[1.0,4], [5,9,11,14]]},
                    "t20": {"c":"[['white','yellow','brown'], 6] != [['white','yellow','brown'], 6]", "r":[["white","yellow","brown"], 6] != [["white","yellow","brown"], 6]},
                    "t21": {"c":"[ [[1,2,3], 'gold', ['sql++', 5]], [4, 5], 2] > [ [[1,2,3], 'gold', ['sql++', 5]], [4, 5], 0.2]", "r":[ [[1,2,3], 'gold', ['sql++', 5]], [4, 5], 2] > [ [[1,2,3], 'gold', ['sql++', 5]], [4, 5], 0.2]},
                    "t22": {"c":"[5, [8,1], [[0, 4], 'b']] > [5, [8,1], [[0, 4], 'a', 'c']]", "r":[5, [8,1], [[0, 4], 'b']] > [5, [8,1], [[0, 4], 'a', 'c']]},
                    "t23": {"c":"[[1, null], 9] = [[1, 2], 9]", "r":[[1, null], 9] = [[1, 2], 9]},
                    "t24": {"c":"[[1, null], 9] < [[1, 2], 9]", "r":[[1, null], 9] < [[1, 2], 9]},
                    "t25": {"c":"[[1, null], 9] < [[1, 2], 99]", "r":[[1, null], 9] < [[1, 2], 99]},
                    "t26": {"c":"[[1, null], 9] > [[1, 2], 9]", "r":[[1, null], 9] > [[1, 2], 9]},
                    "t27": {"c":"[[1, null], 9] > [[1, 2], 99]", "r":[[1, null], 9] > [[1, 2], 99]},
                    "t28": {"c": "['a','b','c'] = ['a','b','c']", "r": ['a','b','c'] = ['a','b','c']},
                    "t29": {"c": "['A','b','c'] = ['a','b','c']", "r": ['A','b','c'] = ['a','b','c']},
                    "t30": {"c": "['a','b','c'] < ['a','b','d']", "r": ['a','b','c'] < ['a','b','d']},
                    "t31": {"c": "['blue', 'black', 'orange'] < ['purple', 'green']", "r": ['blue', 'black', 'orange'] < ['purple', 'green']},
                    "t32": {"c": "['blue', 'black', 'orange'] > ['purple', 'green']", "r": ['blue', 'black', 'orange'] > ['purple', 'green']},
                    "t33": {"c": "['blue', 'black', 'orange'] >= ['blue', 'black', 'orange']", "r": ['blue', 'black', 'orange'] >= ['blue', 'black', 'orange']},
                    "t34": {"c": "[true] > [false]", "r": [true] > [false]},
                    "t35": {"c": "[true, false, true] = [true, false, true]", "r": [true, false, true] = [true, false, true]},
                    "t36": {"c": "[true, false, false] >= [true, true]", "r": [true, false, false] >= [true, true]},
                    "t37":  {"c": "[1,2] = [1,2]", "r": [1,2] = [1,2]},
                    "t38":  {"c": "[1,2] < [1,2]", "r": [1,2] < [1,2]},
                    "t39":  {"c": "[1,2] <= [1,2]", "r": [1,2] <= [1,2]},
                    "t40":  {"c": "[1,2] >= [1,2]", "r": [1,2] >= [1,2]},
                    "t41":  {"c": "[1,2] > [1,2]", "r": [1,2] > [1,2]},
                    "t42":  {"c": "[1,2] != [1,2]", "r": [1,2] != [1,2]},
                    "t43":  {"c": "[2,1] = [1,2]", "r": [2,1] = [1,2]},
                    "t44":  {"c": "[2,1] < [1,2]", "r": [2,1] < [1,2]},
                    "t45":  {"c": "[2,1] <= [1,2]", "r": [2,1] <= [1,2]},
                    "t46":  {"c": "[2,1] >= [1,2]", "r": [2,1] >= [1,2]},
                    "t47":  {"c": "[2,1] > [1,2]", "r": [2,1] > [1,2]},
                    "t48":  {"c": "[2,1] != [1,2]", "r": [2,1] != [1,2]},
                    "t49":  {"c": "[1,2,3] = [1,2]", "r": [1,2,3] = [1,2]},
                    "t50":  {"c": "[1,2,3] < [1,2]", "r": [1,2,3] < [1,2]},
                    "t51":  {"c": "[1,2,3] <= [1,2]", "r": [1,2,3] <= [1,2]},
                    "t52":  {"c": "[1,2,3] >= [1,2]", "r": [1,2,3] >= [1,2]},
                    "t53":  {"c": "[1,2,3] > [1,2]", "r": [1,2,3] > [1,2]},
                    "t54":  {"c": "[1,2,3] != [1,2]", "r": [1,2,3] != [1,2]},
                    "t55":  {"c": "[2,1,3] = [1,2]", "r": [2,1,3] = [1,2]},
                    "t56":  {"c": "[2,1,3] < [1,2]", "r": [2,1,3] < [1,2]},
                    "t57":  {"c": "[2,1,3] <= [1,2]", "r": [2,1,3] <= [1,2]},
                    "t58":  {"c": "[2,1,3] >= [1,2]", "r": [2,1,3] >= [1,2]},
                    "t59":  {"c": "[2,1,3] > [1,2]", "r": [2,1,3] > [1,2]},
                    "t60":  {"c": "[2,1,3] != [1,2]", "r": [2,1,3] != [1,2]},
                    "t61":  {"c": "[1,2] = [1,2,3]", "r": [1,2] = [1,2,3]},
                    "t62":  {"c": "[1,2] < [1,2,3]", "r": [1,2] < [1,2,3]},
                    "t63":  {"c": "[1,2] <= [1,2,3]", "r": [1,2] <= [1,2,3]},
                    "t64":  {"c": "[1,2] >= [1,2,3]", "r": [1,2] >= [1,2,3]},
                    "t65":  {"c": "[1,2] > [1,2,3]", "r": [1,2] > [1,2,3]},
                    "t66":  {"c": "[1,2] != [1,2,3]", "r": [1,2] != [1,2,3]},
                    "t67":  {"c": "[1,2,3,4,5,6] = [1,2,3,4,5,6]", "r": [1,2,3,4,5,6] = [1,2,3,4,5,6]},
                    "t68":  {"c": "[1,2,3,4,5,5] = [1,2,3,4,5,6]", "r": [1,2,3,4,5,5] = [1,2,3,4,5,6]},
                    "t69": {"c":"[23, 2] = [23,2]", "r":[23, 2] = [23, 2]},
                    "t70": {"c":"['black', 4, 3.3] > ['black', 4]", "r":['black', 4, 3.3] > ['black', 4]},
                    "t71": {"c":"[] = []", "r":[] = []},
                    "t72": {"c":"[] != []", "r":[] != []},
                    "t73": {"c":"[] > []", "r":[] > []},
                    "t74": {"c":"[] < []", "r":[] < []},
                    "t75": {"c":"[] < [1,3]", "r":[] < [1,3]},
                    "t76": {"c":"[] > [1,3]", "r":[] > [1,3]}
                    }) v SELECT *
                    ORDER BY v.c"""
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = sql_query
        n1ql_response = self.rest.query_tool(sql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

    def test_deep_comparision_on_objects(self):

        self.log.info('Execute query on SQL++')
        sql_query = """FROM OBJECT_VALUES(
                    {
                    "t1": {"c": "{'name': 'john', 'id': 231} = {'name': 'john', 'id': 231}", "r": {'name': 'john', 'id': 231} = {'name': 'john', 'id': 231}},
                    "t2": {"c": "{'name': 'john', 'id': 231} != {'name': 'john', 'id': 231}", "r": {'name': 'john', 'id': 231} != {'name': 'john', 'id': 231}},
                    "t3": {"c": "{'name': 'david', 'id': 34.2} = {'id': 34.2, 'name': 'david'}", "r": {'name': 'david', 'id': 34.2} = {'id': 34.2, 'name': 'david'}},
                    "t4": {"c": "{'name': 'david', 'id': 34.2} != {'id': 34.2, 'name': 'david'}", "r": {'name': 'david', 'id': 34.2} != {'id': 34.2, 'name': 'david'}},
                    "t5": {"c": "{'name': 'henry', 'id': 111} = {'name': 'henry'}", "r": {'name': 'henry', 'id': 111} = {'name': 'henry'}},
                    "t6": {"c": "{'a': 1, 'b': 2} = {'c': 3, 'd': 4}", "r": {'a': 1, 'b': 2} = {'c': 3, 'd': 4}},
                    "t7": {"c": "{'aa': 11, 'bb': 22} = {'bb': 22, 'cc': 33}", "r": {'aa': 11, 'bb': 22} = {'bb': 22, 'cc': 33}},
                    "t8": {"c": "{'aa': 33, 'bb': missing} != {'aa': 33}", "r": {'aa': 33, 'bb': missing} != {'aa': 33}},
                    "t9": {"c": "{'bb': missing, 'a_a': 9} = {'a_a': 9}", "r": {'bb': missing, 'a_a': 9} = {'a_a': 9}},
                    "t10": {"c": "{'kk': missing, 'aa': 22, 'jj': 'foo'} = {'jj': 'foo', 'dd': missing, 'aa': 22}", "r": {'kk': missing, 'aa': 22, 'jj': 'foo'} = {'jj': 'foo', 'dd': missing, 'aa': 22}},
                    "t11": {
                      "c": "{'dept_ids': [3,1,5], 'manager': {'name': 'mike', 'id': 987}, 'salary': 32.2, 'employees': [{'name': 'seth', 'id': 22}, {'name': 'dave'}]} = {'salary': 32.2, 'dept_ids': [3,1,5], 'employees': [{'name': 'seth', 'id': 22}, {'name': 'dave'}], 'manager': {'name': 'mike', 'id': 987}}",
                      "r": {'dept_ids': [3,1,5], 'manager': {'name': 'mike', 'id': 987}, 'salary': 32.2, 'employees': [{'name': 'seth', 'id': 22}, {'name': 'dave'}]} = {'salary': 32.2, 'dept_ids': [3,1,5], 'employees': [{'name': 'seth', 'id': 22}, {'name': 'dave'}], 'manager': {'name': 'mike', 'id': 987}}
                      },
                    "t12": {"c": "{'f1': [5,6,1], 'f2': [9,2,8]} != {'f1': [5,6,1], 'f2': [8,9,2]}", "r": {'f1': [5,6,1], 'f2': [9,2,8]} != {'f1': [5,6,1], 'f2': [8,9,2]}},
                    "t13": {"c": "{'f1': 44, 'f2': 99} = {'f2': 44, 'f1': 99}", "r": {'f1': 44, 'f2': 99} = {'f2': 44, 'f1': 99}},
                    "t14": {"c": "{'f1': 33, 'F2': 77} = {'f1': 33, 'f2': 77}", "r": {'f1': 33, 'F2': 77} = {'f1': 33, 'f2': 77}},
                    "t15": {"c": "{'f1': 12, 'f2': 34, 'F2': 56} = {'f1': 12, 'F2': 56, 'f2': 34}", "r": {'f1': 12, 'f2': 34, 'F2': 56} = {'f1': 12, 'F2': 56, 'f2': 34}},
                    "t16": {"c": "{} = {}", "r": {} = {}},
                    "t17": {"c": "{'a': missing, 'c': missing} = {'b': missing}", "r": {'a': missing, 'c': missing} = {'b': missing}},
                    "t18": {"c": "{'a': 22, 'b': 'john'} != {}", "r": {'a': 22, 'b': 'john'} != {}},
                    "t19": {"c": "{} != {'a': 22, 'b': 'john'}", "r": {} != {'a': 22, 'b': 'john'}},
                    "t20": {"c": "{'yy': 5, 'zz': 8} = {'yy': 5, 'zz': 8}", "r": {'yy': 5, 'zz': 8} = {'yy': 5, 'zz': 8}},
                    "t21": {"c": "{'f1': [4, [5.4, {'id': 33, 'dept': 11}, {'label': 'foo', 'a': 3}], {'a1': 7, 'z1': 2}, 'str'], 'f2': 3, 'f3': {'n1': {'nn1': {'a': 9, 'b': 10}, 'nn2': {'a': 99, 'x': 14}}, 'n2': {'a': 3, 'b': 5}} } = {'f1': [4, [5.4, {'id': 33, 'dept': 11}, {'a': 3, 'label': 'foo'}], {'a1': 7, 'z1': 2}, 'str'], 'f3': {'n1': {'nn1': {'a': 9, 'b': 10}, 'nn2': {'a': 99, 'x': 14}}, 'n2': {'a': 3, 'b': 5}},'f2': 3 }","r": {'f1': [4, [5.4, {'id': 33, 'dept': 11}, {'label': 'foo', 'a': 3}], {'a1': 7, 'z1': 2}, 'str'], 'f2': 3, 'f3': {'n1': {'nn1': {'a': 9, 'b': 10}, 'nn2': {'a': 99, 'x': 14}}, 'n2': {'a': 3, 'b': 5}} } = {'f1': [4, [5.4, {'id': 33, 'dept': 11}, {'a': 3, 'label': 'foo'}], {'a1': 7, 'z1': 2}, 'str'], 'f3': {'n1': {'nn1': {'a': 9, 'b': 10}, 'nn2': {'a': 99, 'x': 14}}, 'n2': {'a': 3, 'b': 5}},'f2': 3 } },
                    "t22": { "c": "{'a': 2, 'b': missing} = {'a': 2, 'b': 3}", "r": {'a': 2, 'b': missing} = {'a': 2, 'b': 3} }
                    }) v SELECT *
                    ORDER BY v.c"""
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = sql_query
        n1ql_response = self.rest.query_tool(sql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

    def test_deep_comparision_where_clause(self):

        self.log.info("Load Beer-Sample bucket")
        self.assertTrue(
            self.load_sample_buckets(
                servers=[self.master], bucketName=self.cb_bucket_name, 
                total_items=self.travel_sample_total_docs_count), 
            msg="Failed to load Travel-Sample, item count mismatch")

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.beer_sample_docs_count)

        self.log.info('Verify deep comparision using where clause on object')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT meta().id FROM `%s` WHERE geo = { "alt": 12, "lat": 50.962097, "lon": 1.954764 }' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT meta().id FROM `%s` WHERE geo = { "alt": 12, "lat": 50.962097, "lon": 1.954764 }' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

        self.log.info('Verify deep comparision using where clause on array')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT meta().id FROM `%s` WHERE public_likes = ["Dortha Hermiston","Harrison Harvey"]' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT meta().id FROM `%s` WHERE public_likes = ["Dortha Hermiston","Harrison Harvey"];' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

    def test_deep_comparision_sort(self):

        self.log.info('Load travel-sample bucket')
        self.assertTrue(
            self.load_sample_buckets(
                servers=[self.master], bucketName=self.cb_bucket_name, 
                total_items=self.travel_sample_total_docs_count), 
            msg="Failed to load Travel-Sample, item count mismatch")

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.travel_sample_docs_count)

        self.log.info('Verify sort by record')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT VALUE v FROM %s ORDER BY v.geo DESC' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT VALUE v FROM `%s` ORDER BY v.geo DESC' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

        self.log.info('Verify sort by array')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT VALUE v FROM %s ORDER BY v.public_likes' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT VALUE v FROM `%s` ORDER BY v.public_likes' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

    def test_deep_comparision_group_by(self):

        self.log.info('Load travel-sample bucket')
        self.assertTrue(
            self.load_sample_buckets(
                servers=[self.master], bucketName=self.cb_bucket_name, 
                total_items=self.travel_sample_total_docs_count), 
            msg="Failed to load Travel-Sample, item count mismatch")

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.travel_sample_docs_count)

        self.log.info('Verify group by record')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT v.geo, COUNT(v) FROM `%s` v GROUP BY v.geo HAVING COUNT(v) > 1 ORDER BY v.geo ASC' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT v.geo, COUNT(v) FROM `%s` v GROUP BY v.geo HAVING COUNT(v) > 1 ORDER BY v.geo ASC' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

        self.log.info('Verify group by record using hashing')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT v.geo, COUNT(v) FROM `%s` v /*+ hash */ GROUP BY v.geo HAVING COUNT(v) > 1 ORDER BY v.geo ASC' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))
        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

        self.log.info('Verify group by array')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT g.cities, COUNT(*) FROM (SELECT VALUE OBJECT_PUT(v, "cities", [v.country, v.city]) FROM `%s` v WHERE v.city IS NOT NULL) g GROUP BY g.cities ORDER BY g.cities ASC' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT g.cities, COUNT(*) FROM (SELECT VALUE OBJECT_PUT(v, "cities", [v.country, v.city]) FROM `%s` v WHERE v.city IS NOT NULL) g GROUP BY g.cities ORDER BY g.cities ASC' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

        self.log.info('Verify group by array using hashing')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT g.cities, COUNT(*) FROM (SELECT VALUE OBJECT_PUT(v, "cities", [v.country, v.city]) FROM `%s` v WHERE v.city IS NOT NULL) g /*+ hash */ GROUP BY g.cities ORDER BY g.cities ASC' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))
        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

    def test_deep_comparision_join(self):

        self.log.info('Load travel-sample bucket')
        self.assertTrue(
            self.load_sample_buckets(
                servers=[self.master], bucketName=self.cb_bucket_name, 
                total_items=self.travel_sample_total_docs_count), 
            msg="Failed to load Travel-Sample, item count mismatch")

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.travel_sample_docs_count)

        self.log.info('Verify join by record')
        self.log.info('Execute query on SQL++')
        sql_query = 'FROM `%s` ds1 JOIN `%s` ds2 ON ds1.geo = ds2.geo SELECT meta(ds1).id ORDER BY meta(ds1).id ASC' % (self.cbas_dataset_name, self.cbas_dataset_name)
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(
            sql_query, timeout=300, analytics_timeout=300)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Creating index on N1QL')
        n1ql_query = 'CREATE INDEX geo_index ON `%s`(geo);' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT meta(ds1).id FROM `%s` ds1 JOIN `%s` ds2 ON ds1.geo = ds2.geo ORDER BY meta(ds1).id ASC' % (self.cb_bucket_name, self.cb_bucket_name)
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

        self.log.info('Verify join by array')
        self.log.info('Execute query on SQL++')
        sql_query = 'FROM `%s` ds1 JOIN `%s` ds2 ON ds1.public_likes = ds2.public_likes SELECT meta(ds1).id ORDER BY meta(ds1).id ASC' % (self.cbas_dataset_name, self.cbas_dataset_name)
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(
            sql_query, timeout=300, analytics_timeout=300)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Creating index on N1QL')
        n1ql_query = 'CREATE INDEX likes_index ON `%s`(public_likes)' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT meta(ds1).id FROM `%s` ds1 JOIN `%s` ds2 ON ds1.public_likes = ds2.public_likes ORDER BY meta(ds1).id ASC' % (self.cb_bucket_name, self.cb_bucket_name)
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

    def test_deep_comparision_distinct(self):

        self.log.info('Load travel-sample bucket')
        self.assertTrue(
            self.load_sample_buckets(
                servers=[self.master], bucketName=self.cb_bucket_name, 
                total_items=self.travel_sample_total_docs_count), 
            msg="Failed to load Travel-Sample, item count mismatch")

        self.log.info("Create connection")
        self.cbas_util.createConn(self.cb_bucket_name)

        self.log.info('Create dataset')
        self.cbas_util.create_dataset_on_bucket(self.cb_bucket_name, self.cbas_dataset_name)

        self.log.info('Connect link')
        self.cbas_util.connect_link()

        self.log.info('Verify dataset count')
        self.cbas_util.validate_cbas_dataset_items_count(self.cbas_dataset_name, self.travel_sample_docs_count)

        self.log.info('Verify distinct on record')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT DISTINCT VALUE v.geo FROM `%s` v ORDER BY v.geo' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT DISTINCT VALUE v.geo FROM `%s` v ORDER BY v.geo' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

        self.log.info('Verify distinct on array')
        self.log.info('Execute query on SQL++')
        sql_query = 'SELECT distinct value g.cities FROM (SELECT VALUE OBJECT_PUT(v, "cities", [v.country, v.city]) FROM `%s` v WHERE v.city IS NOT NULL) g ORDER BY g.cities ASC' % self.cbas_dataset_name
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))

        self.log.info('Execute query on N1QL')
        n1ql_query = 'SELECT distinct value g.cities FROM (SELECT VALUE OBJECT_PUT(v, "cities", [v.country, v.city]) FROM `%s` v WHERE v.city IS NOT NULL) g ORDER BY g.cities ASC;' % self.cb_bucket_name
        n1ql_response = self.rest.query_tool(n1ql_query)
        n1ql_status = n1ql_response['status']
        n1ql_result = n1ql_response['results']
        self.assertEqual(n1ql_status, "success", "Query %s failed. Actual: %s, Expected:%s" % (n1ql_query, n1ql_status, 'success'))

        self.log.info('Compare n1ql and sql++ query result')
        self.assertEqual(n1ql_result, sql_result, "Result mismatch. Actual: %s, Expected:%s" % (n1ql_result, sql_result))

    def test_deep_comparision_sqlpp_undefined(self):
        self.log.info('Execute query on SQL++')
        sql_query = """FROM OBJECT_VALUES(
                    {
                    "t1": {"c":"[['white','yellow','brown'], 6] != [6, ['white','yellow','brown']]", "r":[["white","yellow","brown"], 6] != [6, ["white","yellow","brown"]]},
                    "t2": {"c":"[[[1,2], 99], 77] <= [[['flute',2], 99], 77]", "r":[[[1,2], 99], 77] <= [[['flute',2], 99], 77]},
                    "t3": {"c":"[[[1,2], 99], 77] <= [[[missing,2], 99], 77]", "r":[[[1,2], 99], 77] <= [[[missing,2], 99], 77]},
                    "t4": {"c":"[[1, null], 9] = [[1, 2], 99]", "r":[[1, null], 9] = [[1, 2], 99]},
                    "t5": {"c":"{'id':99, 'name':'sam'} != [99, 'sam']", "r": {"id":99, "name":"sam"} != [99, 'sam']},
                    "t6": {"c":"[[1, 'string'], 9] = [[1, 2], 9]", "r":[[1, 'string'], 9] = [[1, 2], 9]},
                    "t7": {"c":"[[1, 'string'], 9] = [[1, 2], 99]", "r":[[1, 'string'], 9] = [[1, 2], 99]},
                    "t8": {"c":"[[1, 'string'], 9] < [[1, 2], 9]", "r":[[1, 'string'], 9] < [[1, 2], 9]},
                    "t9": {"c":"[[1, 'string'], 9] < [[1, 2], 99]", "r":[[1, 'string'], 9] < [[1, 2], 99]},
                    "t10": {"c":"[[1, 'string'], 9] > [[1, 2], 9]", "r":[[1, 'string'], 9] > [[1, 2], 9]},
                    "t11": {"c":"[[1, 'string'], 9] > [[1, 2], 99]", "r":[[1, 'string'], 9] > [[1, 2], 99]},
                    "t12": {"c":"[missing,2] < [null,3]", "r":[missing,2] < [null,3]},
                    "t13": {"c":"[null,1] = [1,1,3]", "r":[null,1] = [1,1,3]},
                    "t14": {"c":"[1,2,missing] != [1,2,missing]", "r":[1,2,missing] != [1,2,missing]},
                    "t15": {"c":"[null,1] != [1,1,3]", "r":[null,1] != [1,1,3]},
                    "t16": {"c":"[missing, missing] = [missing, missing]", "r": [missing, missing] = [missing, missing]},
                    "t17": {"c":"[99, null, 3] = [1, 2, 3]", "r":[99, null, 3] = [1, 2, 3]},
                    "t18": {"c":"[1, missing, 3] = [1, 2, 3]", "r":[1, missing, 3] = [1, 2, 3]},
                    "t19": {"c":"[1, null, missing, 4] = [1, 2, 3, 4]", "r":[1, null, missing, 4] = [1, 2, 3, 4]},
                    "t20": {"c":"[1, null, missing, null, 5] = [1, 2, 3, 4, 5]", "r":[1, null, missing, null, 5] = [1, 2, 3, 4, 5]},
                    "t21": {"c":"[1, missing, null, missing, 5] = [1, 2, 3, 4, 5]", "r":[1, missing, null, missing, 5] = [1, 2, 3, 4, 5]},
                    "t22": {"c":"[1, null, 3] = [1, 2, 99]", "r":[1, null, 3] = [1, 2, 99]},
                    "t23": {"c":"[1, missing, 3] = [1, 2, 99]", "r":[1, missing, 3] = [1, 2, 99]},
                    "t24": {"c":"[1, null, missing, 4] = [1, 2, 3, 99]", "r":[1, null, missing, 4] = [1, 2, 3, 99]},
                    "t25": {"c":"[1, null, missing, null, 5] = [1, 2, 3, 4, 99]", "r":[1, null, missing, null, 5] = [1, 2, 3, 4, 99]},
                    "t26": {"c":"[1, missing, null, missing, 5] = [1, 2, 3, 4, 99]", "r":[1, missing, null, missing, 5] = [1, 2, 3, 4, 99]},
                    "t27": {"c":"[1, missing, 3] != [1, 2, 3]", "r":[1, missing, 3] != [1, 2, 3]},
                    "t28": {"c":"[1, null, missing, 4] != [1, 2, 3, 4]", "r":[1, null, missing, 4] != [1, 2, 3, 4]},
                    "t29": {"c":"[1, null, 3] != [1, 2, 99]", "r":[1, null, 3] != [1, 2, 99]},
                    "t30": {"c":"[1, missing, 3] != [1, 2, 99]", "r":[1, missing, 3] != [1, 2, 99]},
                    "t31": {"c":"[1, null, missing, 4] != [1, 2, 3, 99]", "r":[1, null, missing, 4] != [1, 2, 3, 99]},
                    "t32": {"c":"[1, missing, 3] < [1, 2, 3]", "r":[1, missing, 3] < [1, 2, 3]},
                    "t33": {"c":"[1, missing, null, 4] < [1, 2, 3, 4]", "r":[1, missing, null, 4] < [1, 2, 3, 4]},
                    "t34": {"c":"[1, missing, 3] < [1, 2, 99]", "r":[1, missing, 3] < [1, 2, 99]},
                    "t35": {"c":"[1, missing, 99] < [1, 2, 3]", "r":[1, missing, 99] < [1, 2, 3]},
                    "t36": {"c":"[99, null, 3] < [1, 2, 3]", "r":[99, null, 3] < [1, 2, 3]},
                    "t37": {"c":"[-99, null, 3] < [1, 2, 3]", "r":[-99, null, 3] < [1, 2, 3]},
                    "t38": {"c":"[99, null, 3] >= [1, 2, 3]", "r":[99, null, 3] >= [1, 2, 3]},
                    "t39": {"c":"[-99, null, 3] >= [1, 2, 3]", "r":[-99, null, 3] >= [1, 2, 3]}
                    }) v SELECT VALUE v.r
                    ORDER BY v.c"""
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))
        expected_result = json.loads("[null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null,null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null]")
        self.log.info('Compare sql++ query result to expected result')
        self.assertEqual(sql_result, expected_result, "Result mismatch. Actual: %s, Expected:%s" % (sql_result, expected_result))

        self.log.info('Execute query on SQL++')
        sql_query = """FROM OBJECT_VALUES(
                        {
                        "t1": { "c": "{'a': 2, 'b': 4} < {'a': 88, 'b': 99}", "r":{'a': 2, 'b': 4} < {'a': 88, 'b': 99} },
                        "t2": { "c": "[99, {'id': 33, 'a': 'z'}] < [1, {'id': 44, 'a': 'x'}]", "r": [99, {'id': 33, 'a': 'z'}] < [1, {'id': 44, 'a': 'x'}] },
                        "t3": { "c": "{'a': 3, 'j': 6} = {'m': 2, 'a': 'str'}", "r": {'a': 3, 'j': 6} = {'m': 2, 'a': 'str'} },
                        "t4": { "c": "{'list': [1,2,4], 'f': 4} != {'f': 3, 'list': [1,'str']}", "r": {'list': [1,2,4], 'f': 4} != {'f': 3, 'list': [1,'str']} },
                        "t5": { "c": "{'a': 2, 'b': null} = {'a': 2, 'b': 3}", "r": {'a': 2, 'b': null} = {'a': 2, 'b': 3} },
                        "t6": { "c": "{'list': [1, null], 'f': 3} = {'f': 3, 'list': [1, 2]}", "r": {'list': [1, null], 'f': 3} = {'f': 3, 'list': [1, 2]}},
                        "t7": { "c": "{'list': [1, missing], 'f': 3} = {'f': 3, 'list': [1, 2]}", "r": {'list': [1, missing], 'f': 3} = {'f': 3, 'list': [1, 2]}},
                        "t8": { "c": "{'a': 4, 'b': null} = {'a': 2, 'b': 3}", "r": {'a': 4, 'b': null} = {'a': 2, 'b': 3} }
                        }) v SELECT VALUE v.r
                        ORDER BY v.c;"""
        sql_status, _, _, sql_result, _ = self.cbas_util.execute_statement_on_cbas_util(sql_query)
        self.assertEqual(sql_status, "success", "SQL++ Query %s failed. Actual: %s, Expected:%s" % (sql_query, sql_status, 'success'))
        expected_result = json.loads("[null, null, null, null, null, null, null, null]")
        self.log.info('Compare sql++ query result to expected result')
        self.assertEqual(sql_result, expected_result, "Result mismatch. Actual: %s, Expected:%s" % (sql_result, expected_result))

    def tearDown(self):
        super(DeepComparison, self).tearDown()
