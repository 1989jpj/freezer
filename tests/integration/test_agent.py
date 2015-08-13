# Copyright 2015 Hewlett-Packard
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========================================================================

from copy import copy
import json
import os

import common
import uuid


INTEGRATION_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.normpath(os.path.join(INTEGRATION_DIR, '..'))
COMMON_DIR = os.path.normpath(os.path.join(TEST_DIR, '..'))
FREEZER_BIN_DIR = os.path.normpath(os.path.join(COMMON_DIR, 'bin'))
FREEZERC = os.path.normpath(os.path.join(FREEZER_BIN_DIR, 'freezerc '))


class TestSimpleExecution(common.TestFS):

    def test_freezerc_executes(self):
        result = common.execute(FREEZERC + ' -h')
        self.assertIsNotNone(result)

    def test_freezerc_fails_with_wrong_params(self):
        result = common.execute(FREEZERC + ' --blabla', must_fail=True, merge_stderr=True)
        self.assertIn('unrecognized arguments', result)


class TestBackupFSLocalstorage(common.TestFS):

    def test_trees(self):
        self.assertTreesMatch()
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()

    def test_backup_single_level(self):
        """
        - use the default source and destination trees in /tmp (see common.TestFS)
        - use temporary directory for backup storage
        - add some random data
        - check that trees don't match anymore
        - execute backup of source tree
        - execute restore into destination tree
        - check that source and destination trees match

        :return: non on success
        """
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()

        with common.Temp_Tree() as storage_dir:
            backup_args = {
                'action': 'backup',
                'mode': 'fs',
                'path_to_backup': self.source_tree.path,
                'container': storage_dir.path,
                'storage': 'local',
                'max_level': '6',
                'max_segment_size': '67108864',
                'backup_name': uuid.uuid4().hex
            }

            restore_args = {
                'action': 'restore',
                'restore_abs_path': self.dest_tree.path,
                'backup_name': copy(backup_args['backup_name']),
                'storage': 'local',
                'container': storage_dir.path
            }
            result = common.execute(FREEZERC + self.dict_to_args(backup_args))
            self.assertIsNotNone(result)
            result = common.execute(FREEZERC + self.dict_to_args(restore_args))
            self.assertIsNotNone(result)
            self.assertTreesMatch()

    def test_backup_preexisting_dir(self):
        """
        Use external pre-defined directory for tests.
        If directory does not exist, then skip

        Restore to temporary folder (removed on exit)
        :return:
        """
        workdir = os.path.expanduser('~/test_dir')
        if not os.path.isdir(workdir):
            return
        self.source_tree = common.Temp_Tree(dir='/work', create=False)

        with common.Temp_Tree() as storage_dir:
            backup_args = {
                'action': 'backup',
                'mode': 'fs',
                'path_to_backup': self.source_tree.path,
                'container': storage_dir.path,
                'storage': 'local',
                'max_level': '6',
                'max_segment_size': '67108864',
                'backup_name': uuid.uuid4().hex
            }

            restore_args = {
                'action': 'restore',
                'restore_abs_path': self.dest_tree.path,
                'backup_name': copy(backup_args['backup_name']),
                'storage': 'local',
                'container': storage_dir.path
            }
            result = common.execute(FREEZERC + self.dict_to_args(backup_args))
            self.assertIsNotNone(result)
            result = common.execute(FREEZERC + self.dict_to_args(restore_args))
            self.assertIsNotNone(result)
        self.assertTreesMatch()

    def test_backup_local_storage_lvm(self):
        if not self.use_lvm:
            return

        self.source_tree.add_random_data()
        self.assertTreesMatchNot()

        backup_name = uuid.uuid4().hex
        lvm_auto_snap= self.source_tree.path
        lvm_snapsize= '1G'
        lvm_snapname= 'freezer-snap_{0}'.format(backup_name)
        lvm_dirmount = '/var/freezer/freezer-{0}'.format(backup_name)
        path_to_backup = os.path.join(lvm_dirmount, self.source_tree.path)

        with common.Temp_Tree() as storage_dir:
            backup_args = {
                'action': 'backup',
                'mode': 'fs',
                'path_to_backup': path_to_backup,
                'lvm_auto_snap': lvm_auto_snap,
                'lvm_dirmount': lvm_dirmount,
                'lvm_snapsize': lvm_snapsize,
                'lvm_snapname': lvm_snapname,
                'container': storage_dir.path,
                'storage': 'local',
                'max_level': '6',
                'max_segment_size': '67108864',
                'backup_name': backup_name
            }
            restore_args = {
                'action': 'restore',
                'restore_abs_path': self.dest_tree.path,
                'backup_name': copy(backup_args['backup_name']),
                'storage': 'local',
                'container': storage_dir.path
            }

            result = common.execute(FREEZERC + self.dict_to_args(backup_args))
            self.assertIsNotNone(result)
            result = common.execute(FREEZERC + self.dict_to_args(restore_args))
            self.assertIsNotNone(result)
        self.assertTreesMatch()


