#!/usr/bin/python
##
## pentax version using pslr-shoot instead of gphoto2.
## Get pslr-shoot from https://sourceforge.net/projects/pkremote/
## Just do "make cli" and "make install" after download as root on pi
##
import RPi.GPIO as GPIO, datetime, time, os, subprocess, atexit, threading, exifread

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
GPIO.output(BUTTON_LED, False)
GPIO.output(PRINT_LED, True)

# Long press button setup
HOLDTIME = 2                        # Duration for button hold (shutdown)
TAPTIME = 0.01                      # Debounce time for button taps

# init file path
directory = '/home/pi/photobooth_images'
if os.path.exists('/mnt/hdd/photobooth_images'):
  directory = '/mnt/hdd/photobooth_images'
  print("found hdd folder: "+ directory)

@atexit.register
def cleanup():
  GPIO.output(BUTTON_LED, False)
  GPIO.output(POSE_LED, False)
  GPIO.cleanup()

def blinkPoseLed():
  print("blink startet")
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

def blinkGreenLed(times=10):
  GPIO.output(BUTTON_LED, True)
  for i in range(times):
    GPIO.output(BUTTON_LED, False)
    time.sleep(0.1)
    GPIO.output(BUTTON_LED, True)
    time.sleep(0.1)
  GPIO.output(BUTTON_LED, False)

def snapPhoto():
    print("snap started")
    ## pslr-shoot does not support filename with date/time substitution, so concat manually
    time.sleep(4)
    d=datetime.datetime.now()
    gpout = subprocess.check_output("sudo pslr-shoot -m P -i 400 -r 10 -q 3 -o "+ directory +"/photobooth"+ d.strftime('%H%M%S') +".jpg", stderr=subprocess.STDOUT, shell=True)

def tap():
  snapCnt = 0
  while snapCnt < 4:
    print("pose! ("+ str(snapCnt) +")")
    GPIO.output(BUTTON_LED, False)
    
    blink = threading.Thread(target=blinkPoseLed)
    snap = threading.Thread(target=snapPhoto)
    blink.start()
    snap.start()

    blink.join()
    snap.join()
    print("threads ready")
    snapCnt += 1
    time.sleep(0.5)
  GPIO.output(POSE_LED, False)
  GPIO.output(BUTTON_LED, False)
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

## wait for camera to be connected
statout = "" 
print(statout)
while "connected" not in statout:
  statout = subprocess.check_output("sudo pslr-shoot -s", stderr=subprocess.STDOUT, shell=True)
  print(statout)
  time.sleep(2);
  
## Camera is now connected, now take one picture
print("camera is now connected ...")
GPIO.output(PRINT_LED, False)
blinkGreenLed(3)
gpout = subprocess.check_output("sudo pslr-shoot -m P -i 400 -r 10 -q 3 -o /home/pi/dateset.jpg", stderr=subprocess.STDOUT, shell=True)
f = open('/home/pi/dateset.jpg', 'rb')
tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal', details=False)
picDateStr = str(tags['EXIF DateTimeOriginal'])
picDateStr = picDateStr.replace(":", "-", 2)

sysDate = datetime.datetime.now()
picDate = datetime.datetime.strptime(picDateStr, '%Y-%m-%d %H:%M:%S')
print('Date from EXIF..: '+ picDateStr)
print('Sysdate is......: '+ sysDate.strftime('%Y-%m-%d %H:%M:%S'))
## we assume that sysdate is bigger than picdate
delta = sysDate - picDate
print('time delta is...: '+ str(delta))
if delta.seconds > 14400:
  print('difference too big, setting system clock ...')
  ## setting sysclock
  try:
    setDateOut = subprocess.check_output("sudo date \"+%Y-%m-%d %T\" -s \""+ picDateStr +"\"", stderr=subprocess.STDOUT, shell=True)
    print('successfull: '+ setDateOut)
  except CalledProcessError as e:
    print('setting sysdate was not successfull:\n'+ e.output)


GPIO.output(BUTTON_LED, True)

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
