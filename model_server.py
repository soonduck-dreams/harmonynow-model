"""
model_server.py

[1. 역할]
- 음악 생성 모델 서버로, MIDI 파일을 입력받아 새로운 음악을 생성하고, 결과를 ZIP 파일로 반환하는 FastAPI 기반 애플리케이션.
- MIDI 파일의 채워넣기(infill), 코드 진행 및 멜로디 생성 등의 음악적 작업을 수행.

[2. 주요 기능]
- 음악 생성:
  - 주어진 시작(intro)과 끝(outro) MIDI 파일을 입력받아 새로운 MIDI 데이터를 생성.
  - 코드 진행 및 멜로디를 포함한 음악적 요소들을 합성하여 결과물 생성.
- 파일 관리:
  - 업로드된 파일을 컨테이너 내부 디렉토리에 저장 및 읽기.
  - 결과물(MIDI 및 WAV 파일)을 ZIP 파일로 패키징하여 반환.
- API 엔드포인트:
  - `/infill`: 새로운 음악을 생성하고 ZIP 파일로 반환.
  - `/connect-test`: 연결 테스트를 위한 간단한 메시지 반환.

[3. 사용 사례]
- 코드 진행 및 멜로디 데이터를 기반으로 새로운 음악을 생성하여 클라이언트 애플리케이션에 제공.
- 음악 생성 결과를 다운로드 가능한 ZIP 파일 형태로 반환.
"""

import sys
import time
import os
import uuid
import shutil
import zipfile

import midi2audio
import transformers
from transformers import AutoModelForCausalLM
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from anticipation import ops
from anticipation.sample import generate
from anticipation.tokenize import extract_instruments
from anticipation.convert import events_to_midi, midi_to_events
from anticipation.visuals import visualize
from anticipation.config import *
from anticipation.vocab import *

from pydub import AudioSegment

app = FastAPI()

SMALL_MODEL = 'stanford-crfm/music-small-800k'     # faster inference, worse sample quality
MEDIUM_MODEL = 'stanford-crfm/music-medium-800k'   # slower inference, better sample quality
LARGE_MODEL = 'stanford-crfm/music-large-800k'     # slowest inference, best sample quality

FILE_PATH = "/app/"  # 컨테이너 내부 경로로 수정

# load an anticipatory music transformer
print('Loading Model... ', end='')
model = AutoModelForCausalLM.from_pretrained(MEDIUM_MODEL).cuda()
print('Done')

# a MIDI synthesizer
print('Loading MIDI synthesizer... ', end='')
fs = midi2audio.FluidSynth('/usr/share/sounds/sf2/TimGM6mb.sf2')
print('Done')

music_length = 16
before_outro_length = music_length - 4

# the MIDI synthesis script
def synthesize(fs, tokens, output_dir, wav_output_name='output', mid_output_name='midi_output'):
    mid = events_to_midi(tokens)
    midi_output_path = os.path.join(output_dir, f'{mid_output_name}.mid')
    wav_output_path = os.path.join(output_dir, f'{wav_output_name}.wav')
    mid.save(midi_output_path) # 결과 mid 파일 저장
    fs.midi_to_audio(midi_output_path, wav_output_path) # 결과 wav 파일 저장

    # WAV 소리를 키우기
    audio = AudioSegment.from_file(wav_output_path, format="wav")
    louder_audio = audio + 14
    louder_audio.export(wav_output_path, format="wav")  # 기존 파일 덮어쓰기

    # ZIP 파일 생성
    zip_output_path = os.path.join(output_dir, 'generated_music.zip')
    with zipfile.ZipFile(zip_output_path, 'w') as zipf:
        zipf.write(midi_output_path, arcname=os.path.basename(midi_output_path))
        zipf.write(wav_output_path, arcname=os.path.basename(wav_output_path))

def add_control_offset(events):
    events = [CONTROL_OFFSET + tok for tok in events]
    return events

