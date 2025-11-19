import RPi.GPIO as GPIO
import time
import math

# ==================== 핀 설정 (이전과 동일) ====================
RED_PIN = 18    
GREEN_PIN = 27  
MOTOR_PWM_PIN = 25  
MOTOR_ENABLE_PIN = 24 
BUZZER_PIN = 23       

FREQUENCY = 100 
DELAY_TIME = 10 # ✨ 10초 유지로 수정 ✨
NOTE_DURATION = 0.2 # ✨ 16분음표 길이 (0.2초로 느리게 조정) ✨

# ✨ 엘리제를 위하여 음계 주파수 정의 ✨
NOTES = {
    'E5': 659, 'Ds5': 622, 'B4': 466, 'D5': 587, 
    'C5': 523, 'A4': 440, 'R': 0 # R: 쉼표
}

# ✨ 엘리제를 위하여 도입부 멜로디 배열 (E-D#-E-D#-E-B-D-C-A) ✨
# (음표 길이 비율은 유지)
FUR_ELISE_NOTES = [
    ('E5', 1), ('Ds5', 1), ('E5', 1), ('Ds5', 1), 
    ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1), 
    ('A4', 4) # 4는 4분음표 (16분음표 기준 4배)
]

# ==================== GPIO 초기화 및 PWM 설정 (이전과 동일) ====================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(MOTOR_PWM_PIN, GPIO.OUT)
GPIO.setup(MOTOR_ENABLE_PIN, GPIO.OUT) 
GPIO.setup(BUZZER_PIN, GPIO.OUT)

GPIO.output(RED_PIN, False)
GPIO.output(GREEN_PIN, False)
GPIO.output(MOTOR_ENABLE_PIN, False)

motor_pwm = GPIO.PWM(MOTOR_PWM_PIN, FREQUENCY)
motor_pwm.start(0) 

buzzer_pwm = GPIO.PWM(BUZZER_PIN, NOTES['B4']) 
buzzer_pwm.start(0) 


# ==================== 부저 연주 함수 (총 시간 동안 반복) ====================
def play_fur_elise_for_duration(total_duration):
    """지정된 시간 동안 엘리제를 위하여 멜로디를 반복 연주합니다."""
    
    start_time = time.time()
    
    while time.time() - start_time < total_duration:
        # FUR_ELISE_NOTES 배열 사용
        for note, duration_multiplier in FUR_ELISE_NOTES:
            
            if time.time() - start_time >= total_duration:
                break
                
            freq = NOTES[note]
            duration = NOTE_DURATION * duration_multiplier
            
            # 남은 시간이 부족하면 멜로디 길이 보정
            if time.time() + duration > start_time + total_duration:
                duration = start_time + total_duration - time.time()
                if duration <= 0: break

            if freq == 0:
                buzzer_pwm.ChangeDutyCycle(0)
            else:
                buzzer_pwm.ChangeFrequency(freq)
                buzzer_pwm.ChangeDutyCycle(50) 
                
            time.sleep(duration)
            
    buzzer_pwm.ChangeDutyCycle(0)


# ==================== LED/모터/부저 제어 함수 (시간만 수정) ====================
def set_status(is_running):
    if is_running:
        # 1. 모터 구동 (RED ON, 소리 ON)
        GPIO.output(RED_PIN, True)   
        GPIO.output(GREEN_PIN, False)
        GPIO.output(MOTOR_ENABLE_PIN, True) 
        motor_pwm.ChangeDutyCycle(80) 
        
        print(f"Status: RED (Motor RUNNING, FUR ELISE ON) for {DELAY_TIME}s")
        
        # ✨ 10초 동안 멜로디 반복 연주 ✨
        play_fur_elise_for_duration(DELAY_TIME) 
        
    else:
        # 2. 모터 정지 (GREEN ON, 소리 OFF)
        GPIO.output(RED_PIN, False)
        GPIO.output(GREEN_PIN, True)
        GPIO.output(MOTOR_ENABLE_PIN, False) 
        motor_pwm.ChangeDutyCycle(0) 
        buzzer_pwm.ChangeDutyCycle(0)
        
        print(f"Status: GREEN (Motor STOPPED, BUZZER OFF) for {DELAY_TIME}s")
        time.sleep(DELAY_TIME) 

# ==================== 메인 루프 (이전과 동일) ====================
if __name__ == "__main__":
    try:
        while True:
            set_status(True) 
            set_status(False) 

    except KeyboardInterrupt:
        motor_pwm.stop() 
        buzzer_pwm.stop()
        
        GPIO.output(RED_PIN, False)
        GPIO.output(GREEN_PIN, False)
        GPIO.output(MOTOR_ENABLE_PIN, False)
        GPIO.cleanup()
        print("Program terminated safely.")
