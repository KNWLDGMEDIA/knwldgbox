import datetime
import sys

class utils:

    def error_with_reason(self, reason, to_break = False, code = 1000):
        print(f"[{self.date_}] - Stop Reason: " + reason)
        if to_break == True:
            sys.exit(code)
    
    def __init__(self):
        self.date_ = datetime.datetime.now()