class TestBackupSSH(common.TestFS):
    """
    Tests are executed if the following env vars are defined:
     - FREEZER_TEST_SSH_KEY
     - FREEZER_TEST_SSH_USERNAME
     - FREEZER_TEST_SSH_HOST
     - FREEZER_TEST_CONTAINER (directory on the remote machine used to store backups)
    """

    def test_backup_ssh(self):
        if not self.use_ssh:
            return
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()

        backup_args = {
            'action': 'backup',
            'mode': 'fs',
            'path_to_backup': self.source_tree.path,
            'max_level': '6',
            'max_segment_size': '67108864',
            'backup_name': uuid.uuid4().hex,
            'storage': 'ssh',
            'container': self.container,
            'ssh_key': self.ssh_key,
            'ssh_username': self.ssh_username,
            'ssh_host': self.ssh_host,
            'metadata_out': '-'
        }
        restore_args = {
            'action': 'restore',
            'restore_abs_path': self.dest_tree.path,
            'backup_name': copy(backup_args['backup_name']),
            'storage': 'ssh',
            'container': self.container,
            'ssh_key': self.ssh_key,
            'ssh_username': self.ssh_username,
            'ssh_host': self.ssh_host
        }

        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)

        result = json.loads(result)
        sub_path = '_'.join([result['hostname'], result['backup_name']])
        # It may be reasonable to insert a check of the files in the
        # storage directory
        # file_list = self.get_file_list_ssh(sub_path)

        self.assertIn('backup_name', result)
        self.assertEquals(result['backup_name'], backup_args['backup_name'])
        self.assertIn('container', result)
        self.assertEquals(result['container'], self.container)

        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()

        self.remove_ssh_directory(sub_path)

    def test_backup_ssh_incremental(self):
        if not self.use_ssh:
            return
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()

        backup_args = {
            'action': 'backup',
            'mode': 'fs',
            'path_to_backup': self.source_tree.path,
            'max_level': '6',
            'max_segment_size': '67108864',
            'backup_name': uuid.uuid4().hex,
            'storage': 'ssh',
            'container': self.container,
            'ssh_key': self.ssh_key,
            'ssh_username': self.ssh_username,
            'ssh_host': self.ssh_host,
            'metadata_out': '-'
        }
        restore_args = {
            'action': 'restore',
            'restore_abs_path': self.dest_tree.path,
            'backup_name': copy(backup_args['backup_name']),
            'storage': 'ssh',
            'container': self.container,
            'ssh_key': self.ssh_key,
            'ssh_username': self.ssh_username,
            'ssh_host': self.ssh_host
        }
        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)

        result = json.loads(result)
        sub_path = '_'.join([result['hostname'], result['backup_name']])
        # It may be reasonable to insert a check of the files in the
        # storage directory
        # file_list = self.get_file_list_ssh(sub_path)

        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()

        # -- level 1
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()
        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)
        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()

        # -- level 2
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()
        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)
        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()

        self.remove_ssh_directory(sub_path)

    def test_backup_ssh_incremental_with_lvm(self):
        if not self.use_ssh:
            return
        if not self.use_lvm:
            return

        self.source_tree.add_random_data()
        self.assertTreesMatchNot()

        backup_name = uuid.uuid4().hex
        lvm_auto_snap= self.source_tree.path
        lvm_snapsize= '1G'
        lvm_snapname= 'freezer-snap_{0}'.format(backup_name)
        lvm_dirmount = '/var/freezer/freezer-{0}'.format(backup_name)
        path_to_backup = os.path.join(lvm_dirmount, self.source_tree.path)

        backup_args = {
            'action': 'backup',
            'mode': 'fs',
            'path_to_backup': path_to_backup,
            'lvm_auto_snap': lvm_auto_snap,
            'lvm_dirmount': lvm_dirmount,
            'lvm_snapsize': lvm_snapsize,
            'lvm_snapname': lvm_snapname,
            'backup_name': backup_name,
            'max_level': '6',
            'max_segment_size': '67108864',
            'storage': 'ssh',
            'container': self.container,
            'ssh_key': self.ssh_key,
            'ssh_username': self.ssh_username,
            'ssh_host': self.ssh_host
        }
        restore_args = {
            'action': 'restore',
            'restore_abs_path': self.dest_tree.path,
            'backup_name': copy(backup_args['backup_name']),
            'storage': 'ssh',
            'container': self.container,
            'ssh_key': self.ssh_key,
            'ssh_username': self.ssh_username,
            'ssh_host': self.ssh_host
        }
        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)
        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()

        # -- level 1
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()
        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)
        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()

        # -- level 2
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()
        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)
        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()


