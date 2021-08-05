# PyMouse
State control system for automated, high-throughput behavioral training
It is tightly intergated with Database storage & control

Core modules:

[<img src="http://www.plantuml.com/plantuml/png/TP91Q-D038Nl_XM2FTkRN8CnOPT22-sblVQYsB8zT4PZPZHDwQylJXt5WV4jqVUafwVnCGe6ISuMySFmX04T16e5UR3qwXDt_trW2h3V5Lg7Xw-9Wd740d-i6KOP0X6l16zYNB8fRk1_DEAdyU4EH_411u9dFmmKGFy_iL3eiQMYGy4JHeBhZ-9NMvTfAXijhhOhEt_cicnqeHpKTTQmhcPQDSiwXIQggpJTofgahYpraj7h8CsXJJbsQPz9c2zpXzWBmQKClb-_mG7gQBxfiDyrBsWOeg0Ga0hglpDkxWTewdNx8t9dAOAC1CZ6eONJ8bk6m3lVv8PdvPQJfNusqjjl6SKBDpc35Ac3Z4icptBud0bQgvzCFePGm5QCvvXDe6-mDRtrpYKsBSupSXPd8oEC6Bep1hfw78cxvEmF">]

#### Experiment
Main state experiment Empty class that is overriden by other classes depending on the type of experiment.

A typical experiment state diagram:

[<img src="http://www.plantuml.com/plantuml/png/SoWkIImgAStDuT9mpIifgjHKqDMrKz08A4eDASfCpD7aWZEXCZ1XP377fFoY4ZIneDJonA8KDC60qhpCuWoG8AQ945EWOfvv9Qb5K0cOKPWoCFCmPP0vG4aDrufCe0CTKlDIW5u50000">]

Each of the states is discribed by 4 funcions:

_entry_: code that is run on entry to each state.  
_run_: Main run command.  
_next_: Defines the conditions for the transition to the next state.  
_exit_: Code that runs uppon the exit of the state.

Tables that are needed for the experiment that discribe the setup:

> SetupConfiguration  
> SetupConfiguration.Port  
> SetupConfiguration.Screen

The experiment parameters are specified in *.py script configuration files that are entered in the Task table within the lab_experriment schema. Some examples are in the conf folder but any folder that is accessible to the system can be used. Each protocol has a unique task_idx identifier that is used uppon running. 

Implemented experiment types:  
* MatchToSample: Experiment with Cue/Delay/Response periods 
* MatchPort: Stimulus matched to ports
* Navigate: Navigation experiment
* Passive: Passive stimulus presentation experiment
* FreeWater: Free water delivery experiment
* Calibrate: Port Calibration of water amount
* PortTest: Testing port for water delivery

#### Behavior
Empty class that handles the animal behavior in the experiment.  

IMPORTANT: Liquid calibration protocol needs to be run frequently for accurate liquid delivery

Implemented Behavior types:
* MultiPort:  Default RP setup with lick, liquid delivery and proximity port
* VRBall (beta): Ball for 2D environments with single lick/liquid delivery port
* Touch (beta): Touchscreen interface

#### Stimulus
Empty class that handles the stimuli used in the experiment.

Implemented stimulus types:
* Grating: Orientation gratings
* Bar: Moving bar for retinotopic mapping
* Movies: Movie presentation
* Olfactory: Odor persentation
* Panda: Object presentation
* VROdors: Virtual environment with odors
* SmellyObjects: Odor-Visual objects


Non-overridable classes:
#### Logger (non-overridable)
Handles all database interactions and it is shared across Experiment/Behavior/Stimulus classes
non-overridable

Data are storred in tables within 3 different schemata that are automatically created:

> lab_experiments  
> lab_behavior  
> lab_stimuli

#### Interface (non-overridable)
Handles all communication with hardware

## HOW TO RUN
Can be run either as a service that is controled by the SetupControl table
```bash
sudo python3 run.py
```

or can specify a task_idx to run directly. After it completes, the process ends.
```bash
sudo python3 run.py 1 
```

This process can be automated by either a bash script that runs on startup or through control from a salt server. 

## INSTALLATION INSTRUCTIONS (for Raspberry pi)
Get latest raspbian OS
in raspi-config:
 - enable ssh
 - disable screen blanking
 - enable Desktop auto-login

Change hostname - Optional, but it will make it easier to identify later
```bash
sed -r -i s/raspberrypi/<<HOSTNAME>>/g /etc/hostname /etc/hostname
sed -r -i s/raspberrypi/<<HOSTNAME>>/g /etc/hosts /etc/hosts
```

Change username - Optional
```bash
sudo useradd -s /bin/bash -d /home/<<USERNAME>>/ -m -G sudo USERNAME
sudo passwd <<USERNAME>>
mkhomedir_helper <<USERNAME>>
sudo userdel -r -f pi
```

Install salt for remote control, you need to have a salt-master server! - Optional
```bash
sudo apt install salt-minion
echo 'master: <<YOUR_SALT-MASTER_IP>>' | sudo tee -a /etc/salt/minion
echo 'id: HOSTNAME' | sudo tee -a /etc/salt/minion
sudo service salt-minion restart
```

X display settings for ssh run, important for Panda stimulus
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
    "database.password": "PASSWORD",
    "database.port": "PORT",
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
