# coding:utf-8
#!/usr/bin/env python
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
try:  #ansible < 2.4
    ANSIBLE_VERSION = "2.2"
    from ansible.vars import VariableManager
    from ansible.inventory import Inventory
except:  #ansible > 2.4
    ANSIBLE_VERSION = "2.4"
    from ansible.Inventory import Inventory
    from ansible.vars.manager import VariableManager
    from ansible.inventory.manager import InventoryManager
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
from ansible.errors import AnsibleError
from ansible.inventory.group import Group
from ansible.inventory.host import Host
from ansible.playbook.play import Play
import traceback
import mysql_db, get_ip_show_type, config, crypto
import os, json, sys, time
import tempfile
import logging

_logger = logging.getLogger(__name__)

from ops_django.settings import RUN_MODE



class ResultCallback(CallbackBase):
    """结果回调"""
    def __init__(self, *args, **kwargs):
        self.history_id = kwargs.get('history_id', None)
        try:
            kwargs.pop('history_id')
        except Exception:
            pass
        super(ResultCallback, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

        self.ret = {
            'host_ok': {},
            'host_unreachable': {},
            'host_failed': {}
        }

    def update_result(self):
        c = config.config('mysql.ini')
        db_name = c.getOption(RUN_MODE, 'dbname')
        with mysql_db.conn_dbpool(db_name, RUN_MODE) if RUN_MODE == 'DEPLOY' else mysql_db.conn_dbpool(db_name,
                                                                                                       "LOCAL") as _db:
            data = [(
                json.dumps(self.ret),
                self.history_id
            )]
            try:
                _db.executemany("update ops_job_script_history set result=%s where id=%s", data)
            except:
                print traceback.format_exc()

    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()] = result
        if not self.history_id is None:
            self.update_result()
        self.ret['host_unreachable'] = {result._host.name: result._result}

    def v2_runner_on_ok(self, result, *args, **kwargs):
        self.host_ok[result._host.get_name()] = result
        if not self.history_id is None:
            self.update_result()
        self.ret['host_ok'] = {result._host.name: result._result}

    def v2_runner_on_failed(self, result, *args, **kwargs):
        self.host_failed[result._host.get_name()] = result
        if not self.history_id is None:
            self.update_result()
        self.ret['host_failed'] = {result._host.name: result._result}

    def runner_on_skipped(self, result, *args, **kwargs):
        self.host_failed[result._host.get_name()] = result
        if not self.history_id is None:
            self.update_result()
        self.ret['host_failed'] = {result._host.name: result._result}

    def runner_on_async_failed(self, result, *args, **kwargs):
        self.host_failed[result._host.get_name()] = result
        if not self.history_id is None:
            self.update_result()
        self.ret['host_failed'] = {result._host.name: result._result}


def AnsibleTempSource():
    '''
    数据库获取ansible resource
    :return:
    '''
    c = config.config('mysql.ini')
    db_name = c.getOption(RUN_MODE, 'dbname')
    ip_show_type = get_ip_show_type.get_show_type()
    with mysql_db.conn_dbpool(db_name, RUN_MODE) if RUN_MODE == 'DEPLOY' else mysql_db.conn_dbpool(db_name, "LOCAL") as _db:
        ssh_info = _db.select("select * from cmdb_ansible_ssh_info;")
        ips = [i['outer_addr_ip' if ip_show_type == 'outer_ip' else 'inner_addr_ip'] for i in ssh_info]
        # 查询没有记录ansible信息的主机，使用默认配置
        sql = "select * from cmdb_tree_node where node_name not in ('%s') and node_type='ip';" % "','".join(ips)
        other_host = _db.select(sql)
        other_host = [i['node_name'] for i in other_host]

    resource = list()
    for i in ssh_info:
        try:
            resource.append({
                "hostname": i['outer_addr_ip'],
                "port": 22 if not i['ansible_ssh_port'] else int(i['ansible_ssh_port']),
                "username": "root" if not i['ansible_ssh_user'] else i['ansible_ssh_user'],
                "password": crypto.passwd_deaes(i['ansible_sudo_pass']),
                "ip": i['outer_addr_ip'] if ip_show_type == 'outer_ip' else i['inner_addr_ip'],
            })
            for ip in other_host:
                resource.append({
                    "hostname": ip,
                    "port": 22,
                    "username": "root",
                    "password": '',
                    "ip": ip,
                })
        except Exception:
            print traceback.format_exc()
            raise AnsibleError
    return resource

