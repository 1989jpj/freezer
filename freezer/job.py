"""
Copyright 2014 Hewlett-Packard

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This product includes cryptographic software written by Eric Young
(eay@cryptsoft.com). This product includes software written by Tim
Hudson (tjh@cryptsoft.com).
========================================================================
"""

import sys

from freezer import swift
from freezer import utils
from freezer import backup
from freezer import restore
from freezer import exec_cmd
import logging
from freezer.restore import RestoreOs


class Job:
    def __init__(self, conf_dict):
        self.conf = conf_dict

    def execute(self):
        logging.info('[*] Action not implemented')

    def get_metadata(self):
        return None

    @staticmethod
    def executemethod(func):
        def wrapper(self):
            self.start_time = utils.DateTime.now()
            self.conf.time_stamp = self.start_time.timestamp
            logging.info('[*] Job execution Started at: {0}'.
                         format(self.start_time))

            try:
                sw_connector = self.conf.client_manager.get_swift()
                self.conf.containers_list = sw_connector.get_account()[1]
            except Exception as error:
                raise Exception('Get containers list error: {0}'.format(error))

            retval = func(self)

            end_time = utils.DateTime.now()
            logging.info('[*] Job execution Finished, at: {0}'.
                         format(end_time))
            logging.info('[*] Job time Elapsed: {0}'.
                         format(end_time - self.start_time))
            return retval
        return wrapper


class InfoJob(Job):
    @Job.executemethod
    def execute(self):
        if self.conf.list_containers:
            swift.show_containers(self.conf.containers_list)
        elif self.conf.list_objects:
            if not self.conf.storage.ready():
                logging.critical(
                    '[*] Container {0} not available'.format(
                        self.conf.container))
                return False
            swift.show_objects(self.conf)
        else:
            logging.warning(
                '[*] No retrieving info options were set. Exiting.')
            return False
        return True


class BackupJob(Job):
    @Job.executemethod
    def execute(self):
        self.conf.storage.prepare()
        if self.conf.no_incremental:
            if self.conf.max_level or \
               self.conf.always_level:
                raise Exception(
                    'no-incremental option is not compatible '
                    'with backup level options')
            manifest_meta_dict = {}
        else:
            # Check if a backup exist in swift with same name.
            # If not, set backup level to 0
            manifest_meta_dict =\
                swift.check_backup_and_tar_meta_existence(self.conf)

        (self.conf, manifest_meta_dict) = swift.set_backup_level(
            self.conf, manifest_meta_dict)

        self.conf.manifest_meta_dict = manifest_meta_dict
        if self.conf.mode == 'fs':
            backup.backup(
                self.conf, self.start_time.timestamp, manifest_meta_dict)
        elif self.conf.mode == 'mongo':
            backup.backup_mode_mongo(
                self.conf, self.start_time.timestamp, manifest_meta_dict)
        elif self.conf.mode == 'mysql':
            backup.backup_mode_mysql(
                self.conf, self.start_time.timestamp, manifest_meta_dict)
        elif self.conf.mode == 'sqlserver':
            backup.backup_mode_sql_server(
                self.conf, self.time_stamp, manifest_meta_dict)
        else:
            raise ValueError('Please provide a valid backup mode')

    def get_metadata(self):
        metadata = {
            'current_level': self.conf.curr_backup_level,
            'fs_real_path': (self.conf.lvm_auto_snap or
                             self.conf.path_to_backup),
            'vol_snap_path':
                self.conf.path_to_backup if self.conf.lvm_auto_snap else '',
            'client_os': sys.platform,
            'client_version': self.conf.__version__
        }
        fields = ['action', 'always_level', 'backup_media', 'backup_name',
                  'container', 'container_segments', 'curr_backup_level',
                  'dry_run', 'hostname', 'path_to_backup', 'max_level',
                  'mode', 'meta_data_file', 'backup_name', 'hostname',
                  'time_stamp', 'curr_backup_level']
        for field_name in fields:
            metadata[field_name] = self.conf.__dict__.get(field_name, '')
        return metadata


class RestoreJob(Job):
    @Job.executemethod
    def execute(self):
        logging.info('[*] Executing FS restore...')

        if not self.conf.storage.ready():
            raise ValueError('Container: {0} not found. Please provide an '
                             'existing container.'
                             .format(self.conf.container))

        # Get the object list of the remote containers and store it in the
        # same dict passes as argument under the dict.remote_obj_list namespace
        res = RestoreOs(self.conf.client_manager, self.conf.container)
        restore_from_date = self.conf.restore_from_date
        backup_media = self.conf.backup_media
        if backup_media == 'fs':
            restore.restore_fs(self.conf)
        elif backup_media == 'nova':
            res.restore_nova(restore_from_date, self.conf.nova_inst_id)
        elif backup_media == 'cinder':
            res.restore_cinder_by_glance(restore_from_date, self.conf.cinder)
        elif backup_media == 'cindernative':
            res.restore_cinder(restore_from_date, self.conf.cinder_vol_id)
        else:
            raise Exception("unknown backup type: %s" % backup_media)


class AdminJob(Job):
    @Job.executemethod
    def execute(self):
        swift.remove_obj_older_than(self.conf)


class ExecJob(Job):
    @Job.executemethod
    def execute(self):
        logging.info('[*] exec job....')
        if self.conf.command:
            logging.info('[*] Executing exec job....')
            exec_cmd.execute(self.conf.command)
        else:
            logging.warning(
                '[*] No command info options were set. Exiting.')
            return False
        return True


def create_job(conf):
    if conf.action == 'backup':
        return BackupJob(conf)
    if conf.action == 'restore':
        return RestoreJob(conf)
    if conf.action == 'info':
        return InfoJob(conf)
    if conf.action == 'admin':
        return AdminJob(conf)
    if conf.action == 'exec':
        return ExecJob(conf)
    raise Exception('Action "{0}" not supported'.format(conf.action))
