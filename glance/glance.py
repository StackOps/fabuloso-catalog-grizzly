#   Copyright 2012-2013 STACKOPS TECHNOLOGIES S.L.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.from fabric.api import *
from fabric.api import *
from cuisine import *

from fabuloso import fabuloso

import fabuloso.utils as utils

GLANCE_IMAGES = '/var/lib/glance/images'
GLANCE_API_CONFIG = '/etc/glance/glance-api.conf'
GLANCE_REGISTRY_CONFIG = '/etc/glance/glance-registry.conf'
GLANCE_REGISTRY_PASTE_INI = '/etc/glance/glance-registry-paste.ini'


def stop():
    with settings(warn_only=True):
        sudo("service glance-api stop")
        sudo("service glance-registry stop")


def start():
    stop()
    sudo("service glance-api start")
    sudo("service glance-registry start")


def uninstall_ubuntu_packages():
    """Uninstall glance packages"""
    package_clean('glance')
    package_clean('glance-api')
    package_clean('python-glanceclient')
    package_clean('glance-common')
    package_clean('glance-registry')
    package_clean('python-glance')
    package_clean('python-mysqldb')


def install(cluster=False):
    """Generate glance configuration. Execute on both servers"""
    package_ensure('glance')
    package_ensure('glance-api')
    package_ensure('python-glanceclient')
    package_ensure('glance-common')
    package_ensure('glance-registry')
    package_ensure('python-glance')
    package_ensure('python-mysqldb')
    if cluster:
        stop()
        sudo('echo "manual" >> /etc/init/glance-registry.override')
        sudo('echo "manual" >> /etc/init/glance-api.override')
        sudo('mkdir -p /usr/lib/ocf/resource.d/openstack')
        put('./ocf/glance-registry',
            '/usr/lib/ocf/resource.d/openstack/glance-registry', use_sudo=True)
        put('./ocf/glance-api',
            '/usr/lib/ocf/resource.d/openstack/glance-api', use_sudo=True)
        sudo('chmod +x /usr/lib/ocf/resource.d/openstack/glance-*')


def sql_connect_string(host='127.0.0.1', password='stackops', port='3306', schema='glance', username='glance'):
    sql_connection = 'mysql://%s:%s@%s:%s/%s' % (username, password, host,
                                                 port, schema)
    return sql_connection


def set_config_file(service_user='glance', service_tenant_name='service', service_pass='stackops',auth_host='127.0.0.1',
                    auth_port='35357', auth_protocol='http', mysql_username='glance',
                    mysql_password='stackops', mysql_host='127.0.0.1', mysql_port='3306', mysql_schema='glance'):
    utils.set_option(GLANCE_API_CONFIG, 'enable_v1_api', 'True')
    utils.set_option(GLANCE_API_CONFIG, 'enable_v2_api', 'True')
    for f in ['/etc/glance/glance-api.conf',
              '/etc/glance/glance-registry.conf']:
        sudo("sed -i 's#sql_connection.*$#sql_connection = %s#g' %s"
             % (sql_connect_string(mysql_host, mysql_password, mysql_port,
                                   mysql_schema, mysql_username), f))
        sudo("sed -i 's/admin_password.*$/admin_password = %s/g' %s" %
             (service_pass, f))
        sudo("sed -i 's/admin_tenant_name.*$/admin_tenant_name = %s/g' %s" %
             (service_tenant_name, f))
        sudo("sed -i 's/admin_user.*$/admin_user = %s/g' %s" %
             (service_user, f))
        sudo("sed -i 's/auth_host.*$/auth_host = %s/g' %s" % (auth_host, f))
        sudo("sed -i 's/auth_port.*$/auth_port = %s/g' %s" % (auth_port, f))
        sudo("sed -i 's/auth_protocol.*$/auth_protocol = %s/g' %s"
             % (auth_protocol, f))

    utils.set_option(GLANCE_REGISTRY_CONFIG, 'config_file',
                     '/etc/glance/glance-registry-paste.ini',
                     section='paste_deploy')
    utils.set_option(GLANCE_API_CONFIG,
                     'config_file', '/etc/glance/glance-api-paste.ini',
                     section='paste_deploy')
    utils.set_option(GLANCE_API_CONFIG,
                     'flavor', 'keystone+cachemanagement',
                     section='paste_deploy')
    utils.set_option(GLANCE_REGISTRY_CONFIG,
                     'flavor', 'keystone',
                     section='paste_deploy')

    utils.set_option(GLANCE_REGISTRY_PASTE_INI, 'pipeline',
                     'authtoken context registryapp',
                     section='pipeline:glance-registry-keystone')

    start()
    sudo("glance-manage version_control 0")
    sudo("glance-manage db_sync")


