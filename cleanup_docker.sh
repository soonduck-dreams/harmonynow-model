#!/bin/bash

# 모든 중지된 컨테이너 삭제
echo "Stopping and removing all containers..."
docker stop $(docker ps -aq) > /dev/null 2>&1
docker rm $(docker ps -aq) > /dev/null 2>&1

# 태그 없는 (dangling) 이미지 삭제
echo "Removing dangling images..."
docker image prune -f

# 사용할 수 없는 모든 볼륨 삭제
echo "Removing unused volumes..."
docker volume prune -f

# 사용되지 않는 모든 네트워크 삭제
echo "Removing unused networks..."
docker network prune -f

# 모든 불필요한 이미지 삭제
echo "Removing all unused images..."
docker image prune -a -f

echo "Docker cleanup completed!"