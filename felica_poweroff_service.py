# -*- coding: utf-8 -*-

import sys
import datetime
from ctypes import *
import shlex
import subprocess
import time
from slacker import Slacker

# libpafe.hの77行目で定義
FELICA_POLLING_ANY = 0xffff
SLACK_TOKEN = '<your token>'

def read_felica_idm():
    libpafe = cdll.LoadLibrary("/usr/local/lib/libpafe.so")

    libpafe.pasori_open.restype = c_void_p
    pasori = libpafe.pasori_open()

    libpafe.pasori_init(pasori)

    libpafe.felica_polling.restype = c_void_p
    felica = libpafe.felica_polling(pasori, FELICA_POLLING_ANY, 0, 0)

    idm = c_uint16()
    libpafe.felica_get_idm.restype = c_void_p
    libpafe.felica_get_idm(felica, byref(idm))

    # 認識できない時は'0'が入ってくる
    result = idm.value

    # READMEより、felica_polling()使用後はfree()を使う
    # なお、freeは自動的にライブラリに入っているもよう
    libpafe.free(felica)
    libpafe.pasori_close(pasori)

    return result


def switch_act_led(trigger):
    cmd_echo = shlex.split("echo %s" % trigger)
    cmd_redirect = shlex.split("sudo tee /sys/class/leds/led0/trigger")

    p1 = subprocess.Popen(cmd_echo, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(cmd_redirect, stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()[0]


def write_log_file(msg):
    f = open('/home/pi/felica-poweroff/log.txt', 'a')
    now = datetime.datetime.now()
    f.write(now.strftime("%Y/%m/%d %H:%M:%S") + msg + '\n')
    f.close()



if __name__ == '__main__':

    # FeliCaが無い時のログ出力
    if read_felica_idm() == 0:
         write_log_file('FeliCa not found.')
         # Serviceを再実行するよう、0以外を返す
         sys.exit(1)

    # FeliCaを認識した時のログ出力
    write_log_file('Found!')

    # heartbeat > 2秒待ち > microSDランプ の順に切替
    switch_act_led('heartbeat')
    time.sleep(2)
    switch_act_led('mmc0')

    # Slackへの通知
    slack = Slacker(SLACK_TOKEN)
    slack.chat.post_message('#general', 'poweroff now')

    # シャットダウン
    cmd_power_off = shlex.split("sudo systemctl poweroff")
    subprocess.Popen(cmd_power_off)
    # Serviceを再実行しないよう、0を返す
    sys.exit(0)