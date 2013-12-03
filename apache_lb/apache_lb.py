# -*- coding: utf-8 -*-

import os.path

from fabric.api import sudo
from fabric.contrib import files

from cuisine import (
    package_ensure, file_exists, file_attribs, file_attribs_get,
    mode_sudo)

CONF_FILE = '/etc/apache2/sites-available/default'
OWNER = {
    'owner': 'root',
    'group': 'root'
}


def install_apache():
    package_ensure('apache2')


def configure_apache(members, bind_address='*', bind_port=80,
                     common_name='127.0.0.1', lbmethod='byrequests'):

    sudo('a2enmod proxy_http')
    sudo('a2enmod proxy_balancer')

    template_ensure('default.conf',
                    CONF_FILE,
                    context={
                        'members': members,
                        'bind_address': bind_address,
                        'bind_port': bind_port,
                        'common_name': common_name,
                        'lbmethod': lbmethod
                    },
                    mode=0644,
                    use_sudo=True)

    with mode_sudo():
        file_attribs(CONF_FILE, **OWNER)

    sudo('service apache2 restart')


def template_ensure(filename, destination, **kwargs):
    files.upload_template(
        filename,
        destination,
        use_jinja=True,
        template_dir=os.path.join(os.path.dirname(__file__), 'templates'),
        **kwargs)

# Validations

from expects import expect


def validate_apache_config():
    _expect_file_exists(CONF_FILE)
    _expect_owner(CONF_FILE, OWNER)
    _expect_mode(CONF_FILE, '644')


def _expect_file_exists(path):
    expect(file_exists(path)).to.be.true


def _expect_owner(path, owner):
    attribs = file_attribs_get(path)

    expect(attribs).to.have.keys(owner)

def _expect_mode(path, mode):
    attribs = file_attribs_get(path)

    expect(attribs).to.have.key('mode', mode)
