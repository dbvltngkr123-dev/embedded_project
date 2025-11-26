import RPi.GPIO as GPIO
import time

# ==================== 전역 변수 및 핀 설정 ====================
# BCM 핀 번호 사용
RED_PIN = 18    # 적색 LED (잠금)
GREEN_PIN = 27  # 녹색 LED (열림)
MOTOR_PWM_PIN = 25  # 모터 속도 제어
MOTOR_ENABLE_PIN = 24  # 모터 활성화
BUZZER_PIN = 23    # 부저

FREQUENCY = 100
MOTOR_SPEED = 80
LOCK_DURATION = 5     # 문이 열린 후 자동 잠김 시간
SECRET_CODE = "1234"  # 비밀번호 설정 (4자리)

# 1차원 배열 키패드 버튼 핀
KEYPAD_PB = [6, 12, 13, 16, 19, 20, 26, 21]

# 부저 주파수 정의
NOTES = {
    'E5': 659, 'Ds5': 622, 'B4': 466, 'D5': 587,
    'C5': 523, 'A4': 440, 'R': 0
}

FUR_ELISE_NOTES = [
    ('E5', 1), ('Ds5', 1), ('E5', 1), ('Ds5', 1),
    ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
    ('A4', 4)
]

NOTE_DURATION = 0.2
FIRE_SIREN_HIGH = 900
FIRE_SIREN_LOW = 650
FIRE_SIREN_TIME = 0.15  # 경고음 시간

# ==================== GPIO 초기화 ====================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# 키패드 입력 핀 초기화 (PUD_DOWN)
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
buzzer_pwm = GPIO.PWM(BUZZER_PIN, 1)
buzzer_pwm.start(0)

# ==================== 부저 연주 함수 ====================
def play_fur_elise_success_tone():
    buzzer_pwm.ChangeDutyCycle(50)
    for note, duration_mult in FUR_ELISE_NOTES[:5]:
        freq = NOTES[note]
        duration = NOTE_DURATION * duration_mult
        if freq == 0:
            buzzer_pwm.ChangeDutyCycle(0)
        else:
            buzzer_pwm.ChangeFrequency(freq)
            buzzer_pwm.ChangeDutyCycle(50)
        time.sleep(duration)
    buzzer_pwm.ChangeDutyCycle(0)

def play_fail_siren():
    buzzer_pwm.ChangeDutyCycle(50)
    for _ in range(3):
        buzzer_pwm.ChangeFrequency(FIRE_SIREN_HIGH)
        time.sleep(FIRE_SIREN_TIME)
        buzzer_pwm.ChangeFrequency(FIRE_SIREN_LOW)
        time.sleep(FIRE_SIREN_TIME)
    buzzer_pwm.ChangeDutyCycle(0)

# ==================== 키패드 읽기 ====================
# 프로그램 시작 시 초기 prev_state 설정
prev_state = [GPIO.input(pin) for pin in KEYPAD_PB]

def check_keypad():
    global prev_state
    key_pressed = None
    
    for idx, pin in enumerate(KEYPAD_PB):
        current_state = GPIO.input(pin)
        
        # LOW -> HIGH 변화 감지
        if current_state == GPIO.HIGH and prev_state[idx] == GPIO.LOW:
            key_pressed = str(idx + 1)
        
        # 상태 갱신
        prev_state[idx] = current_state
    
    return key_pressed  # 눌린 키 없으면 None 반환

# ==================== 도어락 상태 제어 ====================
def lock_door():
    print("--- [LOCKED] 도어락 잠금 ---")
    GPIO.output(RED_PIN, True)
    GPIO.output(GREEN_PIN, False)
    GPIO.output(MOTOR_ENABLE_PIN, False)
    motor_pwm.ChangeDutyCycle(0)

def unlock_door():
    print("--- [UNLOCKED] 비밀번호 일치! 문 열림 ---")
    GPIO.output(RED_PIN, False)
    GPIO.output(GREEN_PIN, True)
    
    # 모터 잠깐 회전
    GPIO.output(MOTOR_ENABLE_PIN, True)
    motor_pwm.ChangeDutyCycle(MOTOR_SPEED)
    time.sleep(0.5)
    GPIO.output(MOTOR_ENABLE_PIN, False)
    
    play_fur_elise_success_tone()
    
    print(f"문이 {LOCK_DURATION}초 후 자동으로 잠깁니다.")
    time.sleep(LOCK_DURATION)
    lock_door()

def password_fail_sequence(current_input):
    print(f"--- [FAILED] 잘못된 비밀번호: {current_input} ---")
    play_fail_siren()
    for _ in range(3):
        GPIO.output(RED_PIN, False)
        time.sleep(0.1)
        GPIO.output(RED_PIN, True)
        time.sleep(0.1)
    lock_door()

# ==================== 메인 루프 ====================
if __name__ == "__main__":
    input_code = ""
    print(f"--- 도어락 시스템 시작 (비밀번호: {SECRET_CODE}) ---")
    
    try:
        lock_door()
        
        while True:
            key = check_keypad()
            
            if key:  # 키가 눌렸을 때만 처리
                print(f"Pressed key: {key}")
                
                if key == '7':  # 엔터 역할
                    print(f"입력 완료: {input_code}")
                    if input_code == SECRET_CODE:
                        unlock_door()
                    else:
                        password_fail_sequence(input_code)
                    input_code = ""
                    
                elif key == '8':  # 초기화 역할
                    print("입력 초기화.")
                    input_code = ""
                    
                elif key.isdigit() and len(input_code) < len(SECRET_CODE):
                    input_code += key
                    print(f"입력 중: {input_code}")
            
            time.sleep(0.01)

    except KeyboardInterrupt:
        motor_pwm.stop()
        buzzer_pwm.stop()
        GPIO.output(RED_PIN, False)
        GPIO.output(GREEN_PIN, False)
        GPIO.output(MOTOR_ENABLE_PIN, False)
        GPIO.cleanup()
        print("\n프로그램 안전 종료 완료.")
