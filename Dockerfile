# use base python image with python 2.7
FROM python:2.7

# set timezone
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone

# install mysql-client
RUN echo "deb http://ftp.cn.debian.org/debian/ stretch main" > /etc/apt/sources.list
RUN echo "deb http://ftp.cn.debian.org/debian/ stretch-updates main" >> /etc/apt/sources.list
RUN echo "deb http://ftp.cn.debian.org/debian-security stretch/updates main" >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y mysql-client
RUN apt-get install -y openssh-server

RUN sed -i 's/^#.*StrictHostKeyChecking ask/StrictHostKeyChecking no/g' /etc/ssh/ssh_config

RUN service ssh restart

# env
ENV RUN_MODE=DEPLOY
ENV C_FORCE_ROOT=true

COPY ./requirements.txt /app/

WORKDIR /app/
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# add project to the image
ADD . /app/

ADD ./sshkeys/ /root/.ssh/

WORKDIR /app/
# RUN server after docker is up
ENTRYPOINT sh start.sh