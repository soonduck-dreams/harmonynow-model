# 1. Python 3.10 이미지 사용 (Ubuntu/Debian 기반)
FROM python:3.10-slim-bullseye

# 2. 필요한 OS 패키지 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fluidsynth \
        git \
        curl \
        build-essential \
        pkg-config \
        ffmpeg \
        libssl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/archives/*


# 3. 작업 디렉터리 설정
WORKDIR /app

# 4. 모델 코드 클론 및 설치
RUN git clone https://github.com/jthickstun/anticipation.git

# 5. 의존성 설치
RUN pip install --upgrade pip
RUN pip install ./anticipation
RUN pip install -r anticipation/requirements.txt
RUN pip install "numpy<2"
RUN pip install python-multipart
RUN pip install safetensors
RUN pip install pydub

# 6. FastAPI와 Uvicorn 설치
RUN pip install fastapi uvicorn

# 7. model.py 및 필요한 디렉토리 복사
COPY model_server.py /app/
RUN mkdir /app/uploads /app/output

# 8. FastAPI 서버 실행
CMD ["uvicorn", "model_server:app", "--host", "0.0.0.0", "--port", "8000"]
