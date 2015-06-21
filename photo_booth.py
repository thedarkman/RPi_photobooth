#!/usr/bin/python
##
## pentax version using pslr-shoot instead of gphoto2.
## Get pslr-shoot from https://sourceforge.net/projects/pkremote/
## Just do "make cli" and "make install" after download as root on pi
##
import RPi.GPIO as GPIO, datetime, time, os, subprocess, atexit

# GPIO setup
GPIO.setmode(GPIO.BCM)
SWITCH = 24
GPIO.setup(SWITCH, GPIO.IN)
RESET = 25
GPIO.setup(RESET, GPIO.IN)
PRINT_LED = 22
POSE_LED = 18
BUTTON_LED = 23
GPIO.setup(POSE_LED, GPIO.OUT)
GPIO.setup(BUTTON_LED, GPIO.OUT)
GPIO.setup(PRINT_LED, GPIO.OUT)
GPIO.output(BUTTON_LED, True)
GPIO.output(PRINT_LED, False)

# Long press button setup
HOLDTIME = 2                        # Duration for button hold (shutdown)
TAPTIME = 0.01                      # Debounce time for button taps

@atexit.register
def cleanup():
  GPIO.output(BUTTON_LED, False)
  GPIO.output(POSE_LED, False)
  GPIO.cleanup()

def blinkPoseLed():
  GPIO.output(POSE_LED, True)
  time.sleep(1.5)
  for i in range(5):
    GPIO.output(POSE_LED, False)
    time.sleep(0.4)
    GPIO.output(POSE_LED, True)
    time.sleep(0.4)
  for i in range(5):
    GPIO.output(POSE_LED, False)
    time.sleep(0.1)
    GPIO.output(POSE_LED, True)
    time.sleep(0.1)
  GPIO.output(POSE_LED, False)

def blinkGreenLed():
  GPIO.output(BUTTON_LED, True)
  for i in range(10):
    GPIO.output(BUTTON_LED, False)
    time.sleep(0.1)
    GPIO.output(BUTTON_LED, True)
    time.sleep(0.1)
  GPIO.output(BUTTON_LED, False)

def tap():
  snap = 0
  while snap < 4:
    print("pose!")
    GPIO.output(BUTTON_LED, False)
    blinkPoseLed()
    print("SNAP")
    ## pslr-shoot does not support filename with date/time substitution, so concat manually
    d=datetime.datetime.now()
    gpout = subprocess.check_output("sudo pslr-shoot -m P -i 400 -r 10 -q 3 -o /home/pi/photobooth_images/photobooth"+ d.strftime('%H%M%S') +".jpg", stderr=subprocess.STDOUT, shell=True)
    print(gpout)
    if "ERROR" not in gpout:
      snap += 1
    GPIO.output(POSE_LED, False)
    time.sleep(0.5)
  print("please wait while your photos print...")
  GPIO.output(PRINT_LED, True)
  # build image and send to printer
  subprocess.call("sudo /home/pi/scripts/photobooth/assemble_and_print", shell=True)
  # Wait to ensure that print queue doesn't pile up
  idle = False
  while idle == False:
     time.sleep(5)
     statout = subprocess.check_output("lpstat -p", stderr=subprocess.STDOUT, shell=True)
     if "idle" in statout:
        idle = True
        print("printer is ready")
  print("ready for next round")
  GPIO.output(PRINT_LED, False)
  GPIO.output(BUTTON_LED, True)

def hold():
  blinkGreenLed()
  print("long pressed button! Shutting down system")
  subprocess.call("sudo shutdown -hP now", shell=True)

## initial states for detect long or normal pressed button
prevButtonState = GPIO.input(SWITCH)
prevTime        = time.time()
tapEnable       = False
holdEnable      = False

while True:

  buttonState = GPIO.input(SWITCH)
  t           = time.time()

  # Has button state changed?
  if buttonState != prevButtonState:
    prevButtonState = buttonState   # Yes, save new state/time
    prevTime        = t
  else:                             # Button state unchanged
    if (t - prevTime) >= HOLDTIME:  # Button held more than 'HOLDTIME'?
      # Yes it has.  Is the hold action as-yet untriggered?
      if holdEnable == True:        # Yep!
        hold()                      # Perform hold action (usu. shutdown)
        holdEnable = False          # 1 shot...don't repeat hold action
        tapEnable  = False          # Don't do tap action on release
    elif (t - prevTime) >= TAPTIME: # Not HOLDTIME.  TAPTIME elapsed?
      # Yes.  Debounced press or release...
      if buttonState == False:      # Button released?
        if tapEnable == True:       # Ignore if prior hold()
          tap()                     # Tap triggered (button released)
          tapEnable  = False        # Disable tap and hold
          holdEnable = False
      else:                         # Button pressed
        tapEnable  = True           # Enable tap and hold actions
        holdEnable = True
