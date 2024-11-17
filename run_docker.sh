#!/bin/bash

# Docker 이미지 이름 설정
IMAGE_NAME="my-fastapi-app"
CONTAINER_NAME="fastapi_container"

# 이미지 빌드
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# 빌드 성공 여부 확인
if [ $? -ne 0 ]; then
  echo "Docker image build failed. Exiting."
  exit 1
fi

# 기존 컨테이너 중지 및 제거 (있다면)
if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# 새 컨테이너 실행
echo "Running Docker container..."
docker run --gpus all -p 8000:8000 \
    -v "$(pwd)/output:/app/output" \
    -v "$(pwd)/uploads:/app/uploads" \
    -v "$(pwd)/hf_cache:/root/.cache/huggingface" \
    --name $CONTAINER_NAME \
    $IMAGE_NAME

echo "Docker container is running."
