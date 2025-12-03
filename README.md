pi@raspberrypi:~ $ cd embedded_project

pi@raspberrypi:~ $ python3 Doorlockrg.py

1234 먼저 비밀번호 맞추는것을 입력

error 그다음 5회틀려서 비밀번호 경고음

1515 그다음 비밀번호를 바꾸는걸 보여줌

  잘되었나 확인해서 비밀번호 맞는걸 보여줌
  
1212 원래 비밀번호를 입력해서 비밀번호가 확실히 바뀐걸 보여줌

그다음 1125를 입력해 무음 패닉 모드(비상 상황 알림)  

그다음 1141을 입력해서 도둑이 들었다는것을 신호를 보냄

마지막 1161을 입력해 구급차를 호출하는듯한 연출을 보여줌 




장치,용도,BCM 핀 번호

RED LED,모터 작동 상태 표시,18

GREEN LED,모터 정지 상태 표시,27

Motor Enable,모터 드라이버 ON/OFF 제어,24

Buzzer (PWM),멜로디 연주,17

keypad  리본케이블 J8 -> BT1  
                   J7 -> BT2


Doorlockrg.py가 레알 찐최종본
                   
