# Home Assistant configuration


# Remote development tools:

## Desktop:
 - visual studio code
 - remote-vscode [0]

## Raspberry:
 - ssh access
 - rmate [1]

## Install rmate
    (homeassistant)$ sudo -u homeassistant -s -H pip3 install rmate

## edit the file on vscode
    (desktop/laptop)$ ssh -R 52698:localhost:52698 hassbian
    (homeassistant)$ sudo -u homeassistant -s -H    
    (homeassistant)$ export PATH=$HOME/.local/bin:$PATH
    (homeassistant)$ rmate .homeassistant/configuration.yaml
    (homeassistant)$ rmate .homeassistant/custom_components/besmart/climate.py   


### rif.  
 [0] https://github.com/rafaelmaiolla/remote-vscode  
 [1] https://github.com/sclukey/rmate-python

# Commands
 
##System start/stop/restart

    sudo systemctl start home-assistant@homeassistant.service
    sudo systemctl stop home-assistant@homeassistant.service
    sudo systemctl restart home-assistant@homeassistant.service

##Update

    source /srv/homeassistant/bin/activate
    pip3 install --upgrade homeassistant

## Install deConz

    wget -O - http://phoscon.de/apt/deconz.pub.key | \
           sudo apt-key add -

    sudo sh -c "echo 'deb http://phoscon.de/apt/deconz \
            $(lsb_release -cs) main' > \
            /etc/apt/sources.list.d/deconz.list"

    sudo apt update

    sudo apt install deconz

### Start headless mode
    systemctl enable deconz

### Logs

### rif.
 [0] https://github.com/dresden-elektronik/deconz-rest-plugin/wiki/Supported-Devices
 [1] https://github.com/sclukey/rmate-python