class MyInventory(Inventory):
    """
    this is my ansible inventory object.
    """
    def __init__(self, loader, variable_manager):
        """
        resource的数据格式是一个列表字典，比如
            {
                "group1": {
                    "hosts": [{"hostname": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...],
                    "vars": {"var1": value1, "var2": value2, ...}
                }
            }

        如果你只传入1个列表，这默认该列表内的所有主机属于my_group组,比如
            [{"hostname": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...]
        """

        self.resource = AnsibleTempSource()
        self.inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=[])
        self.gen_inventory()

    def my_add_group(self, hosts, groupname, groupvars=None):
        """
        add hosts to a group
        """
        my_group = Group(name=groupname)

        # if group variables exists, add them to group
        if groupvars:
            for key, value in groupvars.iteritems():
                my_group.set_variable(key, value)

                # add hosts to group
        for host in hosts:
            # set connection variables
            hostname = host.get("hostname", '')
            hostip = host.get('ip', hostname)
            hostport = host.get("port", 22)
            username = host.get("username", 'root')
            password = host.get("password", '')
            my_host = Host(name=hostname, port=hostport)
            if hostip not in ['', None]:
                my_host.set_variable('ansible_ssh_ip', hostip)
            if hostport not in ['', None]:
                my_host.set_variable('ansible_ssh_port', hostport)
            if username not in ['', None]:
                my_host.set_variable('ansible_ssh_user', username)
            if password not in ['', None]:
                my_host.set_variable('ansible_sudo_pass', password)

            # set other variables
            for key, value in host.iteritems():
                if key not in ["hostname", "port", "username", "password"]:
                    my_host.set_variable(key, value)
                    # add to group
            my_group.add_host(my_host)

        self.inventory.add_group(my_group)

    def gen_inventory(self):
        """
        add hosts to inventory.
        """
        if isinstance(self.resource, list):
            self.my_add_group(self.resource, 'default_group')
        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.iteritems():
                self.my_add_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))


class AnsibleApi(object):

    def __init__(self, become=False, become_method=None, become_user=None, history_id=None):
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.inventory = None
        self.variable_manager = None
        self.loader = None
        self.options = None
        self.passwords = None
        self.callback = None
        self.history_id = history_id
        self.__initializeData()
        self.results_raw = {}

    def __initializeData(self):
        '''
        创建参数，为保证每个参数都被设置，ansible使用可命名元组
        '''
        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'timeout',
                                         'ask_pass', 'ssh_common_args',
                                         'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args', 'become', 'become_method',
                                         'become_user', 'ask_value_pass', 'verbosity', 'check', 'listhosts',
                                         'listtasks', 'listtags', 'syntax'])
        '''初始化loader类'''
        self.loader = DataLoader()  # 用于读取与解析yaml和json文件
        self.passwords = dict(vault_pass='secret')

        self.options = Options(connection='ssh', module_path='/to/mymodules', forks=100, timeout=10,
                               ask_pass=False, ssh_common_args='',
                               ssh_extra_args='', sftp_extra_args='', scp_extra_args='', become=self.become, become_method=self.become_method,
                               become_user=self.become_user, ask_value_pass=False, verbosity=None, check=False, listhosts=False,
                               listtasks=False, listtags=False, syntax=False)
        self.variable_manager = VariableManager()
        self.passwords = dict(vault_pass='secret')
        self.inventory = MyInventory(self.loader, self.variable_manager).inventory
        self.variable_manager.set_inventory(self.inventory)

    def run(self, host_list, module_name, module_args):
        """
        run module from andible ad-hoc.
        module_name: ansible module_name
        module_args: ansible module args
        """
        # create play with tasks
        try:
            play_source = dict(
                name="Ansible Play",
                hosts=host_list,
                gather_facts='no',
                tasks=[dict(action=dict(module=module_name, args=module_args))]
            )
            play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

            # actually run it
            tqm = None
            self.callback = ResultCallback(history_id=self.history_id)
            try:
                tqm = TaskQueueManager(
                    inventory=self.inventory,
                    variable_manager=self.variable_manager,
                    loader=self.loader,
                    options=self.options,
                    passwords=self.passwords,
                )
                tqm._stdout_callback = self.callback
                tqm.run(play)
            finally:
                if tqm is not None:
                    tqm.cleanup()
        except Exception:
            print traceback.format_exc()
            raise AnsibleError

    def run_playbook(self, host_list, role_name, role_uuid, temp_param):
        """
        run ansible palybook
        """
        try:
            self.callback = ResultCallback(history_id=self.history_id)
            filenames = ['' + '/handlers/ansible/v1_0/sudoers.yml']  # playbook的路径
            template_file = ''  # 模板文件的路径
            if not os.path.exists(template_file):
                sys.exit()

            extra_vars = {}  # 额外的参数 sudoers.yml以及模板中的参数，它对应ansible-playbook test.yml --extra-vars "host='aa' name='cc' "
            host_list_str = ','.join([item for item in host_list])
            extra_vars['host_list'] = host_list_str
            extra_vars['username'] = role_name
            extra_vars['template_dir'] = template_file
            extra_vars['command_list'] = temp_param.get('cmdList')
            extra_vars['role_uuid'] = 'role-%s' % role_uuid
            self.variable_manager.extra_vars = extra_vars
            # actually run it
            executor = PlaybookExecutor(
                playbooks=filenames, inventory=self.inventory, variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options, passwords=self.passwords,
            )
            executor._tqm._stdout_callback = self.callback
            executor.run()
        except Exception as e:
            print "error:", e.message

    def _get_result(self):
        return self.callback.ret

