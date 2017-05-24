import copy
import exceptions
import time
import uuid
import zlib
import logger
import mc_bin_client
import crc32
import socket
import ctypes
from membase.api.rest_client import RestConnection, RestHelper
import memcacheConstants
from memcached.helper.data_helper import MemcachedClientHelper, VBucketAwareMemcached
from mc_bin_client import MemcachedClient
from threading import Thread
import Queue
from collections import defaultdict
from couchbase_helper.stats_tools import StatsCommon
from remote.remote_util import RemoteMachineShellConnection
from subprocess import call

class BucketOperationHelper():

    #this function will assert

    @staticmethod
    def base_bucket_ratio(servers):
        ratio = 1.0
        #check if ip is same for all servers
        ip = servers[0].ip
        dev_environment = True
        for server in servers:
            if server.ip != ip:
                dev_environment = False
                break
        if dev_environment:
            ratio = 2.0 / 3.0 * 1 / len(servers)
        else:
            ratio = 2.0 / 3.0
        return ratio

    @staticmethod
    def create_multiple_buckets(server, replica, bucket_ram_ratio=(2.0 / 3.0),
                                howmany=3, sasl=True, saslPassword='password',
                                bucketType='membase', evictionPolicy='valueOnly'):
        success = True
        log = logger.Logger.get_logger()
        rest = RestConnection(server)
        info = rest.get_nodes_self()
        if info.memoryQuota < 450.0:
            log.error("at least need 450MB memoryQuota")
            success = False
        else:
            available_ram = info.memoryQuota * bucket_ram_ratio
            if available_ram / howmany > 100:
                bucket_ram = int(available_ram / howmany)
            else:
                bucket_ram = 100
                #choose a port that is not taken by this ns server
            port = info.moxi + 1
            for i in range(0, howmany):
                name = "bucket-{0}".format(i)
                if sasl:
                    rest.create_bucket(bucket=name,
                                       ramQuotaMB=bucket_ram,
                                       replicaNumber=replica,
                                       authType="sasl",
                                       saslPassword=saslPassword,
                                       proxyPort=port,
                                       bucketType=bucketType,
                                       evictionPolicy=evictionPolicy)
                else:
                    rest.create_bucket(bucket=name,
                                       ramQuotaMB=bucket_ram,
                                       replicaNumber=replica,
                                       proxyPort=port)
                port += 1
                msg = "create_bucket succeeded but bucket \"{0}\" does not exist"
                bucket_created = BucketOperationHelper.wait_for_bucket_creation(name, rest)
                if not bucket_created:
                    log.error(msg.format(name))
                    success = False
                    break
        return success

    @staticmethod
    def create_default_buckets(servers, number_of_replicas=1, assert_on_test=None):
        log = logger.Logger.get_logger()
        for serverInfo in servers:
            ip_rest = RestConnection(serverInfo)
            ip_rest.create_bucket(bucket='default',
                               ramQuotaMB=256,
                               replicaNumber=number_of_replicas,
                               proxyPort=11220)
            msg = 'create_bucket succeeded but bucket "default" does not exist'
            removed_all_buckets = BucketOperationHelper.wait_for_bucket_creation('default', ip_rest)
            if not removed_all_buckets:
                log.error(msg)
                if assert_on_test:
                    assert_on_test.fail(msg=msg)

    @staticmethod
    def create_bucket(serverInfo, name='default', replica=1, port=11210, test_case=None, bucket_ram=-1, password=None):
        log = logger.Logger.get_logger()
        rest = RestConnection(serverInfo)
        if bucket_ram < 0:
            info = rest.get_nodes_self()
            bucket_ram = info.memoryQuota * 2 / 3

        if password == None:
            authType = "sasl"
        else:
            authType = "none"

        rest.create_bucket(bucket=name,
                           ramQuotaMB=bucket_ram,
                           replicaNumber=replica,
                           proxyPort=port,
                           authType=authType,
                           saslPassword=password)
        msg = 'create_bucket succeeded but bucket "{0}" does not exist'
        bucket_created = BucketOperationHelper.wait_for_bucket_creation(name, rest)
        if not bucket_created:
            log.error(msg)
            if test_case:
                test_case.fail(msg=msg.format(name))
        return bucket_created

    @staticmethod
    def delete_all_buckets_or_assert(servers, test_case):
        log = logger.Logger.get_logger()
        for serverInfo in servers:
            rest = RestConnection(serverInfo)
            buckets = []
            try:
                buckets = rest.get_buckets()
            except Exception as e:
                log.error(e)
                log.error('15 seconds sleep before calling get_buckets again...')
                time.sleep(15)
                buckets = rest.get_buckets()
            log.info('deleting existing buckets {0} on {1}'.format([b.name for b in buckets], serverInfo.ip))
            for bucket in buckets:
                log.info("remove bucket {0} ...".format(bucket.name))
                try:
                    status = rest.delete_bucket(bucket.name)
                except ServerUnavailableException as e:
                    log.error(e)
                    log.error('5 seconds sleep before calling delete_bucket again...')
                    time.sleep(5)
                    status = rest.delete_bucket(bucket.name)
                if not status:
                    try:
                        BucketOperationHelper.print_dataStorage_content(servers)
                        log.info(StatsCommon.get_stats([serverInfo], bucket.name, "timings"))
                    except:
                        log.error("Unable to get timings for bucket")
                log.info('deleted bucket : {0} from {1}'.format(bucket.name, serverInfo.ip))
                msg = 'bucket "{0}" was not deleted even after waiting for two minutes'.format(bucket.name)
                if test_case:
                    if not BucketOperationHelper.wait_for_bucket_deletion(bucket.name, rest, 200):
                        try:
                            BucketOperationHelper.print_dataStorage_content(servers)
                            log.info(StatsCommon.get_stats([serverInfo], bucket.name, "timings"))
                        except:
                            log.error("Unable to get timings for bucket")
                        test_case.fail(msg)

    @staticmethod
    def delete_bucket_or_assert(serverInfo, bucket='default', test_case=None):
        log = logger.Logger.get_logger()
        log.info('deleting existing bucket {0} on {1}'.format(bucket, serverInfo))

        rest = RestConnection(serverInfo)
        if RestHelper(rest).bucket_exists(bucket):
            status = rest.delete_bucket(bucket)
            if not status:
                try:
                    BucketOperationHelper.print_dataStorage_content([serverInfo])
                    log.info(StatsCommon.get_stats([serverInfo], bucket, "timings"))
                except:
                    log.error("Unable to get timings for bucket")
            log.info('deleted bucket : {0} from {1}'.format(bucket, serverInfo.ip))
        msg = 'bucket "{0}" was not deleted even after waiting for two minutes'.format(bucket)
        if test_case:
            if not BucketOperationHelper.wait_for_bucket_deletion(bucket, rest, 200):
                try:
                    BucketOperationHelper.print_dataStorage_content([serverInfo])
                    log.info(StatsCommon.get_stats([serverInfo], bucket, "timings"))
                except:
                    log.error("Unable to get timings for bucket")
                test_case.fail(msg)


    @staticmethod
    def print_dataStorage_content(servers):
        """"printout content of data and index path folders"""
        #Determine whether its a cluster_run/not
        cluster_run = True

        firstIp = servers[0].ip
        if len(servers) == 1 and servers[0].port == '8091':
            cluster_run = False
        else:
            for node in servers:
                if node.ip != firstIp:
                    cluster_run = False
                    break

        for serverInfo in servers:
            node = RestConnection(serverInfo).get_nodes_self()
            paths = set([node.storage[0].path, node.storage[0].index_path])
            for path in paths:
                if "c:/Program Files" in path:
                    path = path.replace("c:/Program Files", "/cygdrive/c/Program Files")

                if cluster_run:
                    call(["ls", "-lR", path])
                else:
                    log.info("Total number of files.  No need to printout all "
                             "that flood the test log.")
                    shell = RemoteMachineShellConnection(serverInfo)
                    #o, r = shell.execute_command("ls -LR '{0}'".format(path))
                    o, r = shell.execute_command("wc -l '{0}'".format(path))
                    shell.log_command_output(o, r)

    #TODO: TRY TO USE MEMCACHED TO VERIFY BUCKET DELETION BECAUSE
    # BUCKET DELETION IS A SYNC CALL W.R.T MEMCACHED
    @staticmethod
    def wait_for_bucket_deletion(bucket,
                                 rest,
                                 timeout_in_seconds=120):
        log = logger.Logger.get_logger()
        log.info('waiting for bucket deletion to complete....')
        start = time.time()
        helper = RestHelper(rest)
        while (time.time() - start) <= timeout_in_seconds:
            if not helper.bucket_exists(bucket):
                return True
            else:
                time.sleep(2)
        return False

    @staticmethod
    def wait_for_bucket_creation(bucket,
                                 rest,
                                 timeout_in_seconds=120):
        log = logger.Logger.get_logger()
        log.info('waiting for bucket creation to complete....')
        start = time.time()
        helper = RestHelper(rest)
        while (time.time() - start) <= timeout_in_seconds:
            if helper.bucket_exists(bucket):
                return True
            else:
                time.sleep(2)
        return False

    @staticmethod
    def wait_for_vbuckets_ready_state(node, bucket, timeout_in_seconds=300, log_msg='', admin_user='cbadminbucket',
                                      admin_pass='password'):
        log = logger.Logger.get_logger()
        start_time = time.time()
        end_time = start_time + timeout_in_seconds
        ready_vbuckets = {}
        rest = RestConnection(node)
        servers = rest.get_nodes()
        RestHelper(rest).vbucket_map_ready(bucket, 60)
        vbucket_count = len(rest.get_vbuckets(bucket))
        vbuckets = rest.get_vbuckets(bucket)
        obj = VBucketAwareMemcached(rest, bucket)
        memcacheds, vbucket_map, vbucket_map_replica = obj.request_map(rest, bucket)
        #Create dictionary with key:"ip:port" and value: a list of vbuckets
        server_dict = defaultdict(list)
        for everyID in range(0, vbucket_count):
            memcached_ip_port = str(vbucket_map[everyID])
            server_dict[memcached_ip_port].append(everyID)
        while time.time() < end_time and len(ready_vbuckets) < vbucket_count:
            for every_ip_port in server_dict:
                #Retrieve memcached ip and port
                ip, port = every_ip_port.split(":")
                client = MemcachedClient(ip, int(port), timeout=30)
                client.vbucket_count = len(vbuckets)
                bucket_info = rest.get_bucket(bucket)
                versions = rest.get_nodes_versions(logging=False)
                pre_spock = False
                for version in versions:
                    if "5" > version:
                        pre_spock = True
                if pre_spock:
                    log.info("Atleast 1 of the server is on pre-spock "
                             "version. Using the old ssl auth to connect to "
                             "bucket.")
                    client.sasl_auth_plain(
                    bucket_info.name.encode('ascii'),
                    bucket_info.saslPassword.encode('ascii'))
                else:
                    client.sasl_auth_plain(admin_user, admin_pass)
                    bucket = bucket.encode('ascii')
                    client.bucket_select(bucket)
                for i in server_dict[every_ip_port]:
                    try:
                        (a, b, c) = client.get_vbucket_state(i)
                    except mc_bin_client.MemcachedError as e:
                        ex_msg = str(e)
                        if "Not my vbucket" in log_msg:
                            log_msg = log_msg[:log_msg.find("vBucketMap") + 12] + "..."
                        if e.status == memcacheConstants.ERR_NOT_MY_VBUCKET:
                            # May receive this while waiting for vbuckets, continue and retry...S
                            continue
                        log.error("%s: %s" % (log_msg, ex_msg))
                        continue
                    except exceptions.EOFError:
                        # The client was disconnected for some reason. This can
                        # happen just after the bucket REST API is returned (before
                        # the buckets are created in each of the memcached processes.)
                        # See here for some details: http://review.couchbase.org/#/c/49781/
                        # Longer term when we don't disconnect clients in this state we
                        # should probably remove this code.
                        log.error("got disconnected from the server, reconnecting")
                        client.reconnect()
                        client.sasl_auth_plain(bucket_info.name.encode('ascii'),
                                               bucket_info.saslPassword.encode('ascii'))
                        continue

                    if c.find("\x01") > 0 or c.find("\x02") > 0:
                        ready_vbuckets[i] = True
                    elif i in ready_vbuckets:
                        log.warning("vbucket state changed from active to {0}".format(c))
                        del ready_vbuckets[i]
                client.close()
        return len(ready_vbuckets) == vbucket_count

    # try to insert key in all vbuckets before returning from this function
    # bucket { 'name' : 90,'password':,'port':1211'}
    @staticmethod
    def wait_for_memcached(node, bucket, timeout_in_seconds=300, log_msg=''):
        log = logger.Logger.get_logger()
        msg = "waiting for memcached bucket : {0} in {1} to accept set ops"
        log.info(msg.format(bucket, node.ip))
        all_vbuckets_ready = BucketOperationHelper.wait_for_vbuckets_ready_state(node,
                                                                                 bucket, timeout_in_seconds, log_msg)
        # return (counter == vbucket_count) and all_vbuckets_ready
        return all_vbuckets_ready

    @staticmethod
    def verify_data(server, keys, value_equal_to_key, verify_flags, test, debug=False, bucket="default"):
        log = logger.Logger.get_logger()
        log_error_count = 0
        # verify all the keys
        client = MemcachedClientHelper.direct_client(server, bucket)
        vbucket_count = len(RestConnection(server).get_vbuckets(bucket))
        # populate key
        index = 0
        all_verified = True
        keys_failed = []
        for key in keys:
            try:
                index += 1
                vbucketId = crc32.crc32_hash(key) & (vbucket_count - 1)
                client.vbucketId = vbucketId
                flag, keyx, value = client.get(key=key)
                if value_equal_to_key:
                    test.assertEquals(value, key, msg='values dont match')
                if verify_flags:
                    actual_flag = socket.ntohl(flag)
                    expected_flag = ctypes.c_uint32(zlib.adler32(value)).value
                    test.assertEquals(actual_flag, expected_flag, msg='flags dont match')
                if debug:
                    log.info("verified key #{0} : {1}".format(index, key))
            except mc_bin_client.MemcachedError as error:
                if debug:
                    log_error_count += 1
                    if log_error_count < 100:
                        log.error(error)
                        log.error(
                            "memcachedError : {0} - unable to get a pre-inserted key : {0}".format(error.status, key))
                keys_failed.append(key)
                all_verified = False
        client.close()
        if len(keys_failed) > 0:
            log.error('unable to verify #{0} keys'.format(len(keys_failed)))
        return all_verified

    @staticmethod
    def keys_dont_exist(server, keys, bucket):
        log = logger.Logger.get_logger()
        #verify all the keys
        client = MemcachedClientHelper.direct_client(server, bucket)
        vbucket_count = len(RestConnection(server).get_vbuckets(bucket))
        #populate key
        for key in keys:
            try:
                vbucketId = crc32.crc32_hash(key) & (vbucket_count - 1)
                client.vbucketId = vbucketId
                client.get(key=key)
                client.close()
                log.error('key {0} should not exist in the bucket'.format(key))
                return False
            except mc_bin_client.MemcachedError as error:
                log.error(error)
                log.error("expected memcachedError : {0} - unable to get a pre-inserted key : {1}".format(error.status, key))
        client.close()
        return True

    @staticmethod
    def chunks(l, n):
        keys_chunks = {}
        index = 0
        for i in range(0, len(l), n):
            keys_chunks[index] = l[i:i + n]
            index += 1
        return keys_chunks

    @staticmethod
    def keys_exist_or_assert_in_parallel(keys, server, bucket_name, test, concurrency=2):
        log = logger.Logger.get_logger()
        verification_threads = []
        queue = Queue.Queue()
        for i in range(concurrency):
            keys_chunk = BucketOperationHelper.chunks(keys, len(keys) / concurrency)
            t = Thread(target=BucketOperationHelper.keys_exist_or_assert,
                       name="verification-thread-{0}".format(i),
                       args=(keys_chunk.get(i), server, bucket_name, test, queue))
            verification_threads.append(t)
        for t in verification_threads:
            t.start()
        for t in verification_threads:
            log.info("thread {0} finished".format(t.name))
            t.join()
        while not queue.empty():
            item = queue.get()
            if item is False:
                return False
        return True

    @staticmethod
    def keys_exist_or_assert(keys, server, bucket_name, test, queue=None):
        # we should try out at least three times
        log = logger.Logger.get_logger()
        # verify all the keys
        client = MemcachedClientHelper.proxy_client(server, bucket_name)
        # populate key
        retry = 1

        keys_left_to_verify = []
        keys_left_to_verify.extend(copy.deepcopy(keys))
        log_count = 0
        while retry < 6 and len(keys_left_to_verify) > 0:
            msg = "trying to verify {0} keys - attempt #{1} : {2} keys left to verify"
            log.info(msg.format(len(keys), retry, len(keys_left_to_verify)))
            keys_not_verified = []
            for key in keys_left_to_verify:
                try:
                    client.get(key=key)
                except mc_bin_client.MemcachedError as error:
                    keys_not_verified.append(key)
                    if log_count < 100:
                        log.error("key {0} does not exist because {1}".format(key, error))
                        log_count += 1
            retry += 1
            keys_left_to_verify = keys_not_verified
        if len(keys_left_to_verify) > 0:
            log_count = 0
            for key in keys_left_to_verify:
                log.error("key {0} not found".format(key))
                log_count += 1
                if log_count > 100:
                    break
            msg = "unable to verify {0} keys".format(len(keys_left_to_verify))
            log.error(msg)
            if test:
                queue.put(False)
                test.fail(msg=msg)
            if queue is None:
                return False
            else:
                queue.put(False)
        log.info("verified that {0} keys exist".format(len(keys)))
        if queue is None:
            return True
        else:
            queue.put(True)

    @staticmethod
    def load_some_data(serverInfo,
                   fill_ram_percentage=10.0,
                   bucket_name='default'):
        log = logger.Logger.get_logger()
        if fill_ram_percentage <= 0.0:
            fill_ram_percentage = 5.0
        client = MemcachedClientHelper.direct_client(serverInfo, bucket_name)
        #populate key
        rest = RestConnection(serverInfo)
        RestHelper(rest).vbucket_map_ready(bucket_name, 60)
        vbucket_count = len(rest.get_vbuckets(bucket_name))
        testuuid = uuid.uuid4()
        info = rest.get_bucket(bucket_name)
        emptySpace = info.stats.ram - info.stats.memUsed
        log.info('emptySpace : {0} fill_ram_percentage : {1}'.format(emptySpace, fill_ram_percentage))
        fill_space = (emptySpace * fill_ram_percentage) / 100.0
        log.info("fill_space {0}".format(fill_space))
        # each packet can be 10 KB
        packetSize = int(10 * 1024)
        number_of_buckets = int(fill_space) / packetSize
        log.info('packetSize: {0}'.format(packetSize))
        log.info('memory usage before key insertion : {0}'.format(info.stats.memUsed))
        log.info('inserting {0} new keys to memcached @ {0}'.format(number_of_buckets, serverInfo.ip))
        keys = ["key_%s_%d" % (testuuid, i) for i in range(number_of_buckets)]
        inserted_keys = []
        for key in keys:
            vbucketId = crc32.crc32_hash(key) & (vbucket_count - 1)
            client.vbucketId = vbucketId
            try:
                client.set(key, 0, 0, key)
                inserted_keys.append(key)
            except mc_bin_client.MemcachedError as error:
                log.error(error)
                client.close()
                log.error("unable to push key : {0} to vbucket : {1}".format(key, client.vbucketId))
                if test:
                    test.fail("unable to push key : {0} to vbucket : {1}".format(key, client.vbucketId))
                else:
                    break
        client.close()
        return inserted_keys
