from threading import Thread
from time import sleep

from bot.db.models import *


def update():
    print('Started DB updater...')

    while True:
        with db_session:
            song = Song.select(lambda s: not s.scraped).limit(20)

            if len(song) > 1:
                for i in range(0, min(len(song), 20)):
                    song[i].update()

            print('Updated ' + str(len(song)) + ' songs')

        sleep(3)


def setup():
    thread = Thread(target=update)
    thread.start()
