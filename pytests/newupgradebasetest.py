import copy
import re
import testconstants
import gc
import sys
import traceback
import Queue
from threading import Thread
from basetestcase import BaseTestCase
from mc_bin_client import MemcachedError
from memcached.helper.data_helper import VBucketAwareMemcached, MemcachedClientHelper
from membase.helper.bucket_helper import BucketOperationHelper
from membase.api.rest_client import RestConnection, RestHelper, Bucket
from membase.helper.cluster_helper import ClusterOperationHelper
from remote.remote_util import RemoteMachineShellConnection, RemoteUtilHelper
from couchbase_helper.document import DesignDocument, View
from couchbase_helper.documentgenerator import BlobGenerator
from scripts.install import InstallerJob
from builds.build_query import BuildQuery
from pprint import pprint
from testconstants import CB_REPO
from testconstants import MV_LATESTBUILD_REPO
from testconstants import COUCHBASE_VERSION_2
from testconstants import COUCHBASE_VERSION_3
from testconstants import COUCHBASE_VERSIONS
from testconstants import SHERLOCK_VERSION
from testconstants import CB_VERSION_NAME
from testconstants import COUCHBASE_MP_VERSION
from testconstants import STANDARD_BUCKET_PORT

class NewUpgradeBaseTest(BaseTestCase):
    def setUp(self):
        super(NewUpgradeBaseTest, self).setUp()
        self.released_versions = ["2.0.0-1976-rel", "2.0.1", "2.5.0", "2.5.1",
                                  "2.5.2", "3.0.0", "3.0.1",
                                  "3.0.1-1444", "3.0.2", "3.0.2-1603", "3.0.3",
                                  "3.1.0", "3.1.0-1776", "3.1.1", "3.1.1-1807",
                                  "3.1.2", "3.1.2-1815", "3.1.3", "3.1.3-1823",
                                  "4.0.0", "4.0.0-4051", "4.1.0", "4.1.0-5005"]
        self.use_hostnames = self.input.param("use_hostnames", False)
        self.product = self.input.param('product', 'couchbase-server')
        self.initial_version = self.input.param('initial_version', '5.5.0-2958')
        self.initial_vbuckets = self.input.param('initial_vbuckets', 1024)
        self.upgrade_versions = self.input.param('upgrade_version', '6.0.1-2001')
        self.upgrade_versions = self.upgrade_versions.split(";")
        self.skip_cleanup = self.input.param("skip_cleanup", False)
        self.init_nodes = self.input.param('init_nodes', True)

        self.is_downgrade = self.input.param('downgrade', False)
        if self.is_downgrade:
            self.initial_version, self.upgrade_versions = self.upgrade_versions[0], [self.initial_version]

        upgrade_path = self.input.param('upgrade_path', [])
        if upgrade_path:
            upgrade_path = upgrade_path.split(",")
        self.upgrade_versions = upgrade_path + self.upgrade_versions
        if self.input.param('released_upgrade_version', None) is not None:
            self.upgrade_versions = [self.input.param('released_upgrade_version', None)]

        self.initial_build_type = self.input.param('initial_build_type', None)
        self.upgrade_build_type = self.input.param('upgrade_build_type', self.initial_build_type)
        self.stop_persistence = self.input.param('stop_persistence', False)
        self.rest_settings = self.input.membase_settings
        self.rest = None
        self.rest_helper = None
        self.is_ubuntu = False
        self.sleep_time = 15
        self.ddocs = []
        self.item_flag = self.input.param('item_flag', 0)
        self.expire_time = self.input.param('expire_time', 0)
        self.wait_expire = self.input.param('wait_expire', False)
        self.default_view_name = "upgrade-test-view"
        self.ddocs_num = self.input.param("ddocs-num", 0)
        self.view_num = self.input.param("view-per-ddoc", 2)
        self.is_dev_ddoc = self.input.param("is-dev-ddoc", False)
        self.during_ops = None
        if "during-ops" in self.input.test_params:
            self.during_ops = self.input.param("during-ops", None).split(",")
        if self.initial_version.startswith("1.6") or self.initial_version.startswith("1.7"):
            self.product = 'membase-server'
        else:
            self.product = 'couchbase-server'
        if self.max_verify is None:
            self.max_verify = min(self.num_items, 100000)
        shell = RemoteMachineShellConnection(self.master)
        type = shell.extract_remote_info().distribution_type
        shell.disconnect()
        if type.lower() == 'windows':
            self.is_linux = False
        else:
            self.is_linux = True
        if type.lower() == "ubuntu":
            self.is_ubuntu = True
        self.queue = Queue.Queue()
        self.upgrade_servers = []
        if self.initial_build_type == "community" and self.upgrade_build_type == "enterprise":
            if self.initial_version != self.upgrade_versions:
                self.log.warn(
                    "we can't upgrade from couchbase CE to EE with a different version,defaulting to initial_version")
                self.log.warn("http://developer.couchbase.com/documentation/server/4.0/install/upgrading.html")
                self.upgrade_versions = self.input.param('initial_version', '4.1.0-4963')
                self.upgrade_versions = self.upgrade_versions.split(";")

    def tearDown(self):
        test_failed = (hasattr(self, '_resultForDoCleanups') and \
                       len(self._resultForDoCleanups.failures or \
                           self._resultForDoCleanups.errors)) or \
                                 (hasattr(self, '_exc_info') and \
                                  self._exc_info()[1] is not None)
        if test_failed and self.skip_cleanup:
                self.log.warn("CLEANUP WAS SKIPPED DUE TO FAILURES IN UPGRADE TEST")
                self.cluster.shutdown(force=True)
                self.log.info("Test Input params were:")
                pprint(self.input.test_params)

                if self.input.param('BUGS', False):
                    self.log.warn("Test failed. Possible reason is: {0}"
                                           .format(self.input.param('BUGS', False)))
        else:
            if not hasattr(self, 'rest'):
                return
            try:
                # cleanup only nodes that are in cluster
                # not all servers have been installed
                if self.rest is None:
                    self._new_master(self.master)
                nodes = self.rest.get_nodes()
                temp = []
                for server in self.servers:
                    if server.ip in [node.ip for node in nodes]:
                        temp.append(server)
                self.servers = temp
            except Exception, e:
                if e:
                    print "Exception ", e
                self.cluster.shutdown(force=True)
                self.fail(e)
            super(NewUpgradeBaseTest, self).tearDown()
            if self.upgrade_servers:
                self._install(self.upgrade_servers,version=self.initial_version)
        self.sleep(20, "sleep 20 seconds before run next test")

    def _install(self, servers, version=None, community_to_enterprise=False):
        params = {}
        params['num_nodes'] = len(servers)
        params['product'] = self.product
        params['version'] = self.initial_version
        params['vbuckets'] = [self.initial_vbuckets]
        params['init_nodes'] = self.init_nodes
        if version:
            params['version'] = version
        if self.initial_build_type is not None:
            params['type'] = self.initial_build_type
        if community_to_enterprise:
            params['type'] = self.upgrade_build_type
        self.log.info("will install {0} on {1}".format(params['version'], [s.ip for s in servers]))
        InstallerJob().parallel_install(servers, params)
        self.add_built_in_server_user()
        if self.product in ["couchbase", "couchbase-server", "cb"]:
            success = True
            for server in servers:
                shell = RemoteMachineShellConnection(server)
                info = shell.extract_remote_info()
                success &= shell.is_couchbase_installed()
                self.sleep(5, "sleep 5 seconds to let cb up completely")
                ready = RestHelper(RestConnection(server)).is_ns_server_running(60)
                if not ready:
                    if "centos 7" in info.distribution_version.lower():
                        self.log.info("run systemctl daemon-reload")
                        shell.execute_command("systemctl daemon-reload", debug=False)
                        shell.start_server()
                    else:
                        log.error("Couchbase-server did not start...")
                shell.disconnect()
                if not success:
                    sys.exit("some nodes were not install successfully!")
        if self.rest is None:
            self._new_master(self.master)
        if self.use_hostnames:
            for server in self.servers[:self.nodes_init]:
                hostname = RemoteUtilHelper.use_hostname_for_server_settings(server)
                server.hostname = hostname

    def operations(self, servers, services=None):
        self.quota = self._initialize_nodes(self.cluster, servers,
                                            self.disabled_consistent_view,
                                            self.rebalanceIndexWaitingDisabled,
                                            self.rebalanceIndexPausingDisabled,
                                            self.maxParallelIndexers,
                                            self.maxParallelReplicaIndexers, self.port)
        if self.port and self.port != '8091':
            self.rest = RestConnection(self.master)
            self.rest_helper = RestHelper(self.rest)
        self.sleep(120, "wait to make sure node is ready")
        if len(servers) > 1:
            if services is None:
                self.cluster.rebalance([servers[0]], servers[1:], [],
                                       use_hostnames=self.use_hostnames)
            else:
                set_services = services.split(",")
                for i in range(1, len(set_services)):
                    self.cluster.rebalance([servers[0]], [servers[i]], [],
                                           use_hostnames=self.use_hostnames,
                                           services=[set_services[i]])
                    self.sleep(60)

        self.buckets = []
        gc.collect()
        if self.input.param('extra_verification', False):
            self.total_buckets += 2
            print self.total_buckets
        self.bucket_size = self._get_bucket_size(self.quota, self.total_buckets)
        self._bucket_creation()
        if self.stop_persistence:
            for server in servers:
                for bucket in self.buckets:
                    client = MemcachedClientHelper.direct_client(server, bucket)
                    client.stop_persistence()
            self.sleep(10)
        gen_load = BlobGenerator('upgrade', 'upgrade-', self.value_size, end=self.num_items)
        self._load_all_buckets(self.master, gen_load, "create", self.expire_time,
                                                             flag=self.item_flag)
        if not self.stop_persistence:
            self._wait_for_stats_all_buckets(servers)
        else:
            for bucket in self.buckets:
                drain_rate = 0
                for server in servers:
                    client = MemcachedClientHelper.direct_client(server, bucket)
                    drain_rate += int(client.stats()["ep_queue_size"])
                self.sleep(3, "Pause to load all items")
                self.assertEqual(self.num_items * (self.num_replicas + 1), drain_rate,
                    "Persistence is stopped, drain rate is incorrect %s. Expected %s" % (
                                    drain_rate, self.num_items * (self.num_replicas + 1)))
        self.change_settings()

    def _get_build(self, server, version, remote, is_amazon=False, info=None):
        if info is None:
            info = remote.extract_remote_info()
        build_repo = CB_REPO
        if version[:5] in COUCHBASE_VERSIONS:
            if version[:3] in CB_VERSION_NAME:
                build_repo = CB_REPO + CB_VERSION_NAME[version[:3]] + "/"
            elif version[:5] in COUCHBASE_MP_VERSION:
                build_repo = MV_LATESTBUILD_REPO

        if self.upgrade_build_type == "community":
            edition_type = "couchbase-server-community"
        else:
            edition_type = "couchbase-server-enterprise"

        builds, changes = BuildQuery().get_all_builds(version=version, timeout=self.wait_timeout * 5, \
                                                      deliverable_type=info.deliverable_type,
                                                      architecture_type=info.architecture_type, \
                                                      edition_type=edition_type, repo=build_repo, \
                                                      distribution_version=info.distribution_version.lower())

        self.log.info("finding build %s for machine %s" % (version, server))

        if re.match(r'[1-9].[0-9].[0-9]-[0-9]+$', version):
            version = version + "-rel"
        if version[:5] in self.released_versions:
            appropriate_build = BuildQuery().\
                find_couchbase_release_build('%s-enterprise' % (self.product),
                                           info.deliverable_type,
                                           info.architecture_type,
                                           version.strip(),
                                           is_amazon=is_amazon,
                                           os_version=info.distribution_version)
        else:
             appropriate_build = BuildQuery().\
                find_build(builds, '%s-enterprise' % (self.product), info.deliverable_type,
                                   info.architecture_type, version.strip())

        if appropriate_build is None:
            self.log.info("builds are: %s \n. Remote is %s, %s. Result is: %s" % (builds, remote.ip, remote.username, version))
            raise Exception("Build %s for machine %s is not found" % (version, server))
        return appropriate_build

    def _upgrade(self, upgrade_version, server, queue=None, skip_init=False, info=None, save_upgrade_config=False):
        try:
            remote = RemoteMachineShellConnection(server)
            appropriate_build = self._get_build(server, upgrade_version, remote, info=info)
            self.assertTrue(appropriate_build.url, msg="unable to find build {0}".format(upgrade_version))
            self.assertTrue(remote.download_build(appropriate_build), "Build wasn't downloaded!")
            o, e = remote.couchbase_upgrade(appropriate_build, save_upgrade_config=save_upgrade_config, forcefully=self.is_downgrade)
            self.log.info("upgrade {0} to version {1} is completed".format(server.ip, upgrade_version))
            """ remove this line when bug MB-11807 fixed """
            if self.is_ubuntu:
                remote.start_server()
            """ remove end here """
            self.rest = RestConnection(server)
            if self.is_linux:
                self.wait_node_restarted(server, wait_time=testconstants.NS_SERVER_TIMEOUT * 4, wait_if_warmup=True)
            else:
                self.wait_node_restarted(server, wait_time=testconstants.NS_SERVER_TIMEOUT * 10, wait_if_warmup=True, check_service=True)
            if not skip_init:
                self.rest.init_cluster(self.rest_settings.rest_username, self.rest_settings.rest_password)
            self.sleep(self.sleep_time)
            return o, e
        except Exception, e:
            print traceback.extract_stack()
            if queue is not None:
                queue.put(False)
                if not self.is_linux:
                    remote = RemoteMachineShellConnection(server)
                    output, error = remote.execute_command("cmd /c schtasks /Query /FO LIST /TN removeme /V")
                    remote.log_command_output(output, error)
                    output, error = remote.execute_command("cmd /c schtasks /Query /FO LIST /TN installme /V")
                    remote.log_command_output(output, error)
                    output, error = remote.execute_command("cmd /c schtasks /Query /FO LIST /TN upgrademe /V")
                    remote.log_command_output(output, error)
                    remote.disconnect()
                raise e
        if queue is not None:
            queue.put(True)

    def _async_update(self, upgrade_version, servers, queue=None, skip_init=False, info=None, save_upgrade_config=False):
        self.log.info("servers {0} will be upgraded to {1} version".
                      format([server.ip for server in servers], upgrade_version))
        q = queue or self.queue
        upgrade_threads = []
        for server in servers:
            upgrade_thread = Thread(target=self._upgrade,
                                    name="upgrade_thread" + server.ip,
                                    args=(upgrade_version, server, q, skip_init, info, save_upgrade_config))
            upgrade_threads.append(upgrade_thread)
            upgrade_thread.start()
        return upgrade_threads

    def _new_master(self, server):
        self.master = server
        self.rest = RestConnection(self.master)
        self.rest_helper = RestHelper(self.rest)

    def verification(self, servers, check_items=True):
        if self.use_hostnames:
            for server in servers:
                node_info = RestConnection(server).get_nodes_self()
                new_hostname = node_info.hostname
                self.assertEqual("%s:%s" % (server.hostname, server.port), new_hostname,
                                 "Hostname is incorrect for server %s. Settings are %s" % (server.ip, new_hostname))
        if self.master.ip != self.rest.ip or \
           self.master.ip == self.rest.ip and str(self.master.port) != str(self.rest.port):
            if self.port:
                self.master.port = self.port
            self.rest = RestConnection(self.master)
            self.rest_helper = RestHelper(self.rest)
        if self.port and self.port != '8091':
            settings = self.rest.get_cluster_settings()
            if settings and 'port' in settings:
                self.assertTrue(self.port == str(settings['port']),
                                'Expected cluster port is %s, but is %s' % (self.port, settings['port']))
        for bucket in self.buckets:
            if not self.rest_helper.bucket_exists(bucket.name):
                raise Exception("bucket: %s not found" % bucket.name)
        self.verify_cluster_stats(servers, max_verify=self.max_verify, \
                                  timeout=self.wait_timeout * 20, check_items=check_items)

        if self.ddocs:
            self.verify_all_queries()
        if "update_notifications" in self.input.test_params:
            if self.rest.get_notifications() != self.input.param("update_notifications", True):
                self.fail("update notifications settings wasn't saved")
        if "autofailover_timeout" in self.input.test_params:
            if self.rest.get_autofailover_settings().timeout != self.input.param("autofailover_timeout", None):
                self.fail("autofailover settings wasn't saved")
        if "autofailover_alerts" in self.input.test_params:
            alerts = self.rest.get_alerts_settings()
            if alerts["recipients"] != ['couchbase@localhost']:
                self.fail("recipients value wasn't saved")
            if alerts["sender"] != 'root@localhost':
                self.fail("sender value wasn't saved")
            if alerts["emailServer"]["user"] != 'user':
                self.fail("email_username value wasn't saved")
            if alerts["emailServer"]["pass"] != '':
                self.fail("email_password should be empty for security")
        if "autocompaction" in self.input.test_params:
            cluster_status = self.rest.cluster_status()
            if cluster_status["autoCompactionSettings"]["viewFragmentationThreshold"]\
                             ["percentage"] != self.input.param("autocompaction", 50):
                    self.log.info("Cluster status: {0}".format(cluster_status))
                    self.fail("autocompaction settings weren't saved")

    def verify_all_queries(self):
        query = {"connectionTimeout" : 60000}
        expected_rows = self.num_items
        if self.max_verify:
            expected_rows = self.max_verify
            query["limit"] = expected_rows
        if self.input.param("wait_expiration", False):
            expected_rows = 0
        for bucket in self.buckets:
            for ddoc in self.ddocs:
                prefix = ("", "dev_")[ddoc.views[0].dev_view]
                self.perform_verify_queries(len(ddoc.views), prefix, ddoc.name, query, bucket=bucket,
                                           wait_time=self.wait_timeout * 5, expected_rows=expected_rows,
                                           retry_time=10)

    def change_settings(self):
        status = True
        if "update_notifications" in self.input.test_params:
            status &= self.rest.update_notifications(str(self.input.param("update_notifications", 'true')).lower())
        if "autofailover_timeout" in self.input.test_params:
            status &= self.rest.update_autofailover_settings(True, self.input.param("autofailover_timeout", None))
        if "autofailover_alerts" in self.input.test_params:
            status &= self.rest.set_alerts_settings('couchbase@localhost', 'root@localhost', 'user', 'pwd')
        if "autocompaction" in self.input.test_params:
            tmp, _, _ = self.rest.set_auto_compaction(viewFragmntThresholdPercentage=
                                     self.input.param("autocompaction", 50))
            status &= tmp
            if not status:
                self.fail("some settings were not set correctly!")

    def warm_up_node(self, warmup_nodes=None):
        if not warmup_nodes:
            warmup_nodes = [self.servers[:self.nodes_init][-1], ]
        for warmup_node in warmup_nodes:
            shell = RemoteMachineShellConnection(warmup_node)
            shell.stop_couchbase()
            shell.disconnect()
        self.sleep(20)
        for warmup_node in warmup_nodes:
            shell = RemoteMachineShellConnection(warmup_node)
            shell.start_couchbase()
            shell.disconnect()
        ClusterOperationHelper.wait_for_ns_servers_or_assert(warmup_nodes, self)

    def start_index(self):
        if self.ddocs:
            query = {"connectionTimeout" : 60000}
            for bucket in self.buckets:
                for ddoc in self.ddocs:
                    prefix = ("", "dev_")[ddoc.views[0].dev_view]
                    self.perform_verify_queries(len(ddoc.views), prefix, ddoc.name, query, bucket=bucket)

    def failover(self):
        rest = RestConnection(self.master)
        nodes = rest.node_statuses()
        nodes = [node for node in nodes
                if node.ip != self.master.ip or str(node.port) != self.master.port]
        self.failover_node = nodes[0]
        rest.fail_over(self.failover_node.id)

    def add_back_failover(self):
        rest = RestConnection(self.master)
        rest.add_back_node(self.failover_node.id)

    def create_ddocs_and_views(self):
        self.default_view = View(self.default_view_name, None, None)
        for bucket in self.buckets:
            for i in xrange(int(self.ddocs_num)):
                views = self.make_default_views(self.default_view_name, self.view_num,
                                               self.is_dev_ddoc, different_map=True)
                ddoc = DesignDocument(self.default_view_name + str(i), views)
                self.ddocs.append(ddoc)
                for view in views:
                    self.cluster.create_view(self.master, ddoc.name, view, bucket=bucket)

    def delete_data(self, servers, paths_to_delete):
        for server in servers:
            shell = RemoteMachineShellConnection(server)
            for path in paths_to_delete:
                output, error = shell.execute_command("rm -rf {0}".format(path))
                shell.log_command_output(output, error)
                # shell._ssh_client.open_sftp().rmdir(path)
            shell.disconnect()

    def check_seqno(self, seqno_expected, comparator='=='):
        for bucket in self.buckets:
            if bucket.type == 'memcached':
                continue
            ready = BucketOperationHelper.wait_for_memcached(self.master,
                                                          bucket.name)
            self.assertTrue(ready, "wait_for_memcached failed")
            client = VBucketAwareMemcached(RestConnection(self.master), bucket)
            valid_keys, deleted_keys = bucket.kvs[1].key_set()
            for valid_key in valid_keys:
                try:
                    _, flags, exp, seqno, cas = client.memcached(valid_key).getMeta(valid_key)
                except MemcachedError, e:
                    print e
                    client.reset(RestConnection(self.master))
                    _, flags, exp, seqno, cas = client.memcached(valid_key).getMeta(valid_key)
                self.assertTrue((comparator == '==' and seqno == seqno_expected) or
                                (comparator == '>=' and seqno >= seqno_expected),
                                msg="seqno {0} !{1} {2} for key:{3}".
                                format(seqno, comparator, seqno_expected, valid_key))
            client.done()

    def force_reinstall(self, servers):
        for server in servers:
            try:
                remote = RemoteMachineShellConnection(server)
                appropriate_build = self._get_build(server, self.initial_version, remote)
                self.assertTrue(appropriate_build.url, msg="unable to find build {0}".format(self.initial_version))
                remote.download_build(appropriate_build)
                remote.install_server(appropriate_build, force=True)
                self.log.info("upgrade {0} to version {1} is completed".format(server.ip, self.initial_version))
                remote.disconnect()
                self.sleep(10)
                if self.is_linux:
                    self.wait_node_restarted(server, wait_time=testconstants.NS_SERVER_TIMEOUT * 4, wait_if_warmup=True)
                else:
                    self.wait_node_restarted(server, wait_time=testconstants.NS_SERVER_TIMEOUT * 10, wait_if_warmup=True, check_service=True)
            except Exception, e:
                print traceback.extract_stack()
                if queue is not None:
                    queue.put(False)
                    if not self.is_linux:
                        remote = RemoteMachineShellConnection(server)
                        output, error = remote.execute_command("cmd /c schtasks /Query /FO LIST /TN installme /V")
                        remote.log_command_output(output, error)
                        remote.disconnect()
                    raise e

    def _verify_vbucket_nums_for_swap(self, old_vbs, new_vbs):
        out_servers = set(old_vbs) - set(new_vbs)
        in_servers = set(new_vbs) - set(old_vbs)
        self.assertEqual(len(out_servers), len(in_servers),
                        "Seems like it wasn't swap rebalance. Out %s, in %s" % (
                                                len(out_servers),len(in_servers)))
        for vb_type in ["active_vb", "replica_vb"]:
            self.log.info("Checking %s on nodes that remain in cluster..." % vb_type)
            for server, stats in old_vbs.iteritems():
                if server in new_vbs:
                    self.assertTrue(sorted(stats[vb_type]) == sorted(new_vbs[server][vb_type]),
                    "Server %s Seems like %s vbuckets were shuffled, old vbs is %s, new are %s" %(
                                    server.ip, vb_type, stats[vb_type], new_vbs[server][vb_type]))
            self.log.info("%s vbuckets were not suffled" % vb_type)
            self.log.info("Checking in-out nodes...")
            vbs_servs_out = vbs_servs_in = []
            for srv, stat in old_vbs.iteritems():
                if srv in out_servers:
                    vbs_servs_out.extend(stat[vb_type])
            for srv, stat in new_vbs.iteritems():
                if srv in in_servers:
                    vbs_servs_in.extend(stat[vb_type])
            self.assertTrue(sorted(vbs_servs_out) == sorted(vbs_servs_in),
                            "%s vbuckets seem to be suffled" % vb_type)

    def monitor_dcp_rebalance(self):
        if self.input.param('initial_version', '')[:5] in COUCHBASE_VERSION_2 and \
           (self.input.param('upgrade_version', '')[:5] in COUCHBASE_VERSION_3 or \
            self.input.param('upgrade_version', '')[:5] in SHERLOCK_VERSION):
            if int(self.initial_vbuckets) >= 256:
                if self.master.ip != self.rest.ip or \
                   self.master.ip == self.rest.ip and \
                   str(self.master.port) != str(self.rest.port):
                    if self.port:
                        self.master.port = self.port
                    self.rest = RestConnection(self.master)
                    self.rest_helper = RestHelper(self.rest)
                if self.rest._rebalance_progress_status() == 'running':
                    self.log.info("Start monitoring DCP upgrade from {0} to {1}"\
                           .format(self.input.param('initial_version', '')[:5], \
                                    self.input.param('upgrade_version', '')[:5]))
                    status = self.rest.monitorRebalance()
                    if status:
                        self.log.info("Done DCP rebalance upgrade!")
                    else:
                        self.fail("Failed DCP rebalance upgrade")
                elif self.sleep(5) is None and any ("DCP upgrade completed successfully." \
                                    in d.values() for d in self.rest.get_logs(10)):
                    self.log.info("DCP upgrade is completed")
                else:
                    self.fail("DCP reabalance upgrade is not running")
            else:
                self.fail("Need vbuckets setting >= 256 for upgrade from 2.x.x to 3+")
        else:
            if self.master.ip != self.rest.ip:
                self.rest = RestConnection(self.master)
                self.rest_helper = RestHelper(self.rest)
            self.log.info("No need to do DCP rebalance upgrade")

    def dcp_rebalance_in_offline_upgrade_from_version2(self):
        if self.input.param('initial_version', '')[:5] in COUCHBASE_VERSION_2 and \
           (self.input.param('upgrade_version', '')[:5] in COUCHBASE_VERSION_3 or \
            self.input.param('upgrade_version', '')[:5] in SHERLOCK_VERSION) and \
            self.input.param('num_stoped_nodes', self.nodes_init) >= self.nodes_init:
            otpNodes = []
            nodes = self.rest.node_statuses()
            for node in nodes:
                otpNodes.append(node.id)
            self.log.info("Start DCP rebalance after complete offline upgrade from {0} to {1}"\
                           .format(self.input.param('initial_version', '')[:5], \
                                   self.input.param('upgrade_version', '')[:5]))
            self.rest.rebalance(otpNodes, [])
            """ verify DCP upgrade in 3.0.0 version """
            self.monitor_dcp_rebalance()
        else:
            self.log.info("No need to do DCP rebalance upgrade")

    def pre_upgrade(self, servers):
        if self.rest is None:
            self._new_master(self.master)
        self.ddocs_num = 0
        self.create_ddocs_and_views()
        verify_data = False
        if self.scan_consistency != "request_plus":
            verify_data = True
        self.load(self.gens_load, flag=self.item_flag,
                  verify_data=verify_data, batch_size=self.batch_size)
        rest = RestConnection(servers[0])
        output, rq_content, header = rest.set_auto_compaction(dbFragmentThresholdPercentage=20, viewFragmntThresholdPercentage=20)
        self.assertTrue(output, "Error in set_auto_compaction... {0}".format(rq_content))
        status, content, header = rest.set_indexer_compaction(mode="full", fragmentation=20)
        self.assertTrue(status, "Error in setting Append Only Compaction... {0}".format(content))
        operation_type = self.input.param("pre_upgrade", "")
        self.run_async_index_operations(operation_type)

    def during_upgrade(self, servers):
        print("before create_ddocs_and_views")
        self.ddocs_num = 0
        self.create_ddocs_and_views()
        kv_tasks = self.async_run_doc_ops()
        operation_type = self.input.param("during_upgrade", "")
        self.run_async_index_operations(operation_type)
        for task in kv_tasks:
            task.result()

    def post_upgrade(self, servers):
        print("before post_upgrade")
        self.ddocs_num = 0
        self.add_built_in_server_user()
        self.create_ddocs_and_views()
        kv_tasks = self.async_run_doc_ops()
        operation_type = self.input.param("post_upgrade", "")
        self.run_async_index_operations(operation_type)
        for task in kv_tasks:
            task.result()
        self.verification(servers,check_items=False)

    def _create_ephemeral_buckets(self):
        create_ephemeral_buckets = self.input.param(
            "create_ephemeral_buckets", False)
        if not create_ephemeral_buckets:
            return
        rest = RestConnection(self.master)
        versions = rest.get_nodes_versions()
        for version in versions:
            if "5" > version:
                self.log.info("Atleast one of the nodes in the cluster is "
                              "pre 5.0 version. Hence not creating ephemeral"
                              "bucket for the cluster.")
                return
        num_ephemeral_bucket = self.input.param("num_ephemeral_bucket", 1)
        server = self.master
        server_id = RestConnection(server).get_nodes_self().id
        ram_size = RestConnection(server).get_nodes_self().memoryQuota
        bucket_size = self._get_bucket_size(ram_size, self.bucket_size +
                                                      num_ephemeral_bucket)
        self.log.info("Creating ephemeral buckets")
        self.log.info("Changing the existing buckets size to accomodate new "
                      "buckets")
        for bucket in self.buckets:
            rest.change_bucket_props(bucket, ramQuotaMB=bucket_size)

        bucket_tasks = []
        bucket_params = copy.deepcopy(
            self.bucket_base_params['membase']['non_ephemeral'])
        bucket_params['size'] = bucket_size
        bucket_params['bucket_type'] = 'ephemeral'
        bucket_params['eviction_policy'] = 'noEviction'
        ephemeral_buckets = []
        self.log.info("Creating ephemeral buckets now")
        for i in range(num_ephemeral_bucket):
            name = 'ephemeral_bucket' + str(i)
            port = STANDARD_BUCKET_PORT + i + 1
            bucket_priority = None
            if self.standard_bucket_priority is not None:
                bucket_priority = self.get_bucket_priority(
                    self.standard_bucket_priority[i])

            bucket_params['bucket_priority'] = bucket_priority
            bucket_tasks.append(
                self.cluster.async_create_standard_bucket(name=name, port=port,
                                                          bucket_params=bucket_params))
            bucket = Bucket(name=name, authType=None, saslPassword=None,
                            num_replicas=self.num_replicas,
                            bucket_size=self.bucket_size,
                            port=port, master_id=server_id,
                            eviction_policy='noEviction', lww=self.lww)
            self.buckets.append(bucket)
            ephemeral_buckets.append(bucket)

        for task in bucket_tasks:
            task.result(self.wait_timeout * 10)

        if self.enable_time_sync:
            self._set_time_sync_on_buckets(
                ['standard_bucket' + str(i) for i in range(
                    num_ephemeral_bucket)])
        load_gen = BlobGenerator('upgrade', 'upgrade-', self.value_size,
                                 end=self.num_items)
        for bucket in ephemeral_buckets:
            self._load_bucket(bucket, self.master, load_gen, "create",
                              self.expire_time)

    def _return_maps(self):
        index_map = self.get_index_map()
        stats_map = self.get_index_stats(perNode=False)
        return index_map, stats_map
