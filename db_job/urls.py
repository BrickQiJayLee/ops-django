# coding=utf-8

from django.conf.urls import url

from db_job.views import db_instance, db_backup #db_registry, db_backup,
#from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    # DB实例注册
    url(r'^/db_instance/db_registry', db_instance.db_registry,
        name="db-job-db-instance-registry"),
    url(r'^/db_instance/commit_db_instance', db_instance.commit_db_instance,
        name="db-job-db-instance-commit-db-instance"),
    url(r'^/db_instance/delete_instance', db_instance.delete_instance,
        name="db-job-db-instance-delete-instance"),

    # DB备份
    url(r'^/db_backup/backup_list', db_backup.show_db_backup_history, name="db-job-db-backup-backup-list"),
    url(r'^/db_backup/backup_excute_page', db_backup.backup_excute_page, name="db-job-db-backup-backup-excute-page"),
    url(r'^/db_backup/db_backup_start', db_backup.db_backup_start, name="db-backup-start"),

]