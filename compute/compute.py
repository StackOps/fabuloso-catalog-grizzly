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
#   limitations under the License.
from fabric.api import *
from cuisine import *

import fabuloso.utils as utils

PAGE_SIZE = 2 * 1024 * 1024
BONUS_PAGES = 40

NOVA_COMPUTE_CONF = '/etc/nova/nova-compute.conf'

NOVA_CONF = '/etc/nova/nova.conf'

DEFAULT_LIBVIRT_BIN_CONF = '/etc/default/libvirt-bin'

LIBVIRT_BIN_CONF = '/etc/init/libvirt-bin.conf'

LIBVIRTD_CONF = '/etc/libvirt/libvirtd.conf'

LIBVIRT_QEMU_CONF = '/etc/libvirt/qemu.conf'

COMPUTE_API_PASTE_CONF = '/etc/nova/api-paste.ini'

QUANTUM_API_PASTE_CONF = '/etc/quantum/api-paste.ini'

OVS_PLUGIN_CONF = '/etc/quantum/plugins/openvswitch/ovs_quantum_plugin.ini'

QUANTUM_CONF = '/etc/quantum/quantum.conf'

NOVA_PATH = '/var/lib/nova'

NOVA_INSTANCES = '/var/lib/nova/instances'

NOVA_VOLUMES = '/var/lib/nova/volumes'


def stop():
    with settings(warn_only=True):
        quantum_plugin_openvswitch_agent_stop()
        ntp_stop()
        compute_stop()
        iscsi_initiator_stop()


def start():
    stop()
    ntp_start()
    iscsi_initiator_start()
    quantum_plugin_openvswitch_agent_start()
    compute_start()


def openvswitch_stop():
    with settings(warn_only=True):
        sudo("/etc/init.d/openvswitch-switch stop")


def openvswitch_start():
    openvswitch_stop()
    sudo("/etc/init.d/openvswitch-switch start")


def quantum_plugin_openvswitch_agent_stop():
    with settings(warn_only=True):
        sudo("service quantum-plugin-openvswitch-agent stop")


def quantum_plugin_openvswitch_agent_start():
    quantum_plugin_openvswitch_agent_stop()
    sudo("service quantum-plugin-openvswitch-agent start")


def ntp_stop():
    with settings(warn_only=True):
        sudo("service ntp stop")


def ntp_start():
    ntp_stop()
    sudo("service ntp start")


def iscsi_initiator_stop():
    with settings(warn_only=True):
        sudo("nohup service open-iscsi stop")


def iscsi_initiator_start():
    iscsi_initiator_stop()
    sudo("nohup service open-iscsi start")


def libvirt_stop():
    with settings(warn_only=True):
        sudo("nohup service libvirt-bin stop")


def libvirt_start():
    libvirt_stop()
    sudo("nohup service libvirt-bin start")

def compute_stop():
    libvirt_stop()
    with settings(warn_only=True):
        sudo("nohup service nova-compute stop")


def compute_start():
    compute_stop()
    libvirt_start()
    sudo("nohup service nova-compute start")


def configure_ubuntu_packages():
    """Configure compute packages"""
    package_ensure('python-amqp')
    package_ensure('python-software-properties')
    package_ensure('ntp')
    package_ensure('kvm')
    package_ensure('libvirt-bin')
    package_ensure('pm-utils')
    package_ensure('nova-compute-kvm')
    package_ensure('quantum-plugin-openvswitch-agent')
    package_ensure('open-iscsi')
    package_ensure('autofs')


def uninstall_ubuntu_packages():
    """Uninstall compute packages"""
    package_clean('python-amqp')
    package_clean('python-software-properties')
    package_clean('ntp')
    package_clean('kvm')
    package_clean('libvirt-bin')
    package_clean('pm-utils')
    package_clean('nova-compute-kvm')
    package_clean('quantum-plugin-openvswitch-agent')
    package_clean('open-iscsi')
    package_clean('autofs')


def install():
    """Generate compute configuration. Execute on both servers"""
    configure_ubuntu_packages()
    sudo('update-rc.d quantum-plugin-openvswitch-agent defaults 98 02')
    sudo('update-rc.d nova-compute defaults 98 02')


