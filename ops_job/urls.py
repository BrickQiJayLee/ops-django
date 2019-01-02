# coding=utf-8

from django.conf.urls import url
from ops_job.views import script_edit
from ops_job.views import script_executor, script_cron, script_history

urlpatterns = [
    # 脚本编辑
    url(r'^/script$', script_executor.exec_scripts, name="ops-job-script"),
    url(r'^/script/exector_create$', script_executor.exector_create, name="ops-job-exector-create$"),
    url(r'^/script/list$', script_edit.get_scripts_list, name="ops-job-script-list"),
    url(r'^/script/edit', script_edit.edit_script, name="ops-job-script-edit"),
    url(r'^/script/delete$', script_edit.delete_script, name="ops-job-script-delete"),
    url(r'^/script/updatescript', script_edit.updatescript, name="ops-job-script-updatescript"),

    # 作业执行历史
    url(r'^/script/script_history$', script_history.get_script_history, name="ops-job-script-scripthistory"),
    url(r'^/script/script_history_detail', script_history.script_history_detail, name="ops-job-script-scripthistorydetail"),

    # 定时作业
    url(r'^/script/cronlist', script_cron.get_cron_list, name="ops-job-script-cronlist"),
    # 服务监控
    url(r'^/script/get_task_list', script_cron.get_task_list, name="ops-job-script-task-list"),
    url(r'^/script/delete_cron_job', script_cron.delete_cron_job, name="ops-job-delete-cron-job"),
    url(r'^/script/commitcron', script_cron.commitcron, name="ops-job-script-commitcron"),
    url(r'^/script/enablecron', script_cron.enablecron, name="ops-job-script-enablecron"),
    url(r'^/script/script_http$', script_executor.scrpits_http, name="ops-job-script-http"),

    # 获取脚本参数
    url(r'^/script/get_args', script_executor.get_args, name="ops-job-script-get-args"),
]