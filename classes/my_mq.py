# _*_coding:utf-8_*_
import pika
from config import config


def mq_client():
    _config = config("../conf/mq.ini")
    user = _config.getOption("rabbit_mq", "user")
    passwd = _config.getOption("rabbit_mq", "passwd")
    ip = _config.getOption("rabbit_mq", "ip")
    port = _config.getOption("rabbit_mq", "port")
    credentials = pika.PlainCredentials(user, passwd)
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        ip,port,'/',credentials))
    channel = connection.channel()

    channel.queue_declare(queue='balance')
    return channel