def configure_forwarding():
    sudo("sed -i -r 's/^\s*#(net\.ipv4\.ip_forward=1.*)"
         "/\\1/' /etc/sysctl.conf")
    sudo("echo 1 > /proc/sys/net/ipv4/ip_forward")


def configure_network(config_ovs_vlan="false", iface_bridge='eth1', br_postfix='bond-vm',
                      bridge_name=None,
                      bond_parameters='bond_mode=balance-slb '
                                      'other_config:bond-detect-mode=miimon '
                                      'other_config:bond-miimon-interval=100',
                      network_restart=False):

    if str(config_ovs_vlan).lower() == "true":
        openvswitch_start()
        configure_forwarding()
        with settings(warn_only=True):
            sudo('ovs-vsctl del-br br-%s' % br_postfix)
        sudo('ovs-vsctl add-br br-%s' % br_postfix)
        bonding = len(iface_bridge.split()) > 1
        if bonding:
            if bridge_name is not None:
                sudo('ovs-vsctl add-port br-%s %s -- set interface %s '
                     'type=internal' % (br_postfix, bridge_name, bridge_name))
            if network_restart:
                sudo('ovs-vsctl add-bond br-%s %s %s %s; reboot' %
                     (br_postfix, br_postfix, iface_bridge, bond_parameters))
            else:
                sudo('ovs-vsctl add-bond br-%s %s %s %s' %
                     (br_postfix, br_postfix, iface_bridge, bond_parameters))
        else:
            sudo('ovs-vsctl add-port br-%s %s' % (br_postfix, iface_bridge))

def configure_ntp(ntp_host='automation'):
    sudo('echo "server %s" > /etc/ntp.conf' % ntp_host)

def configure_vhost_net():
    sudo('modprobe vhost-net')
    sudo("sed -i '/modprobe vhost-net/d' /etc/rc.local")
    sudo("sed -i '/exit 0/d' /etc/rc.local")
    sudo("echo 'modprobe vhost-net' >> /etc/rc.local")
    sudo("echo 'exit 0' >> /etc/rc.local")

def configure_libvirt():
    utils.uncomment_property(LIBVIRT_QEMU_CONF, 'cgroup_device_acl')
    utils.modify_property(LIBVIRT_QEMU_CONF,
                          'cgroup_device_acl',
                          '["/dev/null", "/dev/full", "/dev/zero", '
                          '"/dev/random", "/dev/urandom", "/dev/ptmx", '
                          '"/dev/kvm", "/dev/kqemu", "/dev/rtc", "/dev/hpet"'
                          ',"/dev/net/tun"]')
    utils.uncomment_property(LIBVIRTD_CONF, 'listen_tls')
    utils.uncomment_property(LIBVIRTD_CONF, 'listen_tcp')
    utils.uncomment_property(LIBVIRTD_CONF, 'auth_tcp')
    utils.modify_property(LIBVIRTD_CONF, 'listen_tls', '0')
    utils.modify_property(LIBVIRTD_CONF, 'listen_tcp', '1')
    utils.modify_property(LIBVIRTD_CONF, 'auth_tcp', '"none"')
    utils.modify_property(LIBVIRT_BIN_CONF, 'env libvirtd_opts', '"-d -l"')
    utils.modify_property(DEFAULT_LIBVIRT_BIN_CONF, 'libvirtd_opts', '"-d -l"')
    with settings(warn_only=True):
        sudo('virsh net-destroy default')
        sudo('virsh net-undefine default')
    libvirt_start()

