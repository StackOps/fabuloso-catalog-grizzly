# -*- coding: utf-8 -*-

import os.path

from cuisine import *


def _random_token():
    import hashlib
    import random

    return hashlib.sha512(str(random.getrandbits(16))).hexdigest()[:8]

DEFAULT = {
    'swift_hash_path_prefix': _random_token(),
    'swift_hash_path_suffix': _random_token()
}

CONF_DIR = '/etc/swift'
CONF_FILE = 'swift.conf'
OWNER = {
    'owner': 'swift',
    'group': 'swift'
}


def install_common_packages():
    # TODO(jaimegildesagredo): Remove this line when swift is packaged
    #                          in the stackops repos

    _ensure_cloud_repos()

    package_ensure('swift')


def install_common_config(
    swift_hash_path_prefix=DEFAULT['swift_hash_path_prefix'],
    swift_hash_path_suffix=DEFAULT['swift_hash_path_suffix']):

    with mode_sudo():
        dir_ensure(CONF_DIR, **OWNER)

    data = dict(
        swift_hash_path_suffix=swift_hash_path_suffix,
        swift_hash_path_prefix=swift_hash_path_prefix
    )

    config = _template(CONF_FILE, data)

    with cd(CONF_DIR):
        with mode_sudo():
            file_write(CONF_FILE, config, **OWNER)


def _ensure_cloud_repos():
    repository_ensure_apt("'deb http://ubuntu-cloud.archive.canonical.com/ubuntu precise-updates/grizzly main'")
    package_ensure('ubuntu-cloud-keyring')
    package_update()


def _template(name, data):
    return _get_template(name).format(**data)


def _get_template(name):
    template_path = os.path.join(os.path.dirname(__file__), 'templates', name)

    with open(template_path) as template:
        return template.read()


# Validations

from expects import expect

def validate_common_config():
    _expect_dir_exists(CONF_DIR)
    _expect_owner(CONF_DIR, OWNER)

    with cd(CONF_DIR):
        _expect_file_exists(CONF_FILE)
        _expect_owner(CONF_FILE, OWNER)


def _expect_dir_exists(path):
    expect(dir_exists(path)).to.be.true


def _expect_file_exists(path):
    expect(file_exists(path)).to.be.true


def _expect_owner(path, owner):
    attribs = file_attribs_get(path)

    expect(attribs).to.have.keys(owner)
