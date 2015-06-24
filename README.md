RPi_photobooth
==============

These files are supplied as part of an [Instructable](http://www.instructables.com/id/Raspberry-Pi-photo-booth-controller/) that describes how to build a photobooth using a Raspberry Pi as the "brains" of a camera, printer, and user interface controller.

## Pentax Version
### Using pslr-shoot instead of gphoto2
Getting pslr-shoot from the [PK-Remote](https://sourceforge.net/projects/pkremote/) project by just compile the command line tool:
```bash
sudo make cli
sudo make install
```

### Multiple button function
Pentax version uses button with long press (> 2seconds) for shutting down the Raspberry Pi.

### Hard disk support
If a hard disk is connected to the raspberry pi, i suggest the pi 2 because of the maximum current usage at the usb port, you can configure
the photobooth script to use that:

* Get UUID from your hard disk with `sudo blkid`
 * Something like `/dev/sda1` should appear and you copy the character after UUID
 * From this `/dev/sdb1: LABEL="Mobil" UUID="46DFB869DCB85541" TYPE="ntfs"` you need only `46DFB869DCB85541`
* Edit `/etc/rc.local` like for the startup script
 * Add this line in front of the photobooth startup:
  * `mount -t ntfs-3g -o uid=1000,gid=1000,umask=007 UUID=<your-uuid-here> /mnt/hdd`
* Reboot
* Check if hard disk was mounted with `mount`
* Create folders
 * `/mnt/hdd/photobooth_images`, easiest way: `mkdir -p /mnt/hdd/photobooth_images`
 * `/mnt/hdd/PB_archive`, easiest way: `mkdir -p /mnt/hdd/PB_archive`
* Script will automatically find hard drive folder and print this at startup