def configure_nova_compute(controller_host=None, public_ip=None, rabbit_password='guest', mysql_username='nova',
                    mysql_password='stackops', mysql_port='3306', mysql_schema='nova',
                    service_user='nova', service_tenant_name='service', service_pass='stackops',
                    auth_port='35357', auth_protocol='http', libvirt_type='kvm', vncproxy_port='6080',
                    glance_port='9292',rescue_image_id=''):
    if controller_host is None:
        puts("{error:'Controller IP of the node needed as argument'}")
        return

    quantum_url = 'http://%s:9696' % controller_host
    admin_auth_url = 'http://%s:35357/v2.0' % controller_host
    auth_host = controller_host
    mysql_host = controller_host
    vncproxy_host = public_ip
    glance_host = controller_host
    rabbit_host = controller_host

    utils.set_option(COMPUTE_API_PASTE_CONF, 'admin_tenant_name', service_tenant_name, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'admin_user', service_user, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'admin_password', service_pass, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'auth_host', auth_host, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'auth_port', auth_port, section='filter:authtoken')
    utils.set_option(COMPUTE_API_PASTE_CONF, 'auth_protocol', auth_protocol, section='filter:authtoken')

    utils.set_option(NOVA_COMPUTE_CONF, 'sql_connection',
                     utils.sql_connect_string(mysql_host, mysql_password,
                                              mysql_port, mysql_schema,
                                              mysql_username))
    utils.set_option(NOVA_COMPUTE_CONF, 'start_guests_on_host_boot', 'false')
    utils.set_option(NOVA_COMPUTE_CONF, 'resume_guests_state_on_host_boot',
                     'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'allow_same_net_traffic', 'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'allow_resize_to_same_host', 'True')

    utils.set_option(NOVA_COMPUTE_CONF, 'verbose', 'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'auth_strategy', 'keystone')
    utils.set_option(NOVA_COMPUTE_CONF, 'use_deprecated_auth', 'false')
    utils.set_option(NOVA_COMPUTE_CONF, 'logdir', '/var/log/nova')
    utils.set_option(NOVA_COMPUTE_CONF, 'state_path', '/var/lib/nova')
    utils.set_option(NOVA_COMPUTE_CONF, 'lock_path', '/var/lock/nova')
    utils.set_option(NOVA_COMPUTE_CONF, 'root_helper',
                     'sudo nova-rootwrap /etc/nova/rootwrap.conf')
    utils.set_option(NOVA_COMPUTE_CONF, 'notification_driver',
                     'nova.openstack.common.notifier.rabbit_notifier')
    utils.set_option(NOVA_COMPUTE_CONF, 'notification_topics',
                     'notifications,monitor')
    utils.set_option(NOVA_COMPUTE_CONF, 'default_notification_level', 'INFO')

    utils.set_option(NOVA_COMPUTE_CONF, 'connection_type', 'libvirt')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_type', libvirt_type)
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_ovs_bridge', 'br-int')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_vif_type', 'ethernet')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_vif_driver',
                     'nova.virt.libvirt.vif.LibvirtHybridOVSBridgeDriver')
    utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_use_virtio_for_bridges',
                     'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'quantum_auth_strategy',
                     'keystone')
    utils.set_option(NOVA_COMPUTE_CONF, 'quantum_admin_username',
                     'quantum')
    utils.set_option(NOVA_COMPUTE_CONF, 'quantum_admin_password',
                     'stackops')
    utils.set_option(NOVA_COMPUTE_CONF, 'quantum_admin_tenant_name',
                     'service')
    utils.set_option(NOVA_COMPUTE_CONF, 'quantum_admin_auth_url',
                     admin_auth_url)
    utils.set_option(NOVA_COMPUTE_CONF, 'quantum_url',
                     quantum_url)

    utils.set_option(NOVA_COMPUTE_CONF, 'novncproxy_base_url',
                     'http://%s:%s/vnc_auto.html'
                     % (vncproxy_host, vncproxy_port))
    utils.set_option(NOVA_COMPUTE_CONF, 'vncserver_listen', '0.0.0.0')
    utils.set_option(NOVA_COMPUTE_CONF, 'vnc_enable', 'true')
    utils.set_option(NOVA_COMPUTE_CONF, 'vncserver_proxyclient_address', "$my_ip")

    utils.set_option(NOVA_COMPUTE_CONF, 'compute_driver',
                     'libvirt.LibvirtDriver')

    utils.set_option(NOVA_COMPUTE_CONF, 'image_service',
                     'nova.image.glance.GlanceImageService')
    utils.set_option(NOVA_COMPUTE_CONF, 'glance_api_servers',
                     '%s:%s' % (glance_host, glance_port))

    utils.set_option(NOVA_COMPUTE_CONF, 'rabbit_host', rabbit_host)
    utils.set_option(NOVA_COMPUTE_CONF, 'rabbit_password', rabbit_password)

    utils.set_option(NOVA_COMPUTE_CONF, 'ec2_private_dns_show_ip', 'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'network_api_class',
                     'nova.network.quantumv2.api.API')
    utils.set_option(NOVA_COMPUTE_CONF, 'dmz_cidr', '169.254.169.254/32')
    utils.set_option(NOVA_COMPUTE_CONF, 'volume_api_class',
                     'nova.volume.cinder.API')
    utils.set_option(NOVA_COMPUTE_CONF, 'cinder_catalog_info',
                     'volume:cinder:internalURL')

    # TOTHINK if its necessary
    utils.set_option(NOVA_COMPUTE_CONF, 'service_quantum_metadata_proxy',
                     'True')
    utils.set_option(NOVA_COMPUTE_CONF, 'quantum_metadata_proxy_shared_secret',
                     'password')

    utils.set_option(NOVA_COMPUTE_CONF, 'nfs_mount_point_base', NOVA_VOLUMES)

    utils.set_option(NOVA_COMPUTE_CONF, 'rescue_image_id', rescue_image_id)

    start()


