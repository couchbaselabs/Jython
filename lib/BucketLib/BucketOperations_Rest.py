'''
Created on Sep 25, 2017

@author: riteshagarwal
'''

import json
import time
import urllib
from bucket import *
from membase.api.exception import BucketCreationException, GetBucketInfoFailed, BucketFlushFailed, BucketCompactionException
from membase.api.rest_client import Node
from memcached.helper.kvstore import KVStore
from Rest_Connection import RestConnection
import logger

log = logger.Logger.get_logger()

class BucketHelper(RestConnection):

    def __init__(self, server):
        super(BucketHelper, self).__init__(server)
    
    def bucket_exists(self, bucket):
        try:
            buckets = self.get_buckets()
            names = [item.name for item in buckets]
            log.info("node {1} existing buckets : {0}" \
                              .format(names, self.ip))
            for item in buckets:
                if item.name == bucket:
                    log.info("node {1} found bucket {0}" \
                             .format(bucket, self.ip))
                    return True
            return False
        except Exception:
            return False
    
    def get_buckets(self):
        # get all the buckets
        buckets = []
        api = '{0}{1}'.format(self.baseUrl, 'pools/default/buckets?basic_stats=true')
        status, content, header = self._http_request(api)
        json_parsed = json.loads(content)
        if status:
            for item in json_parsed:
                bucketInfo = RestParser().parse_get_bucket_json(item)
                buckets.append(bucketInfo)
        return buckets
    
    def vbucket_map_ready(self, bucket, timeout_in_seconds=360):
        end_time = time.time() + timeout_in_seconds
        while time.time() <= end_time:
            vBuckets = self.get_vbuckets(bucket)
            if vBuckets:
                return True
            else:
                time.sleep(0.5)
        msg = 'vbucket map is not ready for bucket {0} after waiting {1} seconds'
        log.info(msg.format(bucket, timeout_in_seconds))
        return False
    
    def _get_vbuckets(self, servers, bucket_name='default'):
        vbuckets_servers = {}
        for server in servers:
            buckets = self.get_buckets()
            if not buckets:
                return vbuckets_servers
            if bucket_name:
                bucket_to_check = [bucket for bucket in buckets
                               if bucket.name == bucket_name][0]
            else:
                bucket_to_check = [bucket for bucket in buckets][0]
            vbuckets_servers[server] = {}
            vbs_active = [vb.id for vb in bucket_to_check.vbuckets
                           if vb.master.startswith(str(server.ip))]
            vbs_replica = []
            for replica_num in xrange(0, bucket_to_check.numReplicas):
                vbs_replica.extend([vb.id for vb in bucket_to_check.vbuckets
                                    if vb.replica[replica_num].startswith(str(server.ip))])
            vbuckets_servers[server]['active_vb'] = vbs_active
            vbuckets_servers[server]['replica_vb'] = vbs_replica
        return vbuckets_servers
    
    def fetch_vbucket_map(self, bucket="default"):
        """Return vbucket map for bucket
        Keyword argument:
        bucket -- bucket name
        """
        api = self.baseUrl + 'pools/default/buckets/' + bucket
        status, content, header = self._http_request(api)
        _stats = json.loads(content)
        return _stats['vBucketServerMap']['vBucketMap']

    def get_vbucket_map_and_server_list(self, bucket="default"):
        """ Return server list, replica and vbuckets map
        that matches to server list """
        vbucket_map = self.fetch_vbucket_map(bucket)
        api = self.baseUrl + 'pools/default/buckets/' + bucket
        status, content, header = self._http_request(api)
        _stats = json.loads(content)
        num_replica = _stats['vBucketServerMap']['numReplicas']
        vbucket_map = _stats['vBucketServerMap']['vBucketMap']
        servers = _stats['vBucketServerMap']['serverList']
        server_list = []
        for node in servers:
            node = node.split(":")
            server_list.append(node[0])
        return vbucket_map, server_list, num_replica
    
    def get_buckets_itemCount(self):
        # get all the buckets
        bucket_map = {}
        api = '{0}{1}'.format(self.baseUrl, 'pools/default/buckets?basic_stats=true')
        status, content, header = self._http_request(api)
        json_parsed = json.loads(content)
        if status:
            for item in json_parsed:
                bucketInfo = RestParser().parse_get_bucket_json(item)
                bucket_map[bucketInfo.name] = bucketInfo.stats.itemCount
        log.info(bucket_map)
        return bucket_map

    def get_bucket_stats_for_node(self, bucket='default', node=None):
        if not node:
            log.error('node_ip not specified')
            return None
        stats = {}
        api = "{0}{1}{2}{3}{4}:{5}{6}".format(self.baseUrl, 'pools/default/buckets/',
                                     bucket, "/nodes/", node.ip, node.port, "/stats")
        status, content, header = self._http_request(api)
        if status:
            json_parsed = json.loads(content)
            op = json_parsed["op"]
            samples = op["samples"]
            for stat_name in samples:
                if stat_name not in stats:
                    if len(samples[stat_name]) == 0:
                        stats[stat_name] = []
                    else:
                        stats[stat_name] = samples[stat_name][-1]
                else:
                    raise Exception("Duplicate entry in the stats command {0}".format(stat_name))
        return stats

    def get_bucket_status(self, bucket):
        if not bucket:
            log.error("Bucket Name not Specified")
            return None
        api = self.baseUrl + 'pools/default/buckets'
        status, content, header = self._http_request(api)
        if status:
            json_parsed = json.loads(content)
            for item in json_parsed:
                if item["name"] == bucket:
                    return item["nodes"][0]["status"]
            log.error("Bucket {} doesn't exist".format(bucket))
            return None

    def fetch_bucket_stats(self, bucket='default', zoom='minute'):
        """Return deserialized buckets stats.
        Keyword argument:
        bucket -- bucket name
        zoom -- stats zoom level (minute | hour | day | week | month | year)
        """
        api = self.baseUrl + 'pools/default/buckets/{0}/stats?zoom={1}'.format(bucket, zoom)
        log.info(api)
        status, content, header = self._http_request(api)
        return json.loads(content)

    def fetch_bucket_xdcr_stats(self, bucket='default', zoom='minute'):
        """Return deserialized bucket xdcr stats.
        Keyword argument:
        bucket -- bucket name
        zoom -- stats zoom level (minute | hour | day | week | month | year)
        """
        api = self.baseUrl + 'pools/default/buckets/@xdcr-{0}/stats?zoom={1}'.format(bucket, zoom)
        status, content, header = self._http_request(api)
        return json.loads(content)

    def get_bucket_stats(self, bucket='default'):
        stats = {}
        status, json_parsed = self.get_bucket_stats_json(bucket)
        if status:
            op = json_parsed["op"]
            samples = op["samples"]
            for stat_name in samples:
                if samples[stat_name]:
                    last_sample = len(samples[stat_name]) - 1
                    if last_sample:
                        stats[stat_name] = samples[stat_name][last_sample]
        return stats

    def get_bucket_stats_json(self, bucket='default'):
        stats = {}
        api = "{0}{1}{2}{3}".format(self.baseUrl, 'pools/default/buckets/', bucket, "/stats")
        if isinstance(bucket, Bucket):
            api = '{0}{1}{2}{3}'.format(self.baseUrl, 'pools/default/buckets/', bucket.name, "/stats")
        status, content, header = self._http_request(api)
        json_parsed = json.loads(content)
        return status, json_parsed

    def get_bucket_json(self, bucket='default'):
        api = '{0}{1}{2}'.format(self.baseUrl, 'pools/default/buckets/', bucket)
        if isinstance(bucket, Bucket):
            api = '{0}{1}{2}'.format(self.baseUrl, 'pools/default/buckets/', bucket.name)
        status, content, header = self._http_request(api)
        if not status:
            raise GetBucketInfoFailed(bucket, content)
        return json.loads(content)

    def is_lww_enabled(self, bucket='default'):
        bucket_info = self.get_bucket_json(bucket=bucket)
        try:
            if bucket_info['conflictResolutionType'] == 'lww':
                return True
        except KeyError:
            return False

    def get_bucket(self, bucket='default', num_attempt=1, timeout=1):
        bucketInfo = None
        api = '%s%s%s?basic_stats=true' % (self.baseUrl, 'pools/default/buckets/', bucket)
        if isinstance(bucket, Bucket):
            api = '%s%s%s?basic_stats=true' % (self.baseUrl, 'pools/default/buckets/', bucket.name)
        status, content, header = self._http_request(api)
        num = 1
        while not status and num_attempt > num:
            log.error("try to get {0} again after {1} sec".format(api, timeout))
            time.sleep(timeout)
            status, content, header = self._http_request(api)
            num += 1
        if status:
            bucketInfo = RestParser().parse_get_bucket_response(content)
        return bucketInfo

    def get_vbuckets(self, bucket='default'):
        b = self.get_bucket(bucket)
        return None if not b else b.vbuckets

    def delete_bucket(self, bucket='default'):
        api = '%s%s%s' % (self.baseUrl, 'pools/default/buckets/', bucket)
        if isinstance(bucket, Bucket):
            api = '%s%s%s' % (self.baseUrl, 'pools/default/buckets/', bucket.name)
        status, content, header = self._http_request(api, 'DELETE')

        if int(header['status']) == 500:
            # According to http://docs.couchbase.com/couchbase-manual-2.5/cb-rest-api/#deleting-buckets
            # the cluster will return with 500 if it failed to nuke
            # the bucket on all of the nodes within 30 secs
            log.warn("Bucket deletion timed out waiting for all nodes")

        return status

    '''Load any of the three sample buckets'''
    def load_sample(self,sample_name):
        api = '{0}{1}'.format(self.baseUrl, "sampleBuckets/install")
        data = '["{0}"]'.format(sample_name)
        status, content, header = self._http_request(api, 'POST', data)
        # Sleep to allow the sample bucket to be loaded
        time.sleep(10)
        return status

    # figure out the proxy port
    
    def create_bucket(self, bucket='',
                      ramQuotaMB=1,
                      replicaNumber=1,
                      proxyPort=11211,
                      bucketType='membase',
                      replica_index=1,
                      threadsNumber=3,
                      flushEnabled=1,
                      evictionPolicy='valueOnly',
                      lww=False,
                      maxTTL=None,
                      compressionMode='passive',
                      storageBackend="couchstore"):


        api = '{0}{1}'.format(self.baseUrl, 'pools/default/buckets')
        params = urllib.urlencode({})

        # this only works for default bucket ?
        init_params = {'name': bucket,
                       'ramQuotaMB': ramQuotaMB,
                       'replicaNumber': replicaNumber,
                       # 'proxyPort': proxyPort,
                       'bucketType': bucketType,
                       'replicaIndex': replica_index,
                       'threadsNumber': threadsNumber,
                       'flushEnabled': flushEnabled,
                       'evictionPolicy': evictionPolicy}

        if lww:
            init_params['conflictResolutionType'] = 'lww'

        if maxTTL:
            init_params['maxTTL'] = maxTTL
        if compressionMode:
            init_params['compressionMode'] = compressionMode
            
        if bucketType == 'ephemeral':
            del init_params['replicaIndex']     # does not apply to ephemeral buckets, and is even rejected

        init_params['storageBackend'] = storageBackend

