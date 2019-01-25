# 部署
 1.安装依赖包:  
 requirement.txt

##### 需要安装mysql，rabbitmq    
  

2.数据库, mq相关:  
----
>#### 初始化数据库：  
>>1). 执行 create database databasename  
>>2). conf目录下写配置

>#### 初始化rabbitmq:  
>>1). rabbitmqctl add_user myuser mypassword #创建用户  
>>2). rabbitmqctl set_user_tags myuser administrator #为用户设置管理员标签
>>3). rabbitmqctl add_vhost vhost #设置虚拟环境  
>>4). rabbitmqctl set_permissions -p vhost myuser ".*" ".*" ".*" #为用户在虚拟环境下设置所有权限    
>>2). conf目录下配置服务

>#### sql导入数据  
>#### python manage.py runserver  

3.celery任务调度配置: 
---- 
>1). 初始化celery: python manage.py migrate djcelery   
>2). 启动celery调度: python manage.py celery beat  
>3). 启动celery任务worker: python manage.py celery worker --loglevel=info

#### 注: 整套服务需要跑至少3个进程 django server进程, 任务调度进程, 任务调度worker进程(可多开)