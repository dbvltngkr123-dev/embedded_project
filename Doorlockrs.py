import RPi.GPIO as GPIO
import time
import threading # 부저와 LED/모터 동작을 동시에 처리하기 위해 threading 모듈 사용

# 부저 동시 접근 제어를 위한 Lock 객체 (Thread-Safety 확보)
BUZZER_LOCK = threading.Lock() 

# ==================== 전역 변수 및 핀 설정 ====================
# BCM 핀 번호 사용
RED_PIN = 27    # 적색 LED (잠금/경고)
GREEN_PIN = 18  # 녹색 LED (열림/경고)
MOTOR_PWM_PIN = 25  # 모터 속도 제어
MOTOR_ENABLE_PIN = 24  # 모터 활성화
BUZZER_PIN = 17    # 부저

FREQUENCY = 100
LOCK_DURATION = 5       # 문이 열린 후 자동 잠김 시간

# 비밀번호 및 특수 코드 정의
SECRET_CODE = "1234"    # 일반 비밀번호
AMBULANCE_CODE = "1161" # 구급차 호출 (녹색 1초 깜빡)
FIREFIGHTER_CODE = "1151" # 소방차 호출 (적색 1초 깜빡)
BURGLAR_CODE = "1141" # 도둑 경고 (적색/녹색 동시 1초 깜빡)
TRAP_CODE = "1131" # 함정 경고 (적색/녹색 번갈아 1초 깜빡)
DISCO_CODE = "1261" # 디스코 파티 모드 (고속 교차 깜빡임, 신나는 소리)
STEALTH_CODE = "1251" # 스텔스 잠입 모드 (희미한 펄스, 저음 소리, 느린 모터)

# [NEW FEATURE] 무음 패닉 모드 (1125)
PANIC_CODE = "1125" # 무음 패닉 모드 (비상 알림)
# [MODIFIED] 무음 패닉 모드 총 작동 시간 (60초)
SILENT_PANIC_DURATION = 60 
# [NEW] 무음 펄스가 지속되는 시간 (30초)
PANIC_PULSE_SOUND_DURATION = 30 
# [UPDATED FEATURE] 손님용 임시 접근 코드 (2468 -> 2424로 변경됨)
GUEST_CODE = "2424" # 손님용 일회성 코드 
GUEST_CODE_DURATION = 12 * 3600 # 손님 코드가 활성화되는 유효 시간 (12시간 시뮬레이션)
# [UPDATED FEATURE] 비밀번호 재설정 관리자 코드 (1593 -> 1515로 변경됨)
ADMIN_CODE = "1515" # 비밀번호 변경 모드 진입 코드 

SPECIAL_MODE_DURATION = 10 # 특수 모드 작동 시간 (10초)
PARTY_MODE_DURATION = 15 # 디스코 모드 작동 시간 (15초)
STEALTH_PWM = 20 # 스텔스 모드 모터 속도 (느리고 조용하게)
STEALTH_TONE_FREQ = 200 # 스텔스 모드 저음 주파수

# [NEW SECURITY] 5회 실패 시 락다운 설정
FAILURE_LIMIT = 5       # 최대 실패 횟수
LOCKDOWN_DURATION = 60  # 락다운 시간 (초)

# [NEW STATE VARIABLES]
failed_attempts = 0     # 현재 실패 횟수 (전역에서 관리)
lockdown_end_time = 0   # 락다운 종료 시간 (Unix Timestamp)
is_panic_mode = False   # 패닉 모드 상태 플래그

# [NEW STATE VARIABLES for Guest/Admin]
# NOTE: 실제 도어락에서는 이 값들을 파일에 저장해야 재부팅 후에도 유지됩니다.
guest_code_expiry_time = 0 # 손님 코드 만료 시간 (Unix Timestamp)
is_guest_code_used = False # 손님 코드 사용 여부 플래그 (일회성 시뮬레이션용)

change_mode_step = 0    # 0: 일반 모드, 1: 새 비밀번호 입력, 2: 새 비밀번호 확인
new_secret_code_temp = "" # 새 비밀번호 임시 저장
is_admin_mode = False   # 관리자 비밀번호 변경 모드 플래그


# 1차원 배열 키패드 버튼 핀
KEYPAD_PB = [6, 12, 13, 16, 19, 20, 26, 21]

# 부저 주파수 및 톤 정의
NOTES = {
    'E5': 659, 'Ds5': 622, 'E5': 659, 'Ds5': 622,
    'E5': 659, 'B4': 466, 'D5': 587, 'C5': 523,
    'A4': 440, 'R': 0, 'G4': 392, 'E4': 330
}

FUR_ELISE_NOTES = [ # 성공 톤
    ('E5', 1), ('Ds5', 1), ('E5', 1), ('Ds5', 1),
    ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
    ('A4', 4)
]

TRAP_MELODY = [ # 함정 노래 (간단한 반복 멜로디)
    ('C5', 1), ('R', 1), ('Ds5', 1), ('R', 1),
    ('C5', 1), ('Ds5', 1), ('R', 1), ('C5', 1),
    ('R', 1), ('Ds5', 1)
]