#         versions = self.get_nodes_versions()
#         pre_spock = False
#         for version in versions:
#             if "5" > version:
#                 pre_spock = True
# 
#         if pre_spock:
#             init_params['proxyPort'] = proxyPort

        params = urllib.urlencode(init_params)

        log.info("{0} with param: {1}".format(api, params))
        create_start_time = time.time()

        maxwait = 60
        for numsleep in range(maxwait):
            status, content, header = self._http_request(api, 'POST', params)
            if status:
                break
            elif (int(header['status']) == 503 and
                    '{"_":"Bucket with given name still exists"}' in content):
                log.info("The bucket still exists, sleep 1 sec and retry")
                time.sleep(1)
            else:
                raise BucketCreationException(ip=self.ip, bucket_name=bucket)

        if (numsleep + 1) == maxwait:
            log.error("Tried to create the bucket for {0} secs.. giving up".
                      format(maxwait))
            raise BucketCreationException(ip=self.ip, bucket_name=bucket)

        create_time = time.time() - create_start_time
        log.info("{0:.02f} seconds to create bucket {1}".
                 format(round(create_time, 2), bucket))
        return status

    def change_bucket_props(self, bucket,
                      ramQuotaMB=None,
                      replicaNumber=None,
                      proxyPort=None,
                      replicaIndex=None,
                      flushEnabled=None,
                      timeSynchronization=None,
                      maxTTL=None,
                      compressionMode=None):
        
        api = '{0}{1}{2}'.format(self.baseUrl, 'pools/default/buckets/', bucket)
        if isinstance(bucket, Bucket):
            api = '{0}{1}{2}'.format(self.baseUrl, 'pools/default/buckets/', bucket.name)
        params = urllib.urlencode({})
        params_dict = {}
        existing_bucket = self.get_bucket_json(bucket)
        if ramQuotaMB:
            params_dict["ramQuotaMB"] = ramQuotaMB
        if replicaNumber:
            params_dict["replicaNumber"] = replicaNumber
        #if proxyPort:
        #    params_dict["proxyPort"] = proxyPort
        if replicaIndex:
            params_dict["replicaIndex"] = replicaIndex
        if flushEnabled:
            params_dict["flushEnabled"] = flushEnabled
        if timeSynchronization:
            params_dict["timeSynchronization"] = timeSynchronization
        if maxTTL:
            params_dict["maxTTL"] = maxTTL
        if compressionMode:
            params_dict["compressionMode"] = compressionMode
            
        params = urllib.urlencode(params_dict)

        log.info("%s with param: %s" % (api, params))
        status, content, header = self._http_request(api, 'POST', params)
        if timeSynchronization:
            if status:
                raise Exception("Erroneously able to set bucket settings %s for bucket on time-sync" % (params, bucket))
            return status, content
        if not status:
            raise Exception("Unable to set bucket settings %s for bucket" % (params, bucket))
        log.info("bucket %s updated" % bucket)
        return status
    
    def get_auto_compaction_settings(self):
        api = self.baseUrl + "settings/autoCompaction"
        status, content, header = self._http_request(api)
        return json.loads(content)

    def set_auto_compaction(self, parallelDBAndVC="false",
                            dbFragmentThreshold=None,
                            viewFragmntThreshold=None,
                            dbFragmentThresholdPercentage=None,
                            viewFragmntThresholdPercentage=None,
                            allowedTimePeriodFromHour=None,
                            allowedTimePeriodFromMin=None,
                            allowedTimePeriodToHour=None,
                            allowedTimePeriodToMin=None,
                            allowedTimePeriodAbort=None,
                            bucket=None):
        """Reset compaction values to default, try with old fields (dp4 build)
        and then try with newer fields"""
        params = {}
        api = self.baseUrl

        if bucket is None:
            # setting is cluster wide
            api = api + "controller/setAutoCompaction"
        else:
            # overriding per/bucket compaction setting
            api = api + "pools/default/buckets/" + bucket
            params["autoCompactionDefined"] = "true"
            # reuse current ram quota in mb per node
            num_nodes = len(self.node_statuses())
            bucket_info = self.get_bucket_json(bucket)
            quota = self.get_bucket_json(bucket)["quota"]["ram"] / (1048576 * num_nodes)
            params["ramQuotaMB"] = quota

        params["parallelDBAndViewCompaction"] = parallelDBAndVC
        # Need to verify None because the value could be = 0
        if dbFragmentThreshold is not None:
            params["databaseFragmentationThreshold[size]"] = dbFragmentThreshold
        if viewFragmntThreshold is not None:
            params["viewFragmentationThreshold[size]"] = viewFragmntThreshold
        if dbFragmentThresholdPercentage is not None:
            params["databaseFragmentationThreshold[percentage]"] = dbFragmentThresholdPercentage
        if viewFragmntThresholdPercentage is not None:
            params["viewFragmentationThreshold[percentage]"] = viewFragmntThresholdPercentage
        if allowedTimePeriodFromHour is not None:
            params["allowedTimePeriod[fromHour]"] = allowedTimePeriodFromHour
        if allowedTimePeriodFromMin is not None:
            params["allowedTimePeriod[fromMinute]"] = allowedTimePeriodFromMin
        if allowedTimePeriodToHour is not None:
            params["allowedTimePeriod[toHour]"] = allowedTimePeriodToHour
        if allowedTimePeriodToMin is not None:
            params["allowedTimePeriod[toMinute]"] = allowedTimePeriodToMin
        if allowedTimePeriodAbort is not None:
            params["allowedTimePeriod[abortOutside]"] = allowedTimePeriodAbort

        params = urllib.urlencode(params)
        log.info("'%s' bucket's settings will be changed with parameters: %s" % (bucket, params))
        return self._http_request(api, "POST", params)

    def disable_auto_compaction(self):
        """
           Cluster-wide Setting
              Disable autocompaction on doc and view
        """
        api = self.baseUrl + "controller/setAutoCompaction"
        log.info("Disable autocompaction in cluster-wide setting")
        status, content, header = self._http_request(api, "POST",
                                  "parallelDBAndViewCompaction=false")
        return status

    def flush_bucket(self, bucket="default"):
        if isinstance(bucket, Bucket):
            bucket_name = bucket.name
        else:
            bucket_name = bucket
        api = self.baseUrl + "pools/default/buckets/%s/controller/doFlush" % (bucket_name)
        status, content, header = self._http_request(api, 'POST')
        if not status:
            raise BucketFlushFailed(self.ip, bucket_name)
        log.info("Flush for bucket '%s' was triggered" % bucket_name)

    def get_bucket_CCCP(self, bucket):
        log.info("Getting CCCP config ")
        api = '%spools/default/b/%s' % (self.baseUrl, bucket)
        if isinstance(bucket, Bucket):
            api = '%spools/default/b/%s' % (self.baseUrl, bucket.name)
        status, content, header = self._http_request(api)
        if status:
            return json.loads(content)
        return None

    def compact_bucket(self, bucket="default"):
        api = self.baseUrl + 'pools/default/buckets/{0}/controller/compactBucket'.format(bucket)
        status, content, header = self._http_request(api, 'POST')
        if status:
            log.info('bucket compaction successful')
        else:
            raise BucketCompactionException(bucket)

        return True

    def cancel_bucket_compaction(self, bucket="default"):
        api = self.baseUrl + 'pools/default/buckets/{0}/controller/cancelBucketCompaction'.format(bucket)
        if isinstance(bucket, Bucket):
            api = self.baseUrl + 'pools/default/buckets/{0}/controller/cancelBucketCompaction'.format(bucket.name)
        status, content, header = self._http_request(api, 'POST')
        log.info("Status is {0}".format(status))
        if status:
            log.info('Cancel bucket compaction successful')
        else:
            raise BucketCompactionException(bucket)
        return True
    
