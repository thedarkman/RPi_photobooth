#!/usr/bin/python
##
## pentax version using pslr-shoot instead of gphoto2.
## Get pslr-shoot from https://sourceforge.net/projects/pkremote/
## Just do "make cli" and "make install" after download as root on pi
##
from picamera import PiCamera
import RPi.GPIO as GPIO, datetime, time, os, subprocess, atexit, threading, exifread
import pygame

# GPIO setup
GPIO.setmode(GPIO.BCM)
SWITCH = 24
GPIO.setup(SWITCH, GPIO.IN)
PRINT_LED = 22
POSE_LED = 18
BUTTON_LED = 23
PHOTO_LIGHT = 25
GPIO.setup(PHOTO_LIGHT, GPIO.OUT)
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

# pygame env stuff to use framebuffer
os.putenv('SDL_FBDEV','/dev/fb0')
os.environ["SDL_FBDEV"] = "/dev/fb0"
os.putenv('SDL_VIDEODRIVER', 'directfb')

# global status vars
printing = 0

@atexit.register
def cleanup():
  GPIO.output(BUTTON_LED, False)
  GPIO.output(POSE_LED, False)
  GPIO.output(PHOTO_LIGHT, False)
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
    file_name =  directory +"/photobooth"+ d.strftime('%H%M%S') +".jpg"
    if usePiCam == True:
      global cam
      cam.start_preview()      
      time.sleep(3)
      cam.capture(file_name)
      cam.stop_preview()
    else:
      gpout = subprocess.check_output("sudo pslr-shoot -m P -i 800 -r 6 -q 3 -o "+ file_name, stderr=subprocess.STDOUT, shell=True)

def tap():
  global printing
  snapCnt = 0
  GPIO.output(PHOTO_LIGHT, True)
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
  GPIO.output(PHOTO_LIGHT, False)
  print("please wait while your photos print...")
  GPIO.output(PRINT_LED, True)
  printing = 1  
  waitP = threading.Thread(target=waitForPrinter)
  animateLeds = threading.Thread(target=blinkAllWhilePrinting)
  waitP.start()
  animateLeds.start()
  waitP.join()
  animateLeds.join()
 
  print("ready for next round")
  GPIO.output(PRINT_LED, False)
  GPIO.output(BUTTON_LED, True)

def waitForPrinter():
  global printing
  # build image and send to printer
  subprocess.call("sudo /home/pi/scripts/photobooth/assemble_and_print", shell=True)
  # Wait to ensure that print queue doesn't pile up
  idle = False
  while idle == False:
     time.sleep(2)
     statout = subprocess.check_output("lpstat -p", stderr=subprocess.STDOUT, shell=True)
     if "idle" in statout or "Leerlauf" in statout:
        idle = True
        print("printer is ready")
  printing = 0

def hold():
  blinkGreenLed()
  print("long pressed button! Shutting down system")
  subprocess.call("sudo shutdown -hP now", shell=True)

def blinkAllWhilePrinting():
  while printing == 1:
    GPIO.output(PRINT_LED, True)
    #GPIO.output(POSE_LED, True)
    time.sleep(1)
    GPIO.output(PRINT_LED, False)
    #GPIO.output(POSE_LED, False)
    time.sleep(1)

## initial states for detect long or normal pressed button
prevButtonState = GPIO.input(SWITCH)
prevTime        = time.time()
tapEnable       = False
holdEnable      = False

usePiCam = False

picam_txt = subprocess.check_output("vcgencmd get_camera", stderr=subprocess.STDOUT, shell=True)
print("picam status: "+ picam_txt)
if "supported=1 detected=1" in picam_txt:
  usePiCam = True

print("Use picam: "+ str(usePiCam))

if usePiCam == False:
  ## wait for camera to be connected
  statout = "" 
  print(statout)
  while "connected" not in statout:
    statout = subprocess.check_output("sudo pslr-shoot -s", stderr=subprocess.STDOUT, shell=True)
    print(statout)
    time.sleep(2);
  
  ## Camera is now connected, now take one picture
  print("Pentax DSLR camera is now connected ...")
  GPIO.output(PRINT_LED, False)
  blinkGreenLed(3)
  gpout = subprocess.check_output("sudo pslr-shoot -m P -i 400 -r 6 -q 3 -o /home/pi/dateset.jpg", stderr=subprocess.STDOUT, shell=True)
  f = open('/home/pi/dateset.jpg', 'rb')
  tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal', details=False)
  picDateStr = str(tags['EXIF DateTimeOriginal'])
  picDateStr = picDateStr.replace(":", "-", 2)

  sysDate = datetime.datetime.now()
  picDate = datetime.datetime.strptime(picDateStr, '%Y-%m-%d %H:%M:%S')
  print('Date from EXIF..: '+ picDateStr)
  print('Sysdate is......: '+ sysDate.strftime('%Y-%m-%d %H:%M:%S'))
  ## we assume that sysdate is bigger than picdate
  if sysDate > picDate:
    delta = sysDate - picDate
  else:
    delta = picDate - sysDate
  print('time delta is...: '+ str(delta))
  if delta.seconds > 14400:
    print('difference too big, setting system clock ...')
    ## setting sysclock
    try:
      setDateOut = subprocess.check_output("sudo date \"+%Y-%m-%d %T\" -s \""+ picDateStr +"\"", stderr=subprocess.STDOUT, shell=True)
      print('successfull: '+ setDateOut)
    except CalledProcessError as e:
      print('setting sysdate was not successfull:\n'+ e.output)
  time.sleep(1)
  GPIO.output(PRINT_LED, False)
  c = 0
  while c <= 2:
    print('using picture to show preview (count='+ str(c) +')')
    if c > 0:
       blinkGreenLed(3)
       gpout = subprocess.check_output("sudo pslr-shoot -m P -i 400 -r 6 -q 3 -o /home/pi/dateset.jpg", stderr=subprocess.STDOUT, shell=True)
    # show preview for setting up the camera
    pygame.display.init()
    img = pygame.image.load( '/home/pi/dateset.jpg' )
    img = pygame.transform.scale(img, (640, 428))
    screen = pygame.display.set_mode( img.get_size(), pygame.FULLSCREEN )
    screen.blit( img, (0,0) )
    pygame.display.flip()
    time.sleep(15)
    c = c + 1
  pygame.quit() 
else:
  cam = PiCamera(resolution=(3280, 2464))
  cam.vflip = True
  cam.hflip = True
  GPIO.output(PRINT_LED, False)
  blinkGreenLed(5)
  cam.start_preview()
  ready = False
  while ready == False:
    buttonState = GPIO.input(SWITCH)
    if ((not prevButtonState) and buttonState):
      print("Button pressed")
      ready = True
    time.sleep(0.05)
  cam.stop_preview()
  blinkGreenLed(5)  

time.sleep(2)
# Reset button state after picam config
prevButtonState = GPIO.input(SWITCH)

# We are ready
print("Setup ready, start waiting for button ...")
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
