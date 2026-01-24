![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)


#PlayingonSONOS

## License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for details.


## Prerequisites
Raspberry Pi 3 or 4

https://github.com/jishi/node-sonos-http-api as sonos api Server in your network

sudo apt update && sudo apt upgrade -y

sudo apt install -y python3 python3-pip python3-venv git

mkdir ~/playingonsonos
cd ~/playingonsonos

## Installation
install.sh

chmod +x install.sh

./install.sh

curl -s https://raw.githubusercontent.com/PnKStR/PlayingonSONOS/main/install.sh | bash

## or Installation
git clone https://github.com/PnKStR/PlayingonSONOS.git
cd PlayingonSONOS

## Start the App
python3 app.py

http://<raspberry-ip>:5008