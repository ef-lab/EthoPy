# PyMouse
State control system for automated behavioral training


# INSTRUCTIONS FOR INSTALL

Get latest raspbian OS
in raspi-config:
 - enable ssh
 - disable screen blanking
 - enable Desktop auto-login

Change hostname 
```bash
sed -r -i s/raspberrypi/HOSTNAME/g /etc/hostname /etc/hostname
sed -r -i s/raspberrypi/HOSTNAME/g /etc/hosts /etc/hosts
```

Change username
```bash
sudo useradd -s /bin/bash -d /home/USERNAME/ -m -G sudo USERNAME
sudo passwd USERNAME
mkhomedir_helper USERNAME
sudo userdel -r -f pi
```

Install salt for remote control, you need to have a salt-master server!
```bash
sudo apt install salt-minion
echo 'master: YOUR_SALT-MASTER_IP' | sudo tee -a /etc/salt/minion
echo 'id: HOSTNAME' | sudo tee -a /etc/salt/minion
sudo service salt-minion restart
```

X display settings for ssh run
```bash
sed -i -e '$aexport DISPLAY=:0' ~/.profile
sed -i -e '$axhost +  > /dev/null' ~/.profile
```

Install dependent libraries
```bash
sudo apt update
sudo apt install python-dev libatlas-base-dev build-essential libavformat-dev libavcodec-dev libswscale-dev libsquish-dev libeigen3-dev libopenal-dev libfreetype6-dev zlib1g-dev libx11-dev libjpeg-dev libvorbis-dev libogg-dev libassimp-dev libode-dev libssl-dev libgles2 libgles1 libegl1 -Y
```

Install python packages
```bash
sudo pip3 install 'numpy>=1.19.1' pygame==1.9.6 cython pybind11 scipy datajoint omxplayer-wrapper imageio imageio-ffmpeg
```

Install correct multitouch driver for 7" inch raspberry pi screen
```bash
git clone http://github.com/ef-lab/python-multitouch ~/github/python-multitouch
cd ~/github/python-multitouch/library
sudo python3 setup.py install
```

Install panda3d version for raspberry pi
```bash
wget ftp://eflab.org/shared/panda3d1.11_1.11.0_armhf.deb
sudo dpkg -i panda3d1.11_1.11.0_armhf.deb
```

Enable pigpio service
```bash
wget https://raw.githubusercontent.com/joan2937/pigpio/master/util/pigpiod.servicesudo cp pigpiod.service /etc/systemd/system
sudo systemctl enable pigpiod.service
sudo systemctl start pigpiod.service
```

Get PyMouse
```bash
git clone http://github.com/ef-lab/PyMouse ~/github/PyMouse
```

Create dj_local_conf.json with the correct parameters in the PyMouse folder:
```json
{
   "database.host": "YOUR DATABASE",
    "database.user": "USERNAME",
    "database.password": "PWD",
    "database.port": PORT,
    "database.reconnect": true,
    "database.enable_python_native_blobs": true
}
```

Create tables
```bash
cd ~/github/PyMouse
python3 -c 'from core.Experiment import *'
python3 -c 'from core.Stimulus import *'
python3 -c 'from core.Behavior import *'
python3 -c 'from Stimuli import *'
python3 -c 'from Behaviors import *'
python3 -c 'from Experiments import *'
```
