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
"""MySQL Component.

This component exposes methods for mysql purposes.
The following are the services available:
    * configure root_pass:string -> configures the mysql admin with the
                                    'root_pass' parameter
    * start -> starts the mysql service
    * stop -> stops the mysql service
"""
from fabric.api import sudo, settings
from cuisine import package_ensure
from fabuloso import fabuloso


def configure(root_pass='stackops'):
    """Generate mysql configuration. Execute on both servers"""
    __configure_ubuntu_packages(root_pass)
    stop()

    #sudo('echo "manual" >> /etc/init/mysql.override')
    sudo('chmod -R og=rxw /var/lib/mysql')
    sudo('chown -R mysql:mysql /var/lib/mysql')
    start()
    sudo("sed -i 's/127.0.0.1/0.0.0.0/g' /etc/mysql/my.cnf")
    sudo("""mysql -uroot -p%s -e "GRANT ALL PRIVILEGES ON *.* TO
         'root'@'%%' IDENTIFIED BY '%s' WITH GRANT OPTION;" """
         % (root_pass, root_pass))


def start():
    stop()
    sudo("nohup service mysql start")


def __configure_ubuntu_packages(root_pass='stackops'):
    """Configure mysql ubuntu packages"""
    sudo('echo mysql-server-5.5 mysql-server/root_password password %s'
         ' | debconf-set-selections' % root_pass)
    sudo('echo mysql-server-5.5 mysql-server/root_password_again password %s'
         ' | debconf-set-selections' % root_pass)
    sudo('echo mysql-server-5.5 mysql-server/start_on_boot boolean true'
         ' | debconf-set-selections')
    package_ensure('mysql-server')
    package_ensure('python-mysqldb')


def stop():
    with settings(warn_only=True):
        sudo("nohup service mysql stop")


def setup_schema(root_pass='stackops', username=None, password=None,
                 schema_name=None, host=None):

    sudo('mysql -uroot -p%s -e "DROP DATABASE IF EXISTS %s;"'
         % (root_pass, schema_name))
    sudo('mysql -uroot -p%s -e "CREATE DATABASE %s;"' % (root_pass,
         schema_name))
    if host is not None:
        sudo("""mysql -uroot -p%s -e "GRANT ALL PRIVILEGES ON %s.* TO
             '%s'@'%s' IDENTIFIED BY '%s';" """
             % (root_pass, schema_name, username, host, password))
    else:
        sudo("""mysql -uroot -p%s -e "GRANT ALL PRIVILEGES ON %s.*
             TO '%s'@'localhost' IDENTIFIED BY '%s';" """
             % (root_pass, schema_name, username, password))
        sudo("""mysql -uroot -p%s -e "GRANT ALL PRIVILEGES ON %s.*
             TO '%s'@'%%' IDENTIFIED BY '%s';" """
             % (root_pass, schema_name, username, password))


def setup_keystone(root_pass='stackops', keystone_user='keystone',
                   keystone_password='stackops'):
    setup_schema(username=keystone_user, password=keystone_password,
                 schema_name='keystone', root_pass=root_pass)


def setup_nova(root_pass='stackops', nova_user='nova',
               nova_password='stackops'):
    setup_schema(username=nova_user, password=nova_password,
                 schema_name='nova', root_pass=root_pass)


def setup_glance(root_pass='stackops', glance_user='glance',
                 glance_password='stackops'):
    setup_schema(username=glance_user, password=glance_password,
                 schema_name='glance', root_pass=root_pass)


def setup_cinder(root_pass='stackops', cinder_user='cinder',
                 cinder_password='stackops'):
    setup_schema(username=cinder_user, password=cinder_password,
                 schema_name='cinder', root_pass=root_pass)


def setup_quantum(root_pass='stackops', quantum_user='quantum',
                  quantum_password='stackops'):
    setup_schema(username=quantum_user, password=quantum_password,
                 schema_name='quantum', root_pass=root_pass)


def setup_portal(root_pass='stackops', portal_user='portal',
                 portal_password='stackops'):
    setup_schema(username=portal_user, password=portal_password,
                 schema_name='portal', root_pass=root_pass)


def setup_accounting(root_pass='stackops', accounting_user='activity',
                     accounting_password='stackops'):
    setup_schema(username=accounting_user, password=accounting_password,
                 schema_name='activity', root_pass=root_pass)


def setup_chargeback(root_pass='stackops', chargeback_user='chargeback',
                     chargeback_password='stackops'):
    setup_schema(username=chargeback_user, password=chargeback_password,
                 schema_name='chargeback', root_pass=root_pass)


def setup_automation(root_pass='stackops', automation_user='automation',
                     automation_password='stackops'):
    setup_schema(username=automation_user, password=automation_password,
                 schema_name='stackopshead', root_pass=root_pass)


def configure_all_schemas(root_pass='stackops', password='stackops',
                          mysql_host='127.0.0.1'):
    setup_schema(username='portal', schema_name='portal', root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='keystone', schema_name='keystone',
                 root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='glance', schema_name='glance', root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='nova', schema_name='nova', root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='cinder', schema_name='cinder', root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='quantum', schema_name='quantum',
                 root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='quantum', schema_name='quantum',
                 root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='accounting', schema_name='accounting',
                 root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)
    setup_schema(username='automation', schema_name='automation',
                 root_pass=root_pass,
                 password=password, drop_previous=False, mysql_host=mysql_host)


def validate_database(database_type, username, password, host, port,
                      schema, drop_schema=None, install_database=None):
    fab = fabuloso.Fabuloso()
    fab.validate_database(database_type, username, password, host, port,
                          schema, drop_schema, install_database)
