#!/bin/bash

# clear last build
[[ `docker ps -a | grep -w ops_django | wc -l` -ne 0 ]] && docker rm -f ops_django

# if clean last build, open it
[[ `docker images | grep -w ops_django | wc -l` -ne 0 ]] && docker rmi ops_django

[ -d sshkeys ] || mkdir sshkeys

cp -rf ~/.ssh/* ./sshkeys/

docker build . -t ops_django

docker run -d --network ops_web --name ops_django -p 8081:8000 ops_django