class AnsiInterface(AnsibleApi):
    def __init__(self, *args, **kwargs):
        super(AnsiInterface, self).__init__(*args, **kwargs)

    def copy_file(self, host_list, src=None, dest=None):
        """
        copy file
        """
        module_args = "src=%s  dest=%s"%(src, dest)
        self.run(host_list, 'copy', module_args)
        result = self._get_result()
        return result

    def make_dir(self, host_list, dir):
        '''
        file
        '''
        module_args = 'path=%s state=directory' % dir
        self.run(host_list, 'file', module_args)
        result = self._get_result()
        return result

    def exec_shell(self, host_list, sh):
        """
        commands
        """
        self.run(host_list, 'shell', sh)
        result = self._get_result()
        return result

    def exec_command(self, host_list, cmds):
        """
        commands
        """
        self.run(host_list, 'command', cmds)
        result = self._get_result()
        return result

    def exec_script(self, host_list, path):
        """
        在远程主机执行shell命令或者.sh脚本
        """
        self.run(host_list, 'shell', path)
        result = self._get_result()
        return result

    def sync_authorized_key(self, host_list, keyargs):
        """
        同步远程主机authkey
        """
        self.run(host_list, 'authorized_key', keyargs)
        result = self._get_result()
        return result

    class asnible_script_temp_file():
        def __init__(self, script_name):
            '''
            获取脚本内容
            '''
            c = config.config('mysql.ini')
            db_name = c.getOption(RUN_MODE, 'dbname')
            with mysql_db.conn_dbpool(db_name, RUN_MODE) if RUN_MODE == 'DEPLOY' else mysql_db.conn_dbpool(db_name,
                                                                                                           "LOCAL") as _db:
                script = _db.select("select * from ops_job_job_script_info where script_name='%s';" % script_name)
            if not len(script) == 1:
                print "Found no script as %s" % script_name
                raise Exception
            else:
                self.script_content = script[0]['script_content']
            self.temp = tempfile.mktemp()
            with open(self.temp, "wb") as f:
                f.write(self.script_content)

        def get_tmp_file(self):
            return self.temp

        def remove_tmp_file(self):
            os.remove(self.temp)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.remove_tmp_file()

    class asnible_args_temp_file():
        def __init__(self, content):
            '''
            脚本参数文件
            :param content:
            '''
            self.temp = tempfile.mktemp()
            with open(self.temp, "wb") as f:
                f.write(content)

        def get_tmp_file(self):
            return self.temp

        def remove_tmp_file(self):
            os.remove(self.temp)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.remove_tmp_file()


    def exec_script_all_type(self, host_list, script_name, script_args='', args_type='normal'):
        """
        在远程主机执行shell命令或者.sh脚本
        """
        TmpFileName = "%s" % int(time.time())
        AnsibleTmpPath = "/data/.ansible_script_tmp/"
        if args_type == 'file':
            with self.asnible_args_temp_file(script_args) as args_file_handler:
                args_file = args_file_handler.get_tmp_file()
                args_file_name = TmpFileName
                script_args = "%s%s" % (AnsibleTmpPath, args_file_name)
                self.run(host_list, 'copy', 'src=%s dest=%s%s owner=root group=root mode=0755' % (args_file, AnsibleTmpPath, args_file_name))

        with self.asnible_script_temp_file(script_name) as script_file_handler:
            script_file = script_file_handler.get_tmp_file()
            TmpFileName = "%s.sh" % TmpFileName
            self.run(host_list, 'file', 'path=%s state=directory mode=0777' % AnsibleTmpPath)
            self.run(host_list, 'shell', 'chmod 777 %s' % AnsibleTmpPath)
            self.run(host_list, 'copy', 'src=%s dest=%s%s owner=root group=root mode=0755' % (script_file, AnsibleTmpPath, TmpFileName))
            self.run(host_list, 'shell', 'chmod 0755 %s%s' % (AnsibleTmpPath, TmpFileName))
            self.run(host_list, 'shell', 'cd %s && ./%s %s' % (AnsibleTmpPath, TmpFileName, script_args))
            result = self._get_result()
        return result

if __name__ == "__main__":
    interface = AnsiInterface()
    print "shell: ", interface.exec_script_all_type(['39.107.35.128'], 'new_script_1543900022000.sh')