def configure_quantum(rabbit_password='guest', rabbit_host='127.0.0.1'):
    utils.set_option(QUANTUM_CONF, 'core_plugin',
                     'quantum.plugins.openvswitch.ovs_quantum_plugin.'
                     'OVSQuantumPluginV2')
    utils.set_option(QUANTUM_CONF, 'auth_strategy', 'keystone')
    utils.set_option(QUANTUM_CONF, 'fake_rabbit', 'False')
    utils.set_option(QUANTUM_CONF, 'rabbit_password', rabbit_password)
    utils.set_option(QUANTUM_CONF, 'rabbit_host', rabbit_host)
    utils.set_option(QUANTUM_CONF, 'notification_driver',
                     'nova.openstack.common.notifier.rabbit_notifier')
    utils.set_option(QUANTUM_CONF, 'notification_topics',
                     'notifications,monitor')
    utils.set_option(QUANTUM_CONF, 'default_notification_level', 'INFO')
    quantum_plugin_openvswitch_agent_start()

def configure_ovs_plugin_gre(config_ovs_gre="true", mysql_host=None, tunnel_ip=None, mysql_quantum_username='quantum', tunnel_start='1',tunnel_end='1000',
                         mysql_quantum_password='stackops', mysql_port='3306', mysql_quantum_schema='quantum'):
    if str(config_ovs_gre).lower() == "true":
        utils.set_option(OVS_PLUGIN_CONF,'sql_connection',utils.sql_connect_string(mysql_host, mysql_quantum_password, mysql_port, mysql_quantum_schema, mysql_quantum_username),section='DATABASE')
        utils.set_option(OVS_PLUGIN_CONF,'reconnect_interval','2',section='DATABASE')
        utils.set_option(OVS_PLUGIN_CONF,'tenant_network_type','gre',section='OVS')
        utils.set_option(OVS_PLUGIN_CONF,'tunnel_id_ranges','%s:%s' % (tunnel_start,tunnel_end),section='OVS')
        utils.set_option(OVS_PLUGIN_CONF,'local_ip', tunnel_ip, section='OVS')
        utils.set_option(OVS_PLUGIN_CONF,'integration_bridge','br-int',section='OVS')
        utils.set_option(OVS_PLUGIN_CONF,'tunnel_bridge','br-tun',section='OVS')
        utils.set_option(OVS_PLUGIN_CONF,'enable_tunneling','True',section='OVS')
        utils.set_option(OVS_PLUGIN_CONF,'root_helper','sudo /usr/bin/quantum-rootwrap /etc/quantum/rootwrap.conf',section='AGENT')
        with settings(warn_only=True):
            sudo('ovs-vsctl del-br br-int')
        sudo('ovs-vsctl add-br br-int')
        quantum_plugin_openvswitch_agent_start()

