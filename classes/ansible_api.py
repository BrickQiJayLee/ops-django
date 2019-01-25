# coding:utf-8
#!/usr/bin/env python
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
from ansible.errors import AnsibleError
from ansible.playbook.play import Play
import traceback
import mysql_db, get_ip_show_type, config, crypto
import os, json, sys, time
import tempfile
import logging

_logger = logging.getLogger(__name__)

from ops_django.settings import RUN_MODE



"""
 2019-01-25 更新: 废弃ansible 2.2
"""


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
        with mysql_db.conn_db(db_name, RUN_MODE) if RUN_MODE == 'DEPLOY' else mysql_db.conn_db(db_name,
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
    with mysql_db.conn_db(db_name, RUN_MODE) if RUN_MODE == 'DEPLOY' else mysql_db.conn_db(db_name, "LOCAL") as _db:
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
                "hostname": i['outer_addr_ip'] if ip_show_type == 'outer_ip' else i['inner_addr_ip'],
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


class AnsibleTempFile():
    def __init__(self):
        '''
        数据库获取ansible变量到临时文件
        :return:
        '''
        c = config.config('mysql.ini')
        db_name = c.getOption(RUN_MODE, 'dbname')
        ip_show_type = get_ip_show_type.get_show_type()
        with mysql_db.conn_db(db_name, RUN_MODE) if RUN_MODE == 'DEPLOY' else mysql_db.conn_db(db_name, "LOCAL") as _db:
            ssh_info = _db.select("select * from cmdb_ansible_ssh_info;")
        inv_list = list()
        for i in ssh_info:
            str = i['outer_addr_ip'] if ip_show_type == 'outer_ip' else i['inner_addr_ip']
            str = "%s ansible_ssh_user=%s" % (str, i['ansible_ssh_user'] if i['ansible_ssh_user'] != '' else 'root')
            str = "%s%s" % (str, " ansible_ssh_port={0}".format(i['ansible_ssh_port']) if i['ansible_ssh_port'] != '' else '')
            str = "%s%s" % (str, " ansible_sudo_pass={0}".format(crypto.passwd_deaes(i['ansible_sudo_pass'])) if i['ansible_sudo_pass'] != '' else '')
            inv_list.append(str)
        inv = '[AllResource]'
        inv = "%s\n%s" % (inv, '\n'.join(inv_list))
        self.temp = tempfile.mktemp()
        with open(self.temp, "wb") as f:
            f.write(inv)
            f.close()

    def get_tmp_file(self):
        """
        获得临时文件
        :return:
        """
        return self.temp

    def remove_tmp_file(self):
        """
        删除临时文件
        :return:
        """
        try:
            os.remove(self.temp)
        except:
            pass


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
        self.history_id = history_id
        self.callback = ResultCallback(history_id=self.history_id)
        self.__initializeData()

    def __initializeData(self):
        '''
        创建参数，为保证每个参数都被设置，ansible使用可命名元组
        '''
        '''初始化loader类'''
        self.loader = DataLoader()  # 用于读取与解析yaml和json文件
        self.passwords = dict(vault_pass='secret')
        self.Options = namedtuple('Options',
                                  ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user',
                                   'check', 'diff'])
        self.options = self.Options(connection='ssh', module_path='/to/mymodules', forks=30, become=self.become,
                                    become_method=self.become_method, become_user=self.become_user, check=False, diff=False)

        self.tmp_file_handler = AnsibleTempFile()
        self.tmp_source = self.tmp_file_handler.get_tmp_file()
        self.inventory = InventoryManager(loader=self.loader, sources=self.tmp_source)
        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

    def run(self, host_list, module_name, module_args):
        """
        run module from andible ad-hoc.
        module_name: ansible module_name
        module_args: ansible module args
        """
        # create play with tasks
        try:
            '''run after _init_task'''
            play_source = dict(
                name="Ansible Play",
                hosts=host_list,
                gather_facts='no',
                tasks=[dict(action=dict(module=module_name, args=module_args))]
            )
            play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)
            tqm = None
            try:
                tqm = TaskQueueManager(
                    inventory=self.inventory,
                    variable_manager=self.variable_manager,
                    loader=self.loader,
                    options=self.options,
                    passwords=self.passwords,
                    stdout_callback=self.callback
                    # Use our custom callback instead of the ``default`` callback plugin, which prints to stdout
                )
                tqm._stdout_callback = self.callback
                tqm.run(play)
            except Exception, e:
                print traceback.format_exc()
                _logger.error("ansible error: %s, %s " % (e, traceback.format_exc()))
            finally:
                # Remove ansible tmp file
                self.tmp_file_handler.remove_tmp_file()
                if tqm is not None:
                    tqm.cleanup()
        except(Exception):
            print traceback.format_exc()
            print self.callback
            #raise AnsibleError

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
            with mysql_db.conn_db(db_name, RUN_MODE) if RUN_MODE == 'DEPLOY' else mysql_db.conn_db(db_name,
                                                                                                           "LOCAL") as _db:
                script = _db.select("select * from ops_job_job_script_info where script_name='%s';" % script_name)
            if not len(script) == 1:
                print "Found no script as %s" % script_name
                raise Exception
            else:
                self.script_content = script[0]['script_content']
            self.temp = tempfile.mktemp()
            with open(self.temp, "wb") as f:
                f.write(self.script_content.encode('UTF-8'))

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
                f.write(content.encode('UTF-8'))

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
        print result
        return result
