# HarmonyNow 모델 서버

음악 생성 모델 서버로, MIDI 파일을 입력받아 새로운 음악을 생성하고, 결과를 ZIP 파일로 반환하는 FastAPI 기반 애플리케이션입니다.

MIDI 파일의 채워넣기(infill), 코드 진행 및 멜로디 생성 등의 음악적 작업을 수행합니다.

# Requirements
실행을 위해 Docker가 필요합니다.

# How to install and run
이 리포지토리를 clone하세요.
```
git clone https://github.com/soonduck-dreams/harmonynow-model.git
```

프로젝트 디렉토리로 이동하여, `launch.sh`을 실행하면 Docker Image가 빌드되고 Container가 실행됩니다.
```
./launch.sh
```

# Development Environment
- OS: CentOS 7.8 (Naver Cloud Platform)
- IDE: VSCode
- Framework & Libraries
  - FastAPI – 웹 애플리케이션 프레임워크
  - anticipation – 음악 생성 모델(Anticipatory Music Transformer)을 활용한 음악 생성 및 MIDI 변환 작업을 지원하는 도구 (MIDI 파일의 편집, tokenization, 악기 추출, 음악 생성)
  - transformers.AutoModelForCausalLM: Hugging Face로부터 사전 학습된 모델 불러오기
  - midi2audio: MIDI 파일을 오디오 파일(.wav)로 변환
  - pydub: 오디오 파일 처리 (음량 키우기)
