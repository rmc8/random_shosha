import os
import pickle
from datetime import datetime, timedelta
from time import sleep


def main():
    now = datetime.now()
    dt_pkl = "datetime.pickle"
    if os.path.exists(dt_pkl):
        with open(dt_pkl, mode="rb") as f:
            pre_dt = pickle.load(f)
        if (now - pre_dt).seconds <= 60 * 60:
            exit()
    with open(dt_pkl, mode="wb") as dt:
        pickle.dump(now - timedelta(minutes=5), dt)
    while True:
        os.system("python auto_reply.py")
        sleep(30)


if __name__ == "__main__":
    main()
