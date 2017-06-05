# <img src="https://raw.github.com/PapyrusThePlant/MusicPanda/master/images/panda.jpg" width="100">Music Panda

Music panda is a simplistic discord  music bot made for funzies.

# Installation

    $ git clone https://github.com/PapyrusThePlant/MusicPanda
    $ cd MusicPanda
    $ python3 -m pip install -U -r requirements.txt

Make sure to spread some panda love by naming your bot `Music Panda` and by using the provided image as its avatar ! :) 

# Requirements

Binaries:
* FFmpeg
* Python 3.6+

Python packages (preferably, give the file `requirements.txt` to pip) :
* discord.py with voice support from the rewrite branch
* youtube_dl

Other:
* One configuration file named `conf.json` as follow :

        {
        "prefix": "insert a custom command prefix here",
        "token": "copy your bot token here"
        }
    Note that the bot will always recognise its mention as a prefix