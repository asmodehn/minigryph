"""
A bare-bones wrapper class that allows us to turn off heartbeating if we don't want it.
"""

from builtins import object
import subprocess
import os 

class Heartbeat(object):
    def __init__(self, is_active=False):
        self.is_active = is_active

    def heartbeat(self, heartbeat_key):
        if self.is_active is True:
            filename = 'monit/heartbeat/%s.txt' % heartbeat_key
            subprocess.call(['touch', filename])



    #! following is useless
    # def check_file_existence(self, filename):
    #     if self.is_active is True:
    #         file_exists = os.path.exists(filename)

    #         if not folder_exists:
    #             os.makedirs(filename, exist_ok=True)