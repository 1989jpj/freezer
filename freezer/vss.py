# Copyright 2014 Hewlett-Packard
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from freezer.winutils import DisableFileSystemRedirection
from freezer.utils import create_subprocess

import logging
import os


def vss_create_shadow_copy(volume):
    """
    Create a new shadow copy for the specified volume

    Windows registry path for vss:
    HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\VSS\Settings

    MaxShadowCopies
    Windows is limited in how many shadow copies can create per volume.
    The default amount of shadow copies is 64, the minimum is 1 and the maxi-
    mum is 512, if you want to change the default value you need to add/edit
    the key MaxShadowCopies and set the amount of shadow copies per volume.

    MinDiffAreaFileSize
    The minimum size of the shadow copy storage area is a per-computer setting
    that can be specified by using the MinDiffAreaFileSize registry value.

    If the MinDiffAreaFileSize registry value is not set, the minimum size of
    the shadow copy storage area is 32 MB for volumes that are smaller than
    500 MB and 320 MB for volumes that are larger than 500 MB.

    If you have not set a maximum size, there is no limit to the amount
    of space that can be used.

    If the MinDiffAreaFileSize registry value does not exist, the backup
    application can create it under the following registry key:

    HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\VolSnap


    Freezer create a shadow copy for each time the client runs it's been
    removed after the backup is complete.

    :param volume: The letter of the windows volume e.g. c:\\
    :return: shadow_id: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    :return: shadow_path: shadow copy path
    """
    shadow_path = None
    shadow_id = None
    with DisableFileSystemRedirection():
        path = os.path.dirname(os.path.abspath(__file__))
        script = '{0}\\scripts\\vss.ps1'.format(path)
        (out, err) = create_subprocess(['powershell.exe',
                                        '-executionpolicy', 'unrestricted',
                                        '-command', script,
                                        '-volume', volume])
        if err != '':
            raise Exception('[*] Error creating a new shadow copy on {0}'
                            ', error {1}' .format(volume, err))

        for line in out.split('\n'):
            if 'symbolic' in line:
                shadow_path = line.split('>>')[1].strip()
            if '__RELPATH' in line:
                shadow_id = line.split('=')[1].strip().lower() + '}'
                shadow_id = shadow_id[1:]

        logging.info('[*] Created shadow copy {0}'.
                     format(shadow_id))

        return shadow_path, shadow_id


def vss_delete_shadow_copy(shadow_id, volume):
    """
    Delete a shadow copy from the volume with the given shadow_id
    :param shadow_id: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    :return: bool
    """

    with DisableFileSystemRedirection():
        cmd = ['vssadmin', 'delete', 'shadows',
               '/shadow={0}'.format(shadow_id), '/quiet']
        (out, err) = create_subprocess(cmd)
        if err != '':
            raise Exception('[*] Error deleting shadow copy with id {0}'
                            ', error {1}' .format(shadow_id, err))

        try:
            os.rmdir(os.path.join(volume, 'shadowcopy'))
        except Exception:
            logging.error('Failed to delete shadow copy symlink {0}'.
                          format(os.path.join(volume, 'shadowcopy')))

        logging.info('[*] Deleting shadow copy {0}'.
                     format(shadow_id))

        return True


def stop_sql_server(backup_opt_dict):
    """ Stop a SQL Server instance to perform the backup of the db files """

    logging.info('[*] Stopping SQL Server for backup')
    with DisableFileSystemRedirection():
        cmd = 'net stop "SQL Server ({0})"'\
            .format(backup_opt_dict.sql_server_instance)
        (out, err) = create_subprocess(cmd)
        if err != '':
            raise Exception('[*] Error while stopping SQL Server,'
                            ', error {0}'.format(err))


def start_sql_server(backup_opt_dict):
    """ Start the SQL Server instance after the backup is completed """

    with DisableFileSystemRedirection():
        cmd = 'net start "SQL Server ({0})"'\
            .format(backup_opt_dict.sql_server_instance)
        (out, err) = create_subprocess(cmd)
        if err != '':
            raise Exception('[*] Error while starting SQL Server'
                            ', error {0}'.format(err))
        logging.info('[*] SQL Server back to normal')