DISCO_MELODY = [ # 디스코 멜로디 (빠르고 경쾌한 루프)
    ('C5', 0.5), ('G4', 0.5), ('E5', 0.5), ('C5', 0.5),
    ('D5', 0.5), ('G4', 0.5), ('A4', 0.5), ('E4', 0.5),
]

DINGDONG_TONE = [ # [NEW] 손님 코드 성공 톤 (짧고 경쾌한 딩동)
    ('C5', 0.2), ('G5', 0.3)
]

ADMIN_MODE_TONE = [ # [NEW] 관리자 변경 모드 진입 톤 (느린 띠링-띠링-)
    ('E4', 0.5), ('R', 0.1), ('G4', 0.5), ('R', 0.1) 
]

ADMIN_FAIL_TONE = [ # [NEW] 관리자 모드 실패/불일치 톤
    ('A4', 0.2), ('E4', 0.2), ('A4', 0.2)
]

NOTE_DURATION = 0.2

# 키 입력 피드백 톤 정의
KEYPRESS_TONE = [('C5', 0.1)] 

# 사이렌 주파수
SIREN_HIGH_AMB = 950 
SIREN_LOW_AMB = 650 
SIREN_HIGH_FIRE = 800
SIREN_LOW_FIRE = 450
SIREN_TIME = 0.3 

# 도둑 경고음 주파수
ALARM_HIGH = 1000
ALARM_LOW = 300
ALARM_TIME = 0.1 

