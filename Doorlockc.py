import RPi.GPIO as GPIO
import time
import threading # 부저와 LED/모터 동작을 동시에 처리하기 위해 threading 모듈 사용

# 부저 동시 접근 제어를 위한 Lock 객체 (Thread-Safety 확보)
BUZZER_LOCK = threading.Lock() 

# ==================== 전역 변수 및 핀 설정 ====================
# BCM 핀 번호 사용
# !!! 사용자의 하드웨어 연결 상태에 맞춰 RED_PIN과 GREEN_PIN의 BCM 핀 번호를 교체했습니다.
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
DISCO_CODE = "1261" # [UPDATED] 디스코 파티 모드 (고속 교차 깜빡임, 신나는 소리)
STEALTH_CODE = "1251" # [UPDATED] 스텔스 잠입 모드 (희미한 펄스, 저음 소리, 느린 모터)

SPECIAL_MODE_DURATION = 10 # 특수 모드 작동 시간 (10초)
PARTY_MODE_DURATION = 15 # 디스코 모드 작동 시간 (15초)
STEALTH_PWM = 20 # 스텔스 모드 모터 속도 (느리고 조용하게)
STEALTH_TONE_FREQ = 200 # 스텔스 모드 저음 주파수

# 1차원 배열 키패드 버튼 핀
KEYPAD_PB = [6, 12, 13, 16, 19, 20, 26, 21]

# 부저 주파수 및 톤 정의
NOTES = {
    'E5': 659, 'Ds5': 622, 'B4': 466, 'D5': 587,
    'C5': 523, 'A4': 440, 'R': 0, 'G4': 392, 'E4': 330
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

DISCO_MELODY = [ # [NEW] 디스코 멜로디 (빠르고 경쾌한 루프)
    ('C5', 0.5), ('G4', 0.5), ('E5', 0.5), ('C5', 0.5),
    ('D5', 0.5), ('G4', 0.5), ('A4', 0.5), ('E4', 0.5),
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
    """[NEW] 디스코 모드 톤 (15초 동안 빠르게 반복)"""
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
    """[NEW] 스텔스 모드 톤 (저주파수 펄스, 조용함)"""
    with BUZZER_LOCK:
        # 단일, 매우 짧고 낮은 톤만 재생
        try:
            buzzer_pwm.ChangeDutyCycle(30) # 듀티 사이클을 낮춰 더 조용하게
            buzzer_pwm.ChangeFrequency(STEALTH_TONE_FREQ)
            time.sleep(NOTE_DURATION * 0.5) 
        except Exception as e:
            print(f"스텔스 톤 재생 중 오류 발생: {e}") 
        finally:
            buzzer_pwm.ChangeDutyCycle(0)

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
    GPIO.output(RED_PIN, True)      # 잠금 상태: 빨간 LED 켜짐
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
    """비밀번호 실패 시 경고 시퀀스"""
    print(f"--- [FAILED] 잘못된 비밀번호: {current_input} ---")
    play_fail_siren()
    for _ in range(3): # 적색 LED 깜빡임
        GPIO.output(RED_PIN, False)
        time.sleep(0.1)
        GPIO.output(RED_PIN, True)
        time.sleep(0.1)
    lock_door()
    
# ==================== 특수 모드 처리 함수 (업그레이드) ====================
def handle_special_mode(mode_name, motor_speed, buzzer_function, mode_duration):
    """
    특수 모드를 처리하는 함수 (LED/모터/부저 동시 작동)
    :param mode_name: 모드 이름 (출력용)
    :param motor_speed: 모터 PWM 듀티 사이클 (0~100)
    :param buzzer_function: 실행할 부저 함수 (함수 객체)
    :param mode_duration: 모드 총 작동 시간 (초)
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

    while time.time() - start_time < mode_duration:
        
        if mode_name in ["Disco Party", "Trap"]:
            # 교차 깜빡임 (Disco: 고속 교차, Trap: 저속 교차)
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

# ==================== 메인 루프 ====================
if __name__ == "__main__":
    input_code = ""
    print(f"--- 도어락 시스템 시작 (일반 비밀번호: {SECRET_CODE}) ---")
    
    try:
        test_buzzer() 

        # 1. 초기 LED 상태 명확화 (빨간불 켜짐)
        lock_door() 
        
        while True:
            key = check_keypad()
            
            if key: # 키가 눌렸을 때만 처리
                
                # 1. 키 입력 피드백 (짧은 소리)
                keypress_thread = threading.Thread(target=play_keypress_tone)
                keypress_thread.start()
                
                print(f"Pressed key: {key}")
                
                if key == '7': # 엔터 역할 (입력 완료)
                    print(f"입력 완료: {input_code}")
                    
                    # 1. 일반 비밀번호 체크
                    if input_code == SECRET_CODE:
                        unlock_door() 
                    # 2. 특수 코드 체크
                    elif input_code == AMBULANCE_CODE:
                        # 구급차 (1161): 녹색 깜빡임, 일반 모터, 사이렌, 10초
                        handle_special_mode("Ambulance", 80, play_ambulance_siren, SPECIAL_MODE_DURATION)
                    elif input_code == FIREFIGHTER_CODE:
                        # 소방차 (1151): 적색 깜빡임, 일반 모터, 사이렌, 10초
                        handle_special_mode("Firefighter", 80, play_firefighter_siren, SPECIAL_MODE_DURATION)
                    elif input_code == DISCO_CODE:
                        # [UPDATED] 디스코 (1261): 빨강/초록 고속 교차, 모터 멈춤(0), 신나는 소리, 15초
                        handle_special_mode("Disco Party", 0, play_disco_tone, PARTY_MODE_DURATION) 
                    elif input_code == STEALTH_CODE:
                        # [UPDATED] 스텔스 (1251): 초록색 희미한 펄스, 모터 매우 느리게(20), 저음 펄스 소리, 10초
                        handle_special_mode("Stealth", STEALTH_PWM, play_stealth_tone, SPECIAL_MODE_DURATION)
                    elif input_code == BURGLAR_CODE:
                        # 도둑: 빨간/초록 동시 깜빡, 모터 느린 속도(30), 다급한 소리, 10초
                        handle_special_mode("Burglar Alert", 30, play_burglar_alarm, SPECIAL_MODE_DURATION)
                    elif input_code == TRAP_CODE:
                        # 함정: 빨간/초록 번갈아 깜빡, 모터 느린 속도(30), 함정 노래, 10초
                        handle_special_mode("Trap", 30, play_trap_tone, SPECIAL_MODE_DURATION)
                    # 3. 실패 처리
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
