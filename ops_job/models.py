# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.


# 脚本库
class OpsJobJobScriptInfo(models.Model):
    job_name = models.CharField(max_length=32)  # job name
    script_name = models.CharField(max_length=32)  # script_name
    script_content = models.TextField(default='')  # script_content
    drop_status = models.IntegerField(blank=True, null=True, default=0)  # drop_status
    mTime = models.DateTimeField(db_column='m_time', blank=True, null=True, auto_now=True)  # mTime

    class Meta:
        # managed = False
        db_table = 'ops_job_job_script_info'

# 脚本执行历史
class OpsJobScriptHistory(models.Model):
    id = models.AutoField(primary_key=True)
    job_name = models.CharField(max_length=32)  # job name
    result = models.TextField(default='')  # result
    dtEventTime = models.DateTimeField(db_column='dtEventTime', blank=True, null=True, auto_now=True)  # dtEventTime
    exec_status = models.IntegerField(blank=True, null=True, default=0)  #0 exec success, 1 execing
    ip_list = models.TextField(default='')  #ip_list

    class Meta:
        # managed = False
        db_table = 'ops_job_script_history'