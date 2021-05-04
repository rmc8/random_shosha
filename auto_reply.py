import os
import random
import shutil
from datetime import datetime

import tweepy
import dropbox
import pandas as pd

from local_module.api_settings import API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_SECRET, DB_ACCESS_TOKEN, UID


class StreamListener(tweepy.StreamListener):
    def __init__(self, dbo, api, me, target):
        super().__init__(api=api)
        self.followers = None
        self.target = target
        self.me = me
        self.dt = datetime.now()
        self.dropbox = dbo
    
    def refresh_followers(self):
        min_sec: int = 60
        refresh_min: int = 15
        refresh_sec: int = min_sec * refresh_min
        now = datetime.now()
        if self.followers is None or (now - self.dt).seconds >= refresh_sec:
            self.followers = {fid for fid in tweepy.Cursor(self.api.followers_ids, user_id=self.me.id).items()}
            self.dt = now
    
    def is_follower(self, uid: int) -> bool:
        return uid in self.followers
    
    def tweet(self, status):
        requester: str = status.user.screen_name
        tweet_id: int = status.id
        file_path, tweet = self.dropbox.get_subject()
        tweet: str = f"@{requester} \n{tweet}"
        try:
            self.api.update_with_media(filename=file_path,
                                       status=tweet,
                                       in_reply_to_status_id=tweet_id)
        finally:
            os.remove(file_path)
    
    def on_status(self, status):
        self.refresh_followers()
        uid: int = status.user.id
        if self.is_follower(uid) and f"@{self.target}" in status.text:
            self.tweet(status)


class DropBoxController:
    def __init__(self, db_obj, df):
        self.db_obj = db_obj
        self.df = df
    
    def _choice_subject(self):
        CARD_INDEX: int = 0
        card_list: list = random.choice(self.df.values.tolist())
        card_no: str = card_list[CARD_INDEX]
        subjects = self.db_obj.files_list_folder(f"/{card_no}", recursive=True).entries
        subject = random.choice(subjects)
        return subject, card_list
    
    def _dl_file(self, subject: str) -> str:
        now = datetime.now()
        file_path: str = f"./tmp/{now:%Y%m%d_%H%M%S}.png"
        with open(file_path, "wb") as f:
            _, res = self.db_obj.files_download(path=subject)
            f.write(res.content)
        return file_path
    
    @staticmethod
    def _get_card_name(path: str) -> str:
        return f"card{path[-19:-4]}"
    
    def get_subject(self):
        subject, card_list = self._choice_subject()
        file_path = self._dl_file(subject.path_display)
        card_name = self._get_card_name(subject.path_display)
        TITLE_INDEX = 1
        URL_INDEX = 2
        AUTHOR_INDEX = 3
        tweet_lines = [f"『{card_list[TITLE_INDEX]}』",
                       card_list[AUTHOR_INDEX],
                       f"CARD: https://www.aozora.gr.jp/{card_list[URL_INDEX]}",
                       f"#ランダム書写 #random_shosha #{card_name}"]
        tweet = "\n".join(tweet_lines)
        return file_path, tweet


def twitter_obj(api_key: str, api_secret_key: str,
                access_token: str, access_token_secret: str):
    def gen_twitter_obj(**kwargs):
        auth = tweepy.OAuthHandler(api_key, api_secret_key)
        auth.set_access_token(access_token, access_token_secret)
        return tweepy.API(auth, wait_on_rate_limit=True, **kwargs)
    
    return gen_twitter_obj


def dropbox_obj(token: str):
    dbx = dropbox.Dropbox(token)
    dbx.users_get_current_account()
    return dbx


def init_dir(dir_name):
    if os.path.exists(dir_name):
        shutil.rmtree(dir_name)
    os.mkdir(dir_name)


def main():
    # Init
    init_dir("./tmp")
    
    # Dropbox
    dbx = dropbox_obj(DB_ACCESS_TOKEN)
    df = pd.read_csv("./db/random_shosha.tsv", sep="\t")
    dbc = DropBoxController(dbx, df)
    
    # Twitter
    gen_twi_obj = twitter_obj(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_SECRET)
    api = gen_twi_obj()
    my_info = api.me()
    streamListener = StreamListener(dbo=dbc, api=api, me=my_info, target=UID)
    stream = tweepy.Stream(auth=api.auth, listener=streamListener)
    stream.filter(track=[f"@{UID}"], is_async=True)


if __name__ == "__main__":
    main()