class TestBackupUsingSwiftStorage(common.TestFS):
    """
    Tests are executed if the following env vars are defined:

     - FREEZER_TEST_OS_TENANT_NAME
     - FREEZER_TEST_OS_USERNAME
     - FREEZER_TEST_OS_REGION_NAME
     - FREEZER_TEST_OS_PASSWORD
     - FREEZER_TEST_OS_AUTH_URL
    """

    def test_backup_os_simple(self):
        if not self.use_os:
            return
        self.source_tree.add_random_data()
        self.assertTreesMatchNot()

        backup_args = {
            'action': 'backup',
            'mode': 'fs',
            'path_to_backup': self.source_tree.path,
            'max_level': '6',
            'max_segment_size': '67108864',
            'backup_name': uuid.uuid4().hex,
            'storage': 'swift',
            'container': 'freezer_test_backups_{0}'.format(uuid.uuid4().hex),
            'metadata_out': '-'
        }
        restore_args = {
            'action': 'restore',
            'restore_abs_path': self.dest_tree.path,
            'backup_name': copy(backup_args['backup_name']),
            'storage': 'swift',
            'container': copy(backup_args['container']),
        }
        remove_args = {
            'action': 'admin',
            'remove_older_than': 0,
            'backup_name': copy(backup_args['backup_name']),
            'storage': 'swift',
            'container': copy(backup_args['container']),
        }
        # --- backup
        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)
        result = json.loads(result)
        self.assertIn('backup_name', result)
        self.assertEquals(result['backup_name'], backup_args['backup_name'])
        self.assertIn('container', result)
        self.assertEquals(result['container'], backup_args['container'])

        # It may be reasonable to insert a check of the files in the
        # swift container
        # file_list = self.get_file_list_openstack(result['container'])

        # --- restore
        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        self.assertTreesMatch()

        # --- remove backups and container
        result = common.execute(FREEZERC + self.dict_to_args(remove_args))
        self.assertIsNotNone(result)

        result = self.remove_swift_container(backup_args['container'])
        self.assertIsNotNone(result)

    def test_backup_swift_mysql(self):
        if not self.use_os:
            return
        if not self.use_lvm:
            return
        if not os.path.isdir('/var/lib/mysql'):
            return
        self.source_tree = common.Temp_Tree(dir='/var/lib/mysql', create=False)

        backup_name = uuid.uuid4().hex
        lvm_auto_snap = self.source_tree.path
        lvm_snapsize = '1G'
        lvm_snapname = 'freezer-snap_{0}'.format(backup_name)
        lvm_dirmount = '/var/freezer/freezer-{0}'.format(backup_name)
        path_to_backup = os.path.join(lvm_dirmount, self.source_tree.path)

        backup_args = {
            'action': 'backup',
            'mode': 'mysql',
            'mysql_conf': '/etc/mysql/debian.cnf',
            'path_to_backup': path_to_backup,
            'lvm_auto_snap': lvm_auto_snap,
            'lvm_dirmount': lvm_dirmount,
            'lvm_snapsize': lvm_snapsize,
            'lvm_snapname': lvm_snapname,
            'container': 'freezer_test_container_{0}'.format(backup_name),
            'storage': 'swift',
            'max_level': '6',
            'max_segment_size': '67108864',
            'backup_name': backup_name
        }
        restore_args = {
            'action': 'restore',
            'restore_abs_path': self.dest_tree.path,
            'backup_name': copy(backup_args['backup_name']),
            'storage': 'swift',
            'container': copy(backup_args['container'])
        }

        result = common.execute(FREEZERC + self.dict_to_args(backup_args))
        self.assertIsNotNone(result)
        result = common.execute(FREEZERC + self.dict_to_args(restore_args))
        self.assertIsNotNone(result)
        # we cannot test if trees as a running mysql instance will modify the files
