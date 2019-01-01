# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class CmdbPool(models.Model):   #设备资源池
    inner_addr_ip = models.CharField(db_column='Inner_Addr_IP', max_length=32)  # Field name made lowercase.
    outer_addr_ip = models.CharField(db_column='Outer_Addr_IP', max_length=32, blank=True, null=True)  # Field name made lowercase.
    operating_system = models.CharField(db_column='Operating_System', max_length=32, blank=True, null=True)  # Field name made lowercase.
    status = models.CharField(db_column='Status', max_length=32, blank=True, null=True)  # Field name made lowercase.
    region = models.CharField(db_column='Region', max_length=32, blank=True, null=True)  # Field name made lowercase.
    available_zone = models.CharField(db_column='Available_Zone', max_length=32, blank=True, null=True)  # Field name made lowercase.
    cpu_info = models.IntegerField(db_column='CPU_Info', blank=True, null=True)  # Field name made lowercase.
    memory_info = models.IntegerField(db_column='Memory_Info', blank=True, null=True)  # Field name made lowercase.
    expire_time = models.DateTimeField(db_column='Expire_Time', blank=True, null=True)  # Field name made lowercase.
    create_time = models.DateTimeField(db_column='Create_Time', blank=True, null=True, auto_now_add=True)  # Field name made lowercase.
    update_time = models.DateTimeField(db_column='Update_Time', blank=True, null=True, auto_now=True)  # Field name made lowercase.

    class Meta:
        #managed = False
        db_table = 'cmdb_pool'

class CmdbTreeNode(models.Model):    #业务目录结构
    product_id = models.IntegerField(blank=True, null=True)
    node_name = models.CharField(max_length=32, blank=True, null=True)
    environment = models.CharField(max_length=32, blank=True, null=True)
    service_info = models.TextField(blank=True, null=True)
    depth = models.IntegerField(blank=True, null=True)
    father_id = models.IntegerField(blank=True, null=True)
    create_time = models.DateTimeField(db_column='Create_Time', blank=True, null=True, auto_now_add=True)  # Field name made lowercase.
    update_time = models.DateTimeField(db_column='Update_Time', blank=True, null=True, auto_now=True)  # Field name made lowercase.
    node_type = models.CharField(max_length=32, blank=True, null=True)
    tag = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'cmdb_tree_node'

class CmdbProductInfo(models.Model):
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=32)
    develop = models.TextField(blank=True, null=True)
    ops = models.TextField(blank=True, null=True)
    test = models.TextField(blank=True, null=True)

    class Meta:
        #managed = False
        db_table = 'cmdb_product_info'


class CmdbAnsibleSshInfo(models.Model):
    inner_addr_ip = models.CharField(max_length=32)   # ip
    outer_addr_ip = models.CharField(max_length=32)   # ip
    ansible_ssh_user = models.CharField(max_length=32)   # login user
    ansible_ssh_port = models.CharField(max_length=32)    # ssh port
    ansible_sudo_pass = models.CharField(max_length=255)    # su pass

    class Meta:
        #managed = False
        db_table = 'cmdb_ansible_ssh_info'

class CmdbUserSshAuth(models.Model):
    username = models.CharField(max_length=32)
    user_key = models.TextField(blank=True, null=True)
    related_node = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=32, blank=True, null=True)
    create_time = models.DateTimeField(db_column='Create_Time', blank=True, null=True,
                                       auto_now_add=True)  # Field name made lowercase.
    update_time = models.DateTimeField(db_column='Update_Time', blank=True, null=True,
                                       auto_now=True)  # Field name made lowercase.
    special_ip = models.TextField(blank=True, null=True)  # special

    class Meta:
        #managed = False
        db_table = 'cmdb_user_ssh_auth'