def configure_local_storage(config_local_storage="true", delete_content=False, set_glance_owner=True):
    if str(config_local_storage).lower() == "true":
        if delete_content:
            sudo('rm -fr %s' % GLANCE_IMAGES)
        stop()
        utils.set_option(GLANCE_API_CONFIG, 'default_store', 'file')
        sudo('sed -i "#%s#d" /etc/fstab' % GLANCE_IMAGES)
        sudo('mkdir -p %s' % GLANCE_IMAGES)
        with settings(warn_only=True):
            if set_glance_owner:
                sudo('chown glance:glance -R %s' % GLANCE_IMAGES)
        start()

def configure_nfs_storage(config_nfs_storage="false", nfs_endpoint='localhost:/mnt', delete_content=False,
                          set_glance_owner=True,
                          nfs_server_mount_point_params='defaults'):
    if str(config_nfs_storage).lower() == "true":
        package_ensure('nfs-common')
        package_ensure('autofs')
        if delete_content:
            sudo('rm -fr %s' % GLANCE_IMAGES)
        stop()
        utils.set_option(GLANCE_API_CONFIG, 'default_store', 'file')
        glance_images_exists = file_exists(GLANCE_IMAGES)
        if not glance_images_exists:
            sudo('mkdir -p %s' % GLANCE_IMAGES)
        mpoint = '%s  -fstype=nfs,vers=3,%s   %s' % \
                 (GLANCE_IMAGES, nfs_server_mount_point_params, nfs_endpoint)
        sudo('''echo "/-    /etc/auto.nfs" > /etc/auto.master''')
        sudo('''echo "%s" > /etc/auto.nfs''' % mpoint)
        sudo('service autofs restart')
        with settings(warn_only=True):
            if set_glance_owner:
                if not glance_images_exists:
                    sudo('chown glance:glance -R %s' % GLANCE_IMAGES)
        start()

def configure_s3_storage(config_s3_storage="false",
                        s3_store_host='s3.amazonaws.com',s3_store_access_key='',s3_store_secret_key='',
                        s3_store_bucket='glance-s3-bucket',s3_store_create_bucket_on_put=False):
    if str(config_s3_storage).lower() == "true":
        stop()
        utils.set_option(GLANCE_API_CONFIG, 'default_store', 's3')
        utils.set_option(GLANCE_API_CONFIG, 's3_store_host', s3_store_host)
        utils.set_option(GLANCE_API_CONFIG, 's3_store_access_key', s3_store_access_key)
        utils.set_option(GLANCE_API_CONFIG, 's3_store_secret_key', s3_store_secret_key)
        utils.set_option(GLANCE_API_CONFIG, 's3_store_bucket', s3_store_bucket)
        utils.set_option(GLANCE_API_CONFIG, 's3_store_create_bucket_on_put', s3_store_create_bucket_on_put)
        start()

def publish_ttylinux(auth_uri='http://127.0.0.1:35357/v2.0',
                     test_username='admin', test_password='stackops',
                     test_tenant_name='admin',
                     ):
    image_name = 'ttylinux-uec-amd64-12.1_2.6.35-22_1'
    with cd('/tmp'):
        sudo('wget http://stackops.s3.amazonaws.com/images/%s.tar.gz -O '
             '/tmp/%s.tar.gz' % (image_name, image_name))
        sudo('mkdir -p images')
        sudo('tar -zxf %s.tar.gz  -C images' % image_name)
        stdout = sudo('glance --os-username %s --os-password %s '
                      '--os-tenant-name %s --os-auth-url %s --os-endpoint-type'
                      ' internalURL image-create '
                      '--name="ttylinux-uec-amd64-kernel" '
                      '--is-public=true --container-format=aki '
                      '--disk-format=aki '
                      '< /tmp/images/%s-vmlinuz*' %
                      (test_username, test_password, test_tenant_name,
                       auth_uri, image_name))
        kernel_id = local('''echo "%s" | grep ' id ' ''' %
                          stdout, capture=True).split('|')
        puts(kernel_id)
        sudo('glance --os-username %s --os-password %s --os-tenant-name %s '
             '--os-auth-url %s --os-endpoint-type internalURL image-create '
             '--name="ttylinux-uec-amd64" --is-public=true '
             '--container-format=ami --disk-format=ami --property '
             'kernel_id=%s < /tmp/images/%s.img'
             % (test_username, test_password, test_tenant_name, auth_uri,
                kernel_id[2].strip(), image_name))
        sudo('rm -fR images')
        sudo('rm -f %s.tar.gz' % image_name)


def validate_database(database_type, username, password, host, port,
                      schema, drop_schema=None, install_database=None):
    fab = fabuloso.Fabuloso()
    fab.validate_database(database_type, username, password, host, port,
                          schema, drop_schema, install_database)


def validate_credentials(user, password, tenant, endpoint, admin_token):
    fab = fabuloso.Fabuloso()
    fab.validate_credentials(user, password, tenant, endpoint, admin_token)