def configure_ovs_plugin_vlan(config_ovs_vlan="false",
                              br_postfix='bond-vm',
                              vlan_start='2',
                              vlan_end='4094',
                              mysql_quantum_username='quantum',
                              mysql_quantum_password='stackops',
                              mysql_host='127.0.0.1',
                              mysql_port='3306', mysql_quantum_schema='quantum'):
    if str(config_ovs_vlan).lower() == "true":
        utils.set_option(OVS_PLUGIN_CONF, 'sql_connection',
                         utils.sql_connect_string(mysql_host,
                                                  mysql_quantum_password,
                                                  mysql_port, mysql_quantum_schema,
                                                  mysql_quantum_username),
                         section='DATABASE')
        utils.set_option(OVS_PLUGIN_CONF, 'reconnect_interval', '2',
                         section='DATABASE')
        utils.set_option(OVS_PLUGIN_CONF, 'tenant_network_type',
                         'vlan', section='OVS')
        utils.set_option(OVS_PLUGIN_CONF, 'network_vlan_ranges', 'physnet1:%s:%s'
                         % (vlan_start, vlan_end), section='OVS')
        utils.set_option(OVS_PLUGIN_CONF, 'bridge_mappings',
                         'physnet1:br-%s' % br_postfix, section='OVS')
        utils.set_option(OVS_PLUGIN_CONF, 'root_helper',
                         'sudo /usr/bin/quantum-rootwrap '
                         '/etc/quantum/rootwrap.conf', section='AGENT')
        with settings(warn_only=True):
            sudo('ovs-vsctl del-br br-int')
        sudo('ovs-vsctl add-br br-int')
        quantum_plugin_openvswitch_agent_start()

def configure_nfs_storage(config_nfs_storage="false",
                          nfs_mountpoint="localhost:/mnt",
                          delete_content=False,
                          set_nova_owner=True,
                          nfs_server_mount_point_params='defaults'):
    if str(config_nfs_storage).lower() == "true":
        package_ensure('nfs-common')
        package_ensure('autofs')
        utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_type', 'default')
        if delete_content:
            sudo('rm -fr %s' % NOVA_INSTANCES)
            sudo('rm -fr %s' % NOVA_VOLUMES)
        stop()
        nova_instance_exists = file_exists(NOVA_INSTANCES)
        nova_volumes_exists = file_exists(NOVA_VOLUMES)
        if not nova_instance_exists:
            sudo('mkdir -p %s' % NOVA_INSTANCES)
        if not nova_volumes_exists:
            sudo('mkdir -p %s' % NOVA_VOLUMES)
        mpoint = '%s  -fstype=nfs,vers=3,%s   %s' % \
                 (NOVA_INSTANCES, nfs_server_mount_point_params, nfs_mountpoint)
        sudo('''echo "/-    /etc/auto.nfs" > /etc/auto.master''')
        sudo('''echo "%s" > /etc/auto.nfs''' % mpoint)
        sudo('service autofs restart')
        with settings(warn_only=True):
            if set_nova_owner:
                if not nova_instance_exists:
                    sudo('chown nova:nova -R %s' % NOVA_INSTANCES)
                if not nova_volumes_exists:
                    sudo('chown nova:nova -R %s' % NOVA_VOLUMES)
        start()

def configure_local_storage(config_local_storage="true", delete_content=False, set_nova_owner=True):
    if str(config_local_storage).lower() == "true":
        utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_type', 'default')
        if delete_content:
            sudo('rm -fr %s' % NOVA_INSTANCES)
        stop()
        sudo('sed -i "#%s#d" /etc/fstab' % NOVA_INSTANCES)
        sudo('mkdir -p %s' % NOVA_INSTANCES)
        if set_nova_owner:
            sudo('chown nova:nova -R %s' % NOVA_INSTANCES)
        start()

def configure_lvm_storage(config_lvm_storage="false", lvm_vgroup_name='nova-volume',lvm_sparse='true', lvm_partition='/dev/sdb', lvm_force_delete="false"):
    if str(config_lvm_storage).lower() == "true":
        if str(lvm_force_delete).lower() == "true":
            sudo('vgremove -f %s' % lvm_vgroup_name)
            sudo('pvcreate -ff -y %s' % lvm_partition)
            sudo('vgcreate %s %s' % (lvm_vgroup_name, lvm_partition))
        utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_type', 'lvm')
        utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_images_volume_group', lvm_vgroup_name)
        utils.set_option(NOVA_COMPUTE_CONF, 'libvirt_sparse_logical_volumes', lvm_sparse)
        start()

def set_option(property='',value=''):
    utils.set_option(NOVA_COMPUTE_CONF, property, value)
