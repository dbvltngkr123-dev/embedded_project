import RPi.GPIO as GPIO

import time

import threading # 부저와 LED/모터 동작을 동시에 처리하기 위해 threading 모듈 사용

# ==================== 전역 변수 및 핀 설정 ====================

# BCM 핀 번호 사용

RED_PIN = 18    # 적색 LED (잠금/경고)

GREEN_PIN = 27  # 녹색 LED (열림/경고)

MOTOR_PWM_PIN = 25  # 모터 속도 제어

MOTOR_ENABLE_PIN = 24  # 모터 활성화

BUZZER_PIN = 17    # 부저 (BCM 23 -> BCM 17로 변경)



FREQUENCY = 100

LOCK_DURATION = 5       # 문이 열린 후 자동 잠김 시간



# 비밀번호 및 특수 코드 정의

SECRET_CODE = "1234"    # 일반 비밀번호

AMBULANCE_CODE = "1161" # 구급차 호출 (녹색 1초 깜빡, 모터 일반, 구급차 소리 10초)

FIREFIGHTER_CODE = "1151" # 소방차 호출 (적색 1초 깜빡, 모터 일반, 소방차 소리 10초)

BURGLAR_CODE = "1141" # 도둑 경고 (적색/녹색 동시 1초 깜빡, 모터 느리게, 다급한 소리 10초)

TRAP_CODE = "1131" # 함정 경고 (적색/녹색 번갈아 1초 깜빡, 모터 느리게, 함정 노래 10초)

SPECIAL_MODE_DURATION = 10 # 특수 모드 작동 시간 (10초)



# 1차원 배열 키패드 버튼 핀

KEYPAD_PB = [6, 12, 13, 16, 19, 20, 26, 21]



# 부저 주파수 및 톤 정의

NOTES = {

    'E5': 659, 'Ds5': 622, 'B4': 466, 'D5': 587,

    'C5': 523, 'A4': 440, 'R': 0

}



FUR_ELISE_NOTES = [

    ('E5', 1), ('Ds5', 1), ('E5', 1), ('Ds5', 1),

    ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),

    ('A4', 4)

]



TRAP_MELODY = [ # 함정 노래 (간단한 반복 멜로디)

    ('C5', 1), ('R', 1), ('Ds5', 1), ('R', 1),

    ('C5', 1), ('Ds5', 1), ('R', 1), ('C5', 1),

    ('R', 1), ('Ds5', 1)

]



NOTE_DURATION = 0.2



# 사이렌 주파수

SIREN_HIGH_AMB = 950 # 구급차 고음

SIREN_LOW_AMB = 650  # 구급차 저음

SIREN_HIGH_FIRE = 800 # 소방차 고음 (구급차와 구분되도록)

SIREN_LOW_FIRE = 450 # 소방차 저음

SIREN_TIME = 0.3 # 사이렌 톤 유지 시간



# 도둑 경고음 주파수

ALARM_HIGH = 1000

ALARM_LOW = 300

ALARM_TIME = 0.1 # 짧고 다급한 간격



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



def play_fur_elise_success_tone():

    """비밀번호 성공 톤 (엘리제를 위하여)"""

    # 부저 안정성을 위해 ChangeDutyCycle을 함수 내에서 명확하게 제어

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

    # 10초 동안 멜로디가 반복되도록 횟수 계산

    melody_time = sum(d for n, d in TRAP_MELODY) * NOTE_DURATION

    cycle_count = int(SPECIAL_MODE_DURATION / melody_time) + 1

    play_tone(TRAP_MELODY, cycle_count=cycle_count)

    

def play_fail_siren():

    """비밀번호 실패 톤"""

    # 실패 사이렌 코드는 기존 코드의 주파수를 사용합니다.

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

    """도어락을 잠금 상태로 설정"""

    print("--- [LOCKED] 도어락 잠금 ---")

    GPIO.output(RED_PIN, True)

    GPIO.output(GREEN_PIN, False)

    GPIO.output(MOTOR_ENABLE_PIN, False)

    motor_pwm.ChangeDutyCycle(0)

    # 부저 소리 확실히 끄기

    buzzer_pwm.ChangeDutyCycle(0) 



def unlock_door():

    """비밀번호 성공 시 문 열림 시퀀스"""

    print("--- [UNLOCKED] 비밀번호 일치! 문 열림 ---")

    GPIO.output(RED_PIN, False)

    GPIO.output(GREEN_PIN, True)

    

    # 모터 잠깐 회전 (문 열림 동작)

    GPIO.output(MOTOR_ENABLE_PIN, True)

    motor_pwm.ChangeDutyCycle(80) # 일반 속도

    time.sleep(0.5)

    GPIO.output(MOTOR_ENABLE_PIN, False)

    

    play_fur_elise_success_tone()

    

    print(f"문이 {LOCK_DURATION}초 후 자동으로 잠깁니다.")

    time.sleep(LOCK_DURATION)

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

    