class RestParser():

    def parse_get_bucket_response(self, response):
        parsed = json.loads(response)
        return self.parse_get_bucket_json(parsed)

    def parse_get_bucket_json(self, parsed):
        bucket = Bucket()
        bucket.name = parsed['name']
        bucket.uuid = parsed['uuid']
        bucket.type = parsed['bucketType']
#         bucket.port = parsed['proxyPort']
        bucket.port = 0
        bucket.nodes = list()
        if 'vBucketServerMap' in parsed:
            vBucketServerMap = parsed['vBucketServerMap']
            serverList = vBucketServerMap['serverList']
            bucket.servers.extend(serverList)
            if "numReplicas" in vBucketServerMap:
                bucket.numReplicas = vBucketServerMap["numReplicas"]
            # vBucketMapForward
            if 'vBucketMapForward' in vBucketServerMap:
                # let's gather the forward map
                vBucketMapForward = vBucketServerMap['vBucketMapForward']
                counter = 0
                for vbucket in vBucketMapForward:
                    # there will be n number of replicas
                    vbucketInfo = vBucket()
                    vbucketInfo.master = serverList[vbucket[0]]
                    if vbucket:
                        for i in range(1, len(vbucket)):
                            if vbucket[i] != -1:
                                vbucketInfo.replica.append(serverList[vbucket[i]])
                    vbucketInfo.id = counter
                    counter += 1
                    bucket.forward_map.append(vbucketInfo)
            vBucketMap = vBucketServerMap['vBucketMap']
            counter = 0
            for vbucket in vBucketMap:
                # there will be n number of replicas
                vbucketInfo = vBucket()
                vbucketInfo.master = serverList[vbucket[0]]
                if vbucket:
                    for i in range(1, len(vbucket)):
                        if vbucket[i] != -1:
                            vbucketInfo.replica.append(serverList[vbucket[i]])
                vbucketInfo.id = counter
                counter += 1
                bucket.vbuckets.append(vbucketInfo)
                # now go through each vbucket and populate the info
            # who is master , who is replica
        # get the 'storageTotals'
        log.debug('read {0} vbuckets'.format(len(bucket.vbuckets)))
        stats = parsed['basicStats']
        # vBucketServerMap
        bucketStats = BucketStats()
        log.debug('stats:{0}'.format(stats))
        bucketStats.opsPerSec = stats['opsPerSec']
        bucketStats.itemCount = stats['itemCount']
        if bucket.type != "memcached":
            bucketStats.diskUsed = stats['diskUsed']
        bucketStats.memUsed = stats['memUsed']
        quota = parsed['quota']
        bucketStats.ram = quota['ram']
        bucket.stats = bucketStats
        nodes = parsed['nodes']
        for nodeDictionary in nodes:
            node = Node()
            node.uptime = nodeDictionary['uptime']
            node.memoryFree = nodeDictionary['memoryFree']
            node.memoryTotal = nodeDictionary['memoryTotal']
            node.mcdMemoryAllocated = nodeDictionary['mcdMemoryAllocated']
            node.mcdMemoryReserved = nodeDictionary['mcdMemoryReserved']
            node.status = nodeDictionary['status']
            node.hostname = nodeDictionary['hostname']
            if 'clusterCompatibility' in nodeDictionary:
                node.clusterCompatibility = nodeDictionary['clusterCompatibility']
            if 'clusterMembership' in nodeDictionary:
                node.clusterCompatibility = nodeDictionary['clusterMembership']
            node.version = nodeDictionary['version']
            node.os = nodeDictionary['os']
            if "ports" in nodeDictionary:
                ports = nodeDictionary["ports"]
                if "proxy" in ports:
                    node.moxi = ports["proxy"]
                if "direct" in ports:
                    node.memcached = ports["direct"]
            if "hostname" in nodeDictionary:
                value = str(nodeDictionary["hostname"])
                node.ip = value[:value.rfind(":")]
                node.port = int(value[value.rfind(":") + 1:])
            if "otpNode" in nodeDictionary:
                node.id = nodeDictionary["otpNode"]
            bucket.nodes.append(node)
        return bucket

    def fetch_bucket_xdcr_stats(self, bucket='default', zoom='minute'):
        """Return deserialized bucket xdcr stats.
        Keyword argument:
        bucket -- bucket name
        zoom -- stats zoom level (minute | hour | day | week | month | year)
        """
        api = self.baseUrl + 'pools/default/buckets/@xdcr-{0}/stats?zoom={1}'.format(bucket, zoom)
        status, content, header = self._http_request(api)
        return json.loads(content)

    def get_xdc_queue_size(self, bucket):
        """Fetch bucket stats and return the latest value of XDC replication
        queue size"""
        bucket_stats = self.fetch_bucket_xdcr_stats(bucket)
        return bucket_stats['op']['samples']['replication_changes_left'][-1]

    def get_dcp_queue_size(self, bucket):
        """Fetch bucket stats and return the latest value of DCP
        queue size"""
        bucket_stats = self.fetch_bucket_stats(bucket)
        return bucket_stats['op']['samples']['ep_dcp_xdcr_items_remaining'][-1]

    def get_active_key_count(self, bucket):
        """Fetch bucket stats and return the bucket's curr_items count"""
        bucket_stats = self.fetch_bucket_stats(bucket)
        return bucket_stats['op']['samples']['curr_items'][-1]

    def get_replica_key_count(self, bucket):
        """Fetch bucket stats and return the bucket's replica count"""
        bucket_stats = self.fetch_bucket_stats(bucket)
        return bucket_stats['op']['samples']['vb_replica_curr_items'][-1]
    
    # the same as Preview a Random Document on UI
    def get_random_key(self, bucket):
        api = self.baseUrl + 'pools/default/buckets/%s/localRandomKey' % (bucket)
        status, content, header = self._http_request(api, headers=self._create_capi_headers())
        json_parsed = json.loads(content)
        if not status:
            raise Exception("unable to get random document/key for bucket %s" % (bucket))
        return json_parsed
    
