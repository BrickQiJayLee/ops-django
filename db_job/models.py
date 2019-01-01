# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.

class DbJobDbInstance(models.Model):
    db_master = models.CharField(db_column='db_master', max_length=32)  # Field name made lowercase.
    db_slave = models.CharField(db_column='db_slave', max_length=32)  # Field name made lowercase.
    db_product = models.CharField(db_column='db_product', max_length=32)  # Field name made lowercase.
    db_product_id = models.CharField(db_column='db_product_id', max_length=32)  # Field name made lowercase.
    db_env = models.CharField(db_column='db_env', max_length=100)  # Field name made lowercase.
    db_mark = models.CharField(db_column='db_mark', max_length=100)  # Field name made lowercase.
    db_passwd = models.CharField(db_column='db_passwd', max_length=32)  # Field name made lowercase.
    db_container_name = models.CharField(db_column='db_container_name', max_length=100)  # Field name made lowercase.
    db_container_name_slave = models.CharField(db_column='db_container_name_slave', default='', max_length=100)  # Field name made lowercase.
    db_user_name = models.CharField(db_column='db_user_name', max_length=32)  # Field name made lowercase.
    db_service_type = models.CharField(db_column='db_service_type', default='container', max_length=32)  # service type  container/service
    db_service_name = models.CharField(db_column='db_service_name', default='', max_length=32)  # Field name made lowercase.
    db_service_name_slave = models.CharField(db_column='db_service_name_slave', default='', max_length=100)  # Field name made lowercase.

    class Meta:
        #managed = False
        db_table = 'db_job_db_instance'

class DbJobDbBackupHistory(models.Model):
    db_instance_id = models.CharField(db_column='db_instance_id', max_length=32)  # Field name made lowercase.
    dbs = models.TextField(db_column='dbs', blank=True, null=True)  # Field name made lowercase.
    tables = models.TextField(db_column='tables', blank=True, null=True)  # Field name made lowercase.
    result = models.TextField(db_column='result', blank=True, null=True)  # Field name made lowercase.
    dtEventTime = models.DateTimeField(db_column='dtEventTime', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        #managed = False
        db_table = 'db_job_db_backup_history'