# ==================== GPIO 초기화 ====================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# 입력 핀 초기화
for pin in KEYPAD_PB:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# 출력 핀 설정
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(MOTOR_PWM_PIN, GPIO.OUT)
GPIO.setup(MOTOR_ENABLE_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# PWM 설정
motor_pwm = GPIO.PWM(MOTOR_PWM_PIN, FREQUENCY)
motor_pwm.start(0)
# 부저 PWM은 듀티 사이클 0으로 시작 (소리 꺼짐 상태)
buzzer_pwm = GPIO.PWM(BUZZER_PIN, 1)
buzzer_pwm.start(0) 

# ==================== 부저 연주 함수 ====================

def test_buzzer():
    """Buzzer 핀 연결 및 작동 테스트 (Passive Buzzer 기준)"""
    print("--- [BUZZER TEST] 2초간 부저 테스트를 시작합니다. 소리가 나는지 확인하세요. ---")
    
    test_duration = 0.5
    
    with BUZZER_LOCK:
        try:
            # 테스트 톤 1 (1000Hz)
            buzzer_pwm.ChangeDutyCycle(50)
            buzzer_pwm.ChangeFrequency(1000)
            time.sleep(test_duration)
            print("테스트 톤 1 완료")

            # 테스트 톤 2 (500Hz)
            buzzer_pwm.ChangeFrequency(500)
            time.sleep(test_duration)
            print("테스트 톤 2 완료")
            
        except Exception as e:
            print(f"부저 테스트 중 오류 발생: {e}")
        finally:
            # 테스트 종료 후 반드시 부저 끄기
            buzzer_pwm.ChangeDutyCycle(0)
            print("--- [BUZZER TEST] 테스트 완료. ---")
            time.sleep(1) # 잠시 대기

def play_tone(notes_list, cycle_count=1):
    """주어진 음표 리스트를 연주"""
    with BUZZER_LOCK:
        buzzer_pwm.ChangeDutyCycle(50) # 소리 켜기
        
        for _ in range(cycle_count):
            for note, duration_mult in notes_list:
                freq = NOTES.get(note)
                duration = NOTE_DURATION * duration_mult
                
                if freq is None or freq == 0:
                    buzzer_pwm.ChangeDutyCycle(0) # 쉼표는 소리 끄기
                else:
                    buzzer_pwm.ChangeFrequency(freq)
                    buzzer_pwm.ChangeDutyCycle(50) # 소리 켜기
                
                time.sleep(duration)
                
        buzzer_pwm.ChangeDutyCycle(0) # 연주 종료 후 소리 끄기

def play_keypress_tone():
    """키 입력 피드백 톤"""
    # 키 입력 톤은 짧게 재생되어야 하므로, 락 없이 스레드에서 직접 재생
    # 하지만 BUZZER_LOCK이 다른 긴 톤과 충돌하는 것을 막아주므로 유지
    with BUZZER_LOCK:
        try:
            buzzer_pwm.ChangeDutyCycle(50) 
            buzzer_pwm.ChangeFrequency(NOTES['C5'])
            time.sleep(NOTE_DURATION * 0.2) 
        except Exception as e:
            print(f"키 입력 톤 재생 중 오류 발생: {e}") 
        finally:
            buzzer_pwm.ChangeDutyCycle(0)

def play_fur_elise_success_tone():
    """비밀번호 성공 톤 (엘리제를 위하여)"""
    with BUZZER_LOCK:
        buzzer_pwm.ChangeDutyCycle(50) 
        for note, duration_mult in FUR_ELISE_NOTES[:5]:
            freq = NOTES.get(note)
            duration = NOTE_DURATION * duration_mult
            
            if freq is None or freq == 0:
                buzzer_pwm.ChangeDutyCycle(0) 
            else:
                buzzer_pwm.ChangeFrequency(freq)
                buzzer_pwm.ChangeDutyCycle(50) 
                
            time.sleep(duration)
        buzzer_pwm.ChangeDutyCycle(0)

def play_siren(high_freq, low_freq, duration, total_time):
    """사이렌 소리 (구급차 또는 소방차)를 지정된 시간 동안 반복"""
    with BUZZER_LOCK:
        start_time = time.time()
        buzzer_pwm.ChangeDutyCycle(50) # 소리 켜기
        
        while time.time() - start_time < total_time:
            buzzer_pwm.ChangeFrequency(high_freq)
            time.sleep(duration)
            buzzer_pwm.ChangeFrequency(low_freq)
            time.sleep(duration)
        
        buzzer_pwm.ChangeDutyCycle(0) # 종료 후 소리 끄기

def play_ambulance_siren():
    """구급차 사이렌 (10초)"""
    play_siren(SIREN_HIGH_AMB, SIREN_LOW_AMB, SIREN_TIME, SPECIAL_MODE_DURATION)

def play_firefighter_siren():
    """소방차 사이렌 (10초)"""
    play_siren(SIREN_HIGH_FIRE, SIREN_LOW_FIRE, SIREN_TIME, SPECIAL_MODE_DURATION)

def play_burglar_alarm():
    """도둑 경보 (다급한 소리 10초)"""
    with BUZZER_LOCK:
        start_time = time.time()
        buzzer_pwm.ChangeDutyCycle(50) # 소리 켜기
        
        while time.time() - start_time < SPECIAL_MODE_DURATION:
            buzzer_pwm.ChangeFrequency(ALARM_HIGH)
            buzzer_pwm.ChangeDutyCycle(50)
            time.sleep(ALARM_TIME)
            buzzer_pwm.ChangeFrequency(ALARM_LOW)
            time.sleep(ALARM_TIME)
        
        buzzer_pwm.ChangeDutyCycle(0) # 종료 후 소리 끄기

def play_trap_tone():
    """함정 멜로디 (10초 동안 반복)"""
    melody_time = sum(d for n, d in TRAP_MELODY) * NOTE_DURATION
    cycle_count = int(SPECIAL_MODE_DURATION / melody_time) + 1
    play_tone(TRAP_MELODY, cycle_count=cycle_count)
    
def play_disco_tone():
    """디스코 모드 톤 (15초 동안 빠르게 반복)"""
    with BUZZER_LOCK:
        start_time = time.time()
        
        # 멜로디의 1회 재생 시간 계산
        melody_time = sum(d for n, d in DISCO_MELODY) * NOTE_DURATION 
        cycle_count = int(PARTY_MODE_DURATION / melody_time) + 1
        
        for _ in range(cycle_count):
            if time.time() - start_time >= PARTY_MODE_DURATION:
                break
            for note, duration_mult in DISCO_MELODY:
                if time.time() - start_time >= PARTY_MODE_DURATION:
                    break
                    
                freq = NOTES.get(note)
                duration = NOTE_DURATION * duration_mult
                
                if freq is None or freq == 0:
                    buzzer_pwm.ChangeDutyCycle(0)
                else:
                    buzzer_pwm.ChangeFrequency(freq)
                    buzzer_pwm.ChangeDutyCycle(50)
                
                time.sleep(duration)
        
        buzzer_pwm.ChangeDutyCycle(0)

def play_stealth_tone():
    """스텔스 모드 톤 (저주파수 펄스, 조용함)"""
    # 이 톤은 단발성이므로 락을 잡고 짧게 재생
    with BUZZER_LOCK:
        try:
            buzzer_pwm.ChangeDutyCycle(30) # 듀티 사이클을 낮춰 더 조용하게
            buzzer_pwm.ChangeFrequency(STEALTH_TONE_FREQ)
            time.sleep(NOTE_DURATION * 0.5) 
        except Exception as e:
            print(f"스텔스 톤 재생 중 오류 발생: {e}") 
        finally:
            buzzer_pwm.ChangeDutyCycle(0)

def play_super_siren():
    """[NEW] 5회 실패 시 60초간 작동하는 매우 강력한 경고음"""
    SUPER_HIGH = 1500 # 더 높은 주파수
    SUPER_LOW = 300   # 더 낮은 주파수
    SUPER_TIME = 0.03 # 매우 빠르게 전환
    
    with BUZZER_LOCK:
        start_time = time.time()
        # 락다운 지속 시간 동안만 재생
        while time.time() - start_time < LOCKDOWN_DURATION:
            # 1. 고주파 톤
            buzzer_pwm.ChangeFrequency(SUPER_HIGH)
            buzzer_pwm.ChangeDutyCycle(50) 
            time.sleep(SUPER_TIME)
            
            # 2. 저주파 톤
            buzzer_pwm.ChangeFrequency(SUPER_LOW)
            time.sleep(SUPER_TIME)
            
        buzzer_pwm.ChangeDutyCycle(0) # 종료 후 소리 끄기

def play_fail_siren():
    """비밀번호 실패 톤"""
    with BUZZER_LOCK:
        buzzer_pwm.ChangeDutyCycle(50) 
        for _ in range(3):
            buzzer_pwm.ChangeFrequency(900)
            buzzer_pwm.ChangeDutyCycle(50)
            time.sleep(0.15)
            buzzer_pwm.ChangeFrequency(650)
            buzzer_pwm.ChangeDutyCycle(50)
            time.sleep(0.15)
        buzzer_pwm.ChangeDutyCycle(0)

def play_dingdong_tone():
    """[NEW] 손님 코드 성공 톤 (딩동)"""
    play_tone(DINGDONG_TONE)
    
def play_admin_mode_tone():
    """[NEW] 관리자 변경 모드 진입 톤 (느린 띠링-띠링-)"""
    # 2회 반복 연주
    play_tone(ADMIN_MODE_TONE, cycle_count=2)

def play_admin_fail_tone():
    """[NEW] 관리자 모드 실패/불일치 톤"""
    play_tone(ADMIN_FAIL_TONE, cycle_count=1)

def play_silent_panic_pulse(total_duration):
    """
    [MODIFIED] 무음 패닉 펄스: 주변에 들리지 않도록 매우 낮은 주파수와
    매우 낮은 듀티 사이클로 '웅' 소리를 지정된 시간 동안 반복 발생시키는 톤.
    """
    # 펄스 간격 설정
    PULSE_ON_TIME = 0.5 # 0.5초간 켜짐
    PULSE_OFF_TIME = 1.0 # 1.0초간 꺼짐 (펄스 간 간격) - 총 1.5초 주기
    
    with BUZZER_LOCK:
        start_time = time.time()
        
        try:
            # 주파수: 100Hz (매우 낮은 저음)
            buzzer_pwm.ChangeFrequency(100)
            
            # 지정된 시간(30초) 동안 펄스를 반복합니다.
            while time.time() - start_time < total_duration:
                # 켜짐: 5% 듀티 사이클 (매우 조용하게)
                buzzer_pwm.ChangeDutyCycle(5)
                # 남은 시간을 고려하여 sleep (정확한 시간 관리를 위해)
                time.sleep(min(PULSE_ON_TIME, total_duration - (time.time() - start_time)))
                
                # 꺼짐: 펄스 간 간격
                buzzer_pwm.ChangeDutyCycle(0)
                time.sleep(min(PULSE_OFF_TIME, total_duration - (time.time() - start_time)))
                
        except Exception as e:
            print(f"무음 패닉 펄스 재생 중 오류 발생: {e}") 
            
        finally:
            buzzer_pwm.ChangeDutyCycle(0)


# ==================== 키패드 읽기 ====================
prev_state = [GPIO.input(pin) for pin in KEYPAD_PB]

def check_keypad():
    """키패드 눌림 감지 및 상태 갱신 (엣지 감지)"""
    global prev_state
    key_pressed = None
    
    for idx, pin in enumerate(KEYPAD_PB):
        current_state = GPIO.input(pin)
        
        # LOW -> HIGH 변화 (눌림) 감지
        if current_state == GPIO.HIGH and prev_state[idx] == GPIO.LOW:
            key_pressed = str(idx + 1) 
        
        # 상태 갱신
        prev_state[idx] = current_state
    
    return key_pressed 

# ==================== 도어락 상태 제어 ====================
def lock_door():
    """도어락을 잠금 상태로 설정 (초기 상태: 빨간불 켜짐)"""
    print("--- [LOCKED] 도어락 잠금 ---")
    GPIO.output(RED_PIN, True)     # 잠금 상태: 빨간 LED 켜짐
    GPIO.output(GREEN_PIN, False)
    GPIO.output(MOTOR_ENABLE_PIN, False)
    motor_pwm.ChangeDutyCycle(0)
    buzzer_pwm.ChangeDutyCycle(0) 

def unlock_door():
    """비밀번호 성공 시 문 열림 시퀀스 (녹색 LED 깜빡임 및 모터 작동)"""
    print("--- [UNLOCKED] 비밀번호 일치! 문 열림 ---")
    GPIO.output(RED_PIN, False) # 잠금 해제, 빨간불 끔
    
    # 1. 모터 작동 및 녹색 LED 깜빡임 및 성공 톤 재생 (동시에)
    GPIO.output(MOTOR_ENABLE_PIN, True)
    motor_pwm.ChangeDutyCycle(80) # 일반 속도
    
    # 부저 성공 톤을 별도 스레드에서 실행
    buzzer_thread = threading.Thread(target=play_fur_elise_success_tone)
    buzzer_thread.start()
    
    # 깜빡임 및 모터 작동 시간 (2.0초)
    blink_duration = 2.0 
    start_time = time.time()
    
    while time.time() - start_time < blink_duration:
        # 녹색 LED 깜빡임
        GPIO.output(GREEN_PIN, True)
        time.sleep(0.15)
        GPIO.output(GREEN_PIN, False)
        time.sleep(0.15)
        
    GPIO.output(MOTOR_ENABLE_PIN, False) # 모터 정지
    motor_pwm.ChangeDutyCycle(0)
    
    buzzer_thread.join() # 톤 재생이 완전히 끝날 때까지 대기

    # 2. 문 열림 유지 (녹색 LED 켜짐 상태)
    GPIO.output(GREEN_PIN, True)
    
    # 남은 잠금 유지 시간 계산
    remaining_lock_duration = LOCK_DURATION - blink_duration
    if remaining_lock_duration > 0:
        print(f"문이 {remaining_lock_duration}초 후 자동으로 잠깁니다.")
        time.sleep(remaining_lock_duration)
    else:
        print("문이 즉시 잠깁니다.")

    lock_door()

def password_fail_sequence(current_input):
    """비밀번호 실패 시 경고 시퀀스 (5회 미만)"""
    print(f"--- [FAILED] 잘못된 비밀번호: {current_input} ---")
    play_fail_siren()
    for _ in range(3): # 적색 LED 깜빡임
        GPIO.output(RED_PIN, False)
        time.sleep(0.1)
        GPIO.output(RED_PIN, True)
        time.sleep(0.1)
    lock_door()
    
def handle_lockdown_mode():
    """
    [NEW] 비밀번호 5회 실패 시 60초 락다운 모드 처리
    """
    global lockdown_end_time
    
    print("=========================================================")
    print(f"!!! [LOCKDOWN ACTIVATED] 비밀번호 {FAILURE_LIMIT}회 실패! {LOCKDOWN_DURATION}초 락다운 !!!")
    print("=========================================================")
    
    # 락다운 타이머 설정
    lockdown_end_time = time.time() + LOCKDOWN_DURATION
    
    # 모터 정지 및 잠금 상태 유지
    GPIO.output(MOTOR_ENABLE_PIN, False)
    motor_pwm.ChangeDutyCycle(0)
    
    # 부저 경고음을 별도 스레드에서 60초간 실행
    buzzer_thread = threading.Thread(target=play_super_siren)
    buzzer_thread.start()
    
    # LED 경고: 빨간색 초고속 깜빡임
    start_time = time.time()
    
    while time.time() < lockdown_end_time:
        # 락다운 지속 시간 동안 지속적으로 빨간불을 빠르게 깜빡임
        GPIO.output(RED_PIN, True)
        GPIO.output(GREEN_PIN, False)
        time.sleep(0.05)
        
        GPIO.output(RED_PIN, False)
        time.sleep(0.05)
        
    # LED 상태 초기화 (경고음은 스레드에서 자동으로 종료됨)
    GPIO.output(RED_PIN, False)
    GPIO.output(GREEN_PIN, False)

    # 스레드가 종료될 때까지 대기
    if buzzer_thread.is_alive():
        buzzer_thread.join()
        
def handle_guest_access():
    """
    [NEW] 손님 코드 처리: 문 열림 및 코드 일회성/시간 제한 설정 시뮬레이션
    """
    global is_guest_code_used
    
    print("--- [GUEST ACCESS] 손님 코드 일치! 문 열림 ---")
    # NOTE: 실제 환경에서는 is_guest_code_used 대신 guest_code_expiry_time을 사용하고, 
    #       이 상태를 파일에 저장해야 재부팅 후에도 일회성 사용/시간 제한이 유지됩니다.
    is_guest_code_used = True
    
    GPIO.output(RED_PIN, False) # 잠금 해제, 빨간불 끔
    
    # 1. 모터 작동 및 녹색 LED 깜빡임 및 성공 톤 재생 (동시에)
    GPIO.output(MOTOR_ENABLE_PIN, True)
    motor_pwm.ChangeDutyCycle(80) # 일반 속도
    
    # 부저 성공 톤을 별도 스레드에서 실행 (딩동 소리)
    buzzer_thread = threading.Thread(target=play_dingdong_tone)
    buzzer_thread.start()
    
    # 깜빡임 및 모터 작동 시간 (2.0초) - unlock_door와 동일하게 유지
    blink_duration = 2.0 
    start_time = time.time()
    
    while time.time() - start_time < blink_duration:
        # 녹색 LED 깜빡임
        GPIO.output(GREEN_PIN, True)
        time.sleep(0.15)
        GPIO.output(GREEN_PIN, False)
        time.sleep(0.15)
        
    GPIO.output(MOTOR_ENABLE_PIN, False) # 모터 정지
    motor_pwm.ChangeDutyCycle(0)
    
    buzzer_thread.join() # 톤 재생이 완전히 끝날 때까지 대기

    # 2. 문 열림 유지 및 자동 잠김
    GPIO.output(GREEN_PIN, True)
    remaining_lock_duration = LOCK_DURATION - blink_duration
    if remaining_lock_duration > 0:
        print(f"문이 {remaining_lock_duration}초 후 자동으로 잠깁니다.")
        time.sleep(remaining_lock_duration)
    else:
        print("문이 즉시 잠깁니다.")

    lock_door()

def handle_admin_code_change(current_input):
    """
    [NEW] 관리자 비밀번호 변경 모드 처리 (1515)
    """
    global change_mode_step, new_secret_code_temp, SECRET_CODE, is_admin_mode
    
    # 1. 새 비밀번호 입력 단계 (Step 1)
    if change_mode_step == 1:
        if len(current_input) == 4 and current_input.isdigit():
            new_secret_code_temp = current_input
            change_mode_step = 2
            print(f"--- [ADMIN MODE] 새 비밀번호 ({new_secret_code_temp}) 입력 완료. 확인을 위해 다시 한 번 입력하세요. ---")
            # LED 피드백: 녹색 깜빡임으로 다음 단계 준비 알림
            for _ in range(2):
                GPIO.output(GREEN_PIN, True)
                time.sleep(0.2)
                GPIO.output(GREEN_PIN, False)
                time.sleep(0.2)
        else:
            print("--- [ADMIN MODE FAILED] 4자리 숫자를 입력해야 합니다. 모드 취소. ---")
            play_admin_fail_tone()
            change_mode_step = 0
            new_secret_code_temp = ""
            is_admin_mode = False
            lock_door()
            
    # 2. 새 비밀번호 확인 단계 (Step 2)
    elif change_mode_step == 2:
        if current_input == new_secret_code_temp:
            SECRET_CODE = current_input
            print("=========================================================")
            print(f"!!! [ADMIN SUCCESS] 비밀번호가 성공적으로 변경되었습니다. 새 비밀번호: {SECRET_CODE} !!!")
            print("=========================================================")
            
            # 성공 톤 및 LED 피드백: 녹색 켜짐
            play_fur_elise_success_tone()
            GPIO.output(GREEN_PIN, True)
            time.sleep(1.5)
            
            # 상태 초기화
            change_mode_step = 0
            new_secret_code_temp = ""
            is_admin_mode = False
            lock_door()
            
            # NOTE: 실제 환경에서는 이 시점에 변경된 SECRET_CODE를 파일에 저장해야 재부팅 후에도 유지됩니다.
            
        else:
            print("--- [ADMIN MODE FAILED] 비밀번호 불일치! 모드 취소. ---")
            play_admin_fail_tone()
            # LED 피드백: 빨간색 깜빡임
            for _ in range(3):
                GPIO.output(RED_PIN, True)
                time.sleep(0.1)
                GPIO.output(RED_PIN, False)
                time.sleep(0.1)
                
            # 상태 초기화
            change_mode_step = 0
            new_secret_code_temp = ""
            is_admin_mode = False
            lock_door()
    # 3. 그 외의 입력 (오류)
    else:
        print("--- [ADMIN MODE ERROR] 잘못된 관리자 모드 단계. 초기화합니다. ---")
        change_mode_step = 0
        new_secret_code_temp = ""
        is_admin_mode = False
        lock_door()

def handle_special_mode(mode_name, motor_speed, buzzer_function, mode_duration):
    """
    특수 모드를 처리하는 함수 (LED/모터/부저 동시 작동)
    """
    print(f"--- [{mode_name.upper()} MODE] {mode_name} 호출 ({mode_duration}초간 작동) ---")
    
    # 모터 설정
    GPIO.output(MOTOR_ENABLE_PIN, True)
    motor_pwm.ChangeDutyCycle(motor_speed)
    
    # 부저 함수를 별도 스레드에서 실행하여 LED/모터와 동시에 작동
    buzzer_thread = threading.Thread(target=buzzer_function)
    buzzer_thread.start()
    
    start_time = time.time()
    
    # LED 깜빡임 타이밍 및 스타일 설정 (mode_name 기반)
    if mode_name == "Disco Party":
        on_time = 0.05
        off_time = 0.05
    elif mode_name == "Stealth":
        on_time = 0.01 # 매우 짧게 켜서 희미한 펄스 느낌
        off_time = 0.8  # 긴 휴지 시간
    elif mode_name == "Trap":
        on_time = 1.0 # 1초 유지
        off_time = 1.0 # 1초 유지 (번갈아 켜짐)
    else: # Ambulance, Firefighter, Burglar (Normal Warning)
        on_time = 0.5
        off_time = 0.5


    # 나머지 모드 (AMB/FIRE/BURGLAR/STEALTH)에 대한 일반 깜빡임 로직
    while time.time() - start_time < mode_duration:
        
        if mode_name in ["Disco Party", "Trap"]:
            # 교차 깜빡임 
            GPIO.output(RED_PIN, True)
            GPIO.output(GREEN_PIN, False)
            time.sleep(on_time) 
            
            GPIO.output(RED_PIN, False)
            GPIO.output(GREEN_PIN, True)
            time.sleep(off_time) 

        else:
            # 동시 또는 단일 색상 깜빡임 (AMB/FIRE/BURGLAR/STEALTH)
            
            # 켜짐 상태 결정
            red_on = mode_name in ["Firefighter", "Burglar Alert"]
            green_on = mode_name in ["Ambulance", "Burglar Alert", "Stealth"]
            
            GPIO.output(RED_PIN, red_on)
            GPIO.output(GREEN_PIN, green_on)
            time.sleep(on_time)
            
            # 깜빡임을 위해 잠시 끄기
            GPIO.output(RED_PIN, False)
            GPIO.output(GREEN_PIN, False)
            time.sleep(off_time)
            
    # 특수 모드 종료
    if buzzer_thread.is_alive():
        # 부저 스레드가 완전히 종료될 때까지 대기
        buzzer_thread.join() 
        
    print(f"--- [{mode_name.upper()} MODE] {mode_duration}초 작동 완료. 도어락 잠금 상태로 복귀 ---")
    lock_door()

def silent_panic_sequence():
    """
    [MODIFIED] 무음 패닉 모드: 30초 동안 조용한 저주파 펄스를 발생시키며 60초간 비상 신호를 전송합니다.
    """
    global is_panic_mode
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! [SILENT PANIC ACTIVATED] 무음 패닉 모드 활성화 (1125) !!!")
    print(f"!!! {PANIC_PULSE_SOUND_DURATION}초 동안 저주파 펄스가 발생되며, 총 {SILENT_PANIC_DURATION}초 동안 비상 신호가 전송됩니다. !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    is_panic_mode = True
    
    # 1. 모터 정지 및 잠금 상태 유지 (문을 열지 않음)
    GPIO.output(MOTOR_ENABLE_PIN, False)
    motor_pwm.ChangeDutyCycle(0)

    try:
        # 2. 아주 미세한 저주파 펄스 피드백 (30초 동안 반복)을 별도 스레드에서 시작
        pulse_thread = threading.Thread(target=play_silent_panic_pulse, args=(PANIC_PULSE_SOUND_DURATION,))
        pulse_thread.start()
        
        # 3. 비상 신호 전송 시뮬레이션 (총 60초)
        print(f"남은 비상 신호 전송 시간: {SILENT_PANIC_DURATION}초")
        time.sleep(SILENT_PANIC_DURATION)
        
    except Exception as e:
        print(f"패닉 모드 중 오류 발생: {e}")
        
    finally:
        # 펄스 스레드가 아직 실행 중일 경우 종료될 때까지 잠시 대기
        if pulse_thread.is_alive():
             print("펄스 사운드 스레드 종료 대기...")
             # 펄스 주기가 1.5초이므로 2초면 충분히 종료됩니다.
             time.sleep(2) 
        
        print("--- [SILENT PANIC] 무음 패닉 모드 종료 ---")
        is_panic_mode = False
        lock_door() # 혹시 모를 상태를 초기화하고 잠금 상태 유지


# ==================== 메인 루프 ====================
if __name__ == "__main__":
    input_code = ""
    print(f"--- 도어락 시스템 시작 (일반 비밀번호: {SECRET_CODE}, {FAILURE_LIMIT}회 실패 시 {LOCKDOWN_DURATION}초 락다운) ---")
    
    try:
        test_buzzer() 

        # 1. 초기 LED 상태 명확화 (빨간불 켜짐)
        lock_door() 
        
        while True:
            current_time = time.time()
            
            # --- 락다운 상태 확인 및 처리 ---
            if current_time < lockdown_end_time:
                remaining = int(lockdown_end_time - current_time)
                # 락다운 중에는 키 입력 무시하고 시간만 체크
                if remaining <= 0:
                    print("--- [LOCKDOWN ENDED] 락다운 해제. 도어락 잠금 상태로 복귀 ---")
                    lock_door()
                    lockdown_end_time = 0
                    failed_attempts = 0 # 락다운 해제 시 실패 횟수 초기화
                
                time.sleep(0.1) # 락다운 중에는 메인 루프 지연 시간을 늘려 CPU 부담 감소
                continue # 키 입력 처리 건너뛰기
            # --- 락다운 상태 확인 끝 ---
            
            key = check_keypad()
            
            if key: # 키가 눌렸을 때만 처리
                
                # 1. 키 입력 피드백 (짧은 소리)
                keypress_thread = threading.Thread(target=play_keypress_tone)
                keypress_thread.start()
                
                print(f"Pressed key: {key}")
                
                # -------------------------
                # --- 관리자 모드 처리 우선 ---
                # -------------------------
                if is_admin_mode:
                    if key == '7': # 엔터 역할 (입력 완료)
                        print(f"[ADMIN MODE] 입력 완료: {input_code}")
                        if len(input_code) == 4 and input_code.isdigit():
                            handle_admin_code_change(input_code)
                        else:
                            print("[ADMIN MODE] 4자리 숫자만 유효합니다. 다시 입력하세요.")
                            play_admin_fail_tone() 
                        input_code = "" # 입력 완료 후 초기화
                    
                    elif key == '8': # 초기화 역할 (관리자 모드 취소)
                        print("--- [ADMIN MODE CANCELLED] 관리자 모드 취소. ---")
                        play_admin_fail_tone() 
                        change_mode_step = 0
                        new_secret_code_temp = ""
                        is_admin_mode = False
                        input_code = ""
                        lock_door()
                        
                    elif key.isdigit() and len(input_code) < 4: # 숫자 키 입력 (4자리까지 허용)
                        input_code += key
                        print(f"[ADMIN MODE] 입력 중: {input_code}")
                        
                    # 관리자 모드 중에는 아래 일반 로직을 건너뜁니다.
                    continue 

                # -------------------------
                # --- 일반/특수 코드 처리 ---
                # -------------------------

                if key == '7': # 엔터 역할 (입력 완료)
                    print(f"입력 완료: {input_code}")
                    
                    # 1. 일반 비밀번호 체크
                    if input_code == SECRET_CODE:
                        unlock_door() 
                        failed_attempts = 0 # 성공 시 실패 횟수 초기화
                    
                    # 2. [UPDATED] 손님 코드 체크 (2424)
                    elif input_code == GUEST_CODE:
                        # RPi 시뮬레이션에서는 '일회성 플래그'만 사용
                        if is_guest_code_used:
                            print("--- [GUEST ACCESS DENIED] 손님 코드가 이미 사용되었습니다. ---")
                            password_fail_sequence(input_code) # 실패 시퀀스 사용
                        else:
                            handle_guest_access()
                            failed_attempts = 0 # 성공 시 실패 횟수 초기화

                    # 3. [UPDATED] 관리자 변경 코드 체크 (1515)
                    elif input_code == ADMIN_CODE:
                        is_admin_mode = True
                        change_mode_step = 1 # 비밀번호 입력 대기 상태로 변경
                        print("--- [ADMIN MODE] 비밀번호 변경 모드에 진입합니다. 새로운 4자리 비밀번호를 입력하세요. ---")
                        play_admin_mode_tone()
                        
                    # 4. 기존 특수 코드 체크
                    elif input_code == AMBULANCE_CODE:
                        handle_special_mode("Ambulance", 80, play_ambulance_siren, SPECIAL_MODE_DURATION)
                    elif input_code == FIREFIGHTER_CODE:
                        handle_special_mode("Firefighter", 80, play_firefighter_siren, SPECIAL_MODE_DURATION)
                    elif input_code == DISCO_CODE:
                        handle_special_mode("Disco Party", 0, play_disco_tone, PARTY_MODE_DURATION) 
                    elif input_code == STEALTH_CODE:
                        handle_special_mode("Stealth", STEALTH_PWM, play_stealth_tone, SPECIAL_MODE_DURATION)
                    elif input_code == BURGLAR_CODE:
                        handle_special_mode("Burglar Alert", 30, play_burglar_alarm, SPECIAL_MODE_DURATION)
                    elif input_code == TRAP_CODE:
                        handle_special_mode("Trap", 30, play_trap_tone, SPECIAL_MODE_DURATION)
                    elif input_code == PANIC_CODE: # [NEW] 무음 패닉 모드 (1125)
                        # 이전에 활성화된 패닉 모드가 없다면 새로 시작
                        if not is_panic_mode:
                            panic_thread = threading.Thread(target=silent_panic_sequence)
                            panic_thread.start()
                        else:
                            print("--- [SILENT PANIC] 이미 패닉 모드가 활성화되어 있습니다. ---")
                            
                    # 5. 실패 처리 (새로운 락다운 로직 적용)
                    else:
                        failed_attempts += 1
                        print(f"실패 횟수: {failed_attempts} / {FAILURE_LIMIT}")
                        if failed_attempts >= FAILURE_LIMIT:
                            handle_lockdown_mode() # 5회 실패 시 락다운 실행
                        else:
                            password_fail_sequence(input_code)
                            
                    input_code = ""
                    
                elif key == '8': # 초기화 역할
                    print("입력 초기화.")
                    input_code = ""
                    
                elif key.isdigit() and len(input_code) < 4: # 숫자 키 입력 (4자리까지 허용)
                    input_code += key
                    print(f"입력 중: {input_code}")
                
            time.sleep(0.01)

    except KeyboardInterrupt:
        # 프로그램 종료 시 모든 장치를 안전하게 멈추고 GPIO 정리
        motor_pwm.stop()
        buzzer_pwm.stop()
        GPIO.output(RED_PIN, False)
        GPIO.output(GREEN_PIN, False)
        GPIO.output(MOTOR_ENABLE_PIN, False)
        GPIO.cleanup()
        print("\n프로그램 안전 종료 완료.")