def remove_control_offset(events):
    events = [tok - CONTROL_OFFSET for tok in events]
    return events

def infill_basic(intro_midi_path, outro_midi_path):
    intro = midi_to_events(intro_midi_path)
    outro = midi_to_events(outro_midi_path)
    outro = ops.translate(outro, before_outro_length, seconds=True)

    outro = add_control_offset(outro)
    inpainted = generate(model, 4, before_outro_length, inputs=intro, controls=outro, top_p=1)

    outro = remove_control_offset(outro)
    return inpainted + outro

def infill_chord(intro_midi_path, outro_midi_path, output_dir, save=False):
    print('Infilling Chord... ')
    intro = midi_to_events(intro_midi_path)
    outro = midi_to_events(outro_midi_path)
    intro_comping, intro_melody = extract_instruments(intro, [53])
    outro_comping, outro_melody = extract_instruments(outro, [53])
    intro_melody = remove_control_offset(intro_melody)
    outro_melody = remove_control_offset(outro_melody)
    outro_melody = ops.translate(outro_melody, before_outro_length, seconds=True)

    result_basic = infill_basic(intro_midi_path, outro_midi_path)
    result_comping, result_melody = extract_instruments(result_basic, [53])
    if save:
        synthesize(fs, result_comping, output_dir, 'comping', 'comping_midi')
    return result_comping, intro_melody, outro_melody

def infill_melody(result_comping, intro_melody, outro_melody, output_dir, save=True, intro_clip_sec=1):
    print('Infilling Melody... ')
    comping_with_outro_melody = result_comping + outro_melody
    comping_with_outro_melody = add_control_offset(comping_with_outro_melody)
    intro_melody_and_middle_melody = generate(model, 4, before_outro_length, inputs=intro_melody, controls=comping_with_outro_melody)

    clipped_intro_melody = ops.clip(intro_melody, 0, intro_clip_sec)
    middle_melody = ops.clip(intro_melody_and_middle_melody, 4, 12)

    middle_melody = add_control_offset(middle_melody)

    generated_intro_melody = generate(model, intro_clip_sec, 4, inputs=clipped_intro_melody, controls=middle_melody)

    middle_melody = remove_control_offset(middle_melody)
    comping_with_outro_melody = remove_control_offset(comping_with_outro_melody)

    result = generated_intro_melody + middle_melody + comping_with_outro_melody
    if save:
        synthesize(fs, result, output_dir, 'full', 'full_midi')

@app.post("/infill")
async def infill_new(
    background_tasks: BackgroundTasks,
    intro_file: UploadFile = File(...),
    outro_file: UploadFile = File(...),
):

    # 업로드된 파일 저장
    request_id = str(uuid.uuid4())
    upload_dir = os.path.join(FILE_PATH, 'uploads', request_id)
    output_dir = os.path.join(FILE_PATH, 'output', request_id)
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    intro_midi_path = os.path.join(upload_dir, 'intro.mid')
    outro_midi_path = os.path.join(upload_dir, 'outro.mid')

    with open(intro_midi_path, "wb") as buffer:
        buffer.write(await intro_file.read())
    with open(outro_midi_path, "wb") as buffer:
        buffer.write(await outro_file.read())

    # 연산 수행
    result_comping, intro_melody, outro_melody = infill_chord(intro_midi_path, outro_midi_path, output_dir, save=False)
    infill_melody(result_comping, intro_melody, outro_melody, output_dir, save=True, intro_clip_sec=4)

    result_zip_path = os.path.join(output_dir, 'generated_music.zip')

    response = FileResponse(
        path=result_zip_path,
        media_type="application/zip",
        filename="generated_music.zip"
    )

    # 백그라운드 작업으로 파일 삭제 예약
    background_tasks.add_task(shutil.rmtree, upload_dir)
    background_tasks.add_task(shutil.rmtree, output_dir)

    return response

@app.get("/connect-test")
async def connectTest():
    time.sleep(3)
    return {"message": "I sleeped for a while! Good morning."}