# ==================== 특수 모드 처리 함수 ====================

def handle_special_mode(mode_name, red_blink_on, green_blink_on, alternate_blink, motor_speed, buzzer_function):

    """

    10초 동안 특수 모드를 처리하는 함수

    :param mode_name: 모드 이름 (출력용)

    :param red_blink_on: 빨간 LED 켜짐/꺼짐

    :param green_blink_on: 초록 LED 켜짐/꺼짐

    :param alternate_blink: 교차 깜빡임 여부 (True/False)

    :param motor_speed: 모터 PWM 듀티 사이클 (0~100)

    :param buzzer_function: 실행할 부저 함수 (함수 객체)

    """

    print(f"--- [{mode_name.upper()} MODE] {mode_name} 호출 (10초간 작동) ---")

    

    # 모터 설정

    GPIO.output(MOTOR_ENABLE_PIN, True)

    motor_pwm.ChangeDutyCycle(motor_speed)

    

    # 부저 함수를 별도 스레드에서 실행하여 LED/모터와 동시에 작동

    buzzer_thread = threading.Thread(target=buzzer_function)

    buzzer_thread.start()

    

    start_time = time.time()

    while time.time() - start_time < SPECIAL_MODE_DURATION:

        

        # LED 깜빡임 로직

        current_state = GPIO.HIGH

        

        if alternate_blink:

            # 교차 깜빡임 (TRAP_CODE: 빨간불과 초록불이 번갈아 깜빡)

            GPIO.output(RED_PIN, current_state)

            GPIO.output(GREEN_PIN, not current_state)

            time.sleep(0.5)

            GPIO.output(RED_PIN, not current_state)

            GPIO.output(GREEN_PIN, current_state)

            time.sleep(0.5)

        else:

            # 동시 또는 단일 색상 깜빡임 (1초 주기로 깜빡)

            GPIO.output(RED_PIN, red_blink_on and current_state)

            GPIO.output(GREEN_PIN, green_blink_on and current_state)

            time.sleep(0.5)

            

            GPIO.output(RED_PIN, False)

            GPIO.output(GREEN_PIN, False)

            time.sleep(0.5)

        

    # 특수 모드 종료

    buzzer_thread.join() # 부저 스레드가 완전히 종료될 때까지 대기

    print(f"--- [{mode_name.upper()} MODE] 10초 작동 완료. 도어락 잠금 상태로 복귀 ---")

    lock_door()



# ==================== 메인 루프 ====================

if __name__ == "__main__":

    input_code = ""

    print(f"--- 도어락 시스템 시작 (일반 비밀번호: {SECRET_CODE}) ---")

    

    try:

        # 부저 핀(BCM 17)이 정상 작동하는지 확인하기 위한 테스트를 먼저 실행합니다.

        test_buzzer() 



        lock_door() # 초기 상태: 잠금

        

        while True:

            key = check_keypad()

            

            if key: # 키가 눌렸을 때만 처리

                print(f"Pressed key: {key}")

                

                if key == '7': # 엔터 역할 (입력 완료)

                    print(f"입력 완료: {input_code}")

                    

                    # 1. 일반 비밀번호 체크

                    if input_code == SECRET_CODE:

                        unlock_door()

                    # 2. 특수 코드 체크

                    elif input_code == AMBULANCE_CODE:

                        # 구급차: 초록불 깜빡, 모터 일반 속도(80), 구급차 소리

                        handle_special_mode("Ambulance", False, True, False, 80, play_ambulance_siren)

                    elif input_code == FIREFIGHTER_CODE:

                        # 소방차: 빨간불 깜빡, 모터 일반 속도(80), 소방차 소리

                        handle_special_mode("Firefighter", True, False, False, 80, play_firefighter_siren)

                    elif input_code == BURGLAR_CODE:

                        # 도둑: 빨간/초록 동시 깜빡, 모터 느린 속도(30), 다급한 소리

                        handle_special_mode("Burglar Alert", True, True, False, 30, play_burglar_alarm)

                    elif input_code == TRAP_CODE:

                        # 함정: 빨간/초록 번갈아 깜빡, 모터 느린 속도(30), 함정 노래

                        handle_special_mode("Trap", True, True, True, 30, play_trap_tone)

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
