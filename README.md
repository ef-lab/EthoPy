# PyMouse
State control system for automated behavioral training


INSTRUCTIONS FOR INSTALL
# get latest raspbian OS
#
# raspi-config
# - enable ssh
# - disable screen blanking
# - enable Desktop auto-login

# change hostname 
sed -r -i s/raspberrypi/HOSTNAME/g /etc/hostname /etc/hostname
sed -r -i s/raspberrypi/HOSTNAME/g /etc/hosts /etc/hosts

# change username
sudo useradd -s /bin/bash -d /home/USERNAME/ -m -G sudo USERNAME
sudo passwd USERNAME
mkhomedir_helper USERNAME
sudo userdel -r -f pi

# install salt for remote control, you need to have a salt-master server!
sudo apt install salt-minion
echo 'master: YOUR_SALT-MASTER_IP' | sudo tee -a /etc/salt/minion
echo 'id: HOSTNAME' | sudo tee -a /etc/salt/minion
sudo service salt-minion restart

# X display settings for ssh run
sed -i -e '$aexport DISPLAY=:0' ~/.profile
sed -i -e '$axhost +  > /dev/null' ~/.profile

# install dependent libraries
sudo apt update
sudo apt install python-dev libatlas-base-dev build-essential libavformat-dev libavcodec-dev libswscale-dev libsquish-dev libeigen3-dev libopenal-dev libfreetype6-dev zlib1g-dev libx11-dev libjpeg-dev libvorbis-dev libogg-dev libassimp-dev libode-dev libssl-dev libgles2 libgles1 libegl1 -Y

# instal python packages
sudo pip3 install 'numpy>=1.19.1' pygame==1.9.6 cython pybind11 scipy datajoint omxplayer-wrapper imageio imageio-ffmpeg

# install correct multitouch driver for 7" inch raspberry pi screen
git clone http://github.com/ef-lab/python-multitouch ~/github/python-multitouch
cd ~/github/python-multitouch/library
sudo python3 setup.py install

# install panda3d version for raspberry pi
wget ftp://eflab.org/shared/panda3d1.11_1.11.0_armhf.deb
sudo dpkg -i panda3d1.11_1.11.0_armhf.deb

# enable pigpio service
wget https://raw.githubusercontent.com/joan2937/pigpio/master/util/pigpiod.servicesudo cp pigpiod.service /etc/systemd/system
sudo systemctl enable pigpiod.service
sudo systemctl start pigpiod.service

# get PyMouse
git clone http://github.com/ef-lab/PyMouse ~/github/PyMouse

# create dj_local_conf.json with the correct parameters in the PyMouse folder:
#{
#   "database.host": "YOUR DATABASE",
#    "database.user": "USERNAME",
#    "database.password": "PWD",
#    "database.port": PORT,
#    "database.reconnect": true,
#    "database.enable_python_native_blobs": true
#}

# create tables
cd ~/github/PyMouse
python3 -c 'from core.Experiment import *'
python3 -c 'from core.Stimulus import *'
python3 -c 'from core.Behavior import *'
python3 -c 'from Stimuli import *'
python3 -c 'from Behaviors import *'
python3 -c 'from Experiments import *'
