"""
用途：
fullnode group owner 用于监控 spam 行为。并自动处理：加入黑名单（标记已有数据为删除；之后无法再发布数据上链）。

依赖：

pip install quorum_data_py
pip install quorum_fullnode_py 
pip install quorum_mininode_py

"""


import datetime
import logging
import time

import requests
from quorum_data_py import feed
from quorum_data_py.trx_type import get_trx_type
from quorum_fullnode_py import FullNode
from quorum_mininode_py.crypto.account import pubkey_to_address

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler(f"{datetime.date.today()}_ban_spam.log")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class BanSpamBot:
    def __init__(
        self,
        url: str = None,
        jwt_token: str = None,
        port: int = None,
        feed_page: str = None,
        white_list: list = None,
    ):
        """
        如果是远程，需要提供 group owner fullnode 的接口 url 和 jwt_token
        如果是同一台机器，只需要提供 fullnode 的 api port
        """
        self.client = FullNode(url, jwt_token, port)
        self.feed_page = feed_page
        self.data = {}
        self.del_posts = []
        self.white_list = white_list
        logger.info("BanSpamBot start.")

    def get_latest_trxid(self, group_id: str, num: int = 20):
        trxs = self.client.api.get_content(num=num, reverse=True, group_id=group_id)
        if trxs:
            return trxs[-1]["TrxId"]
        return None

    def count_trxs_contents(self, group_id: str, trxs: list, times: int = 3):
        for trx in trxs:
            self.data[group_id]["start_trx"] = trx["TrxId"]
            if get_trx_type(trx) not in ["post", "comment"]:
                continue
            content = trx["Data"]["object"]["content"]
            if not content:
                continue
            if content not in self.data[group_id]["contents"]:
                self.data[group_id]["contents"][content] = [trx["SenderPubkey"]]
                continue
            self.data[group_id]["contents"][content].append(trx["SenderPubkey"])
            self.check_spam(content, group_id, times)

    def delte_from_feed_page(
        self, group_id, pubkey, start_trx, feed_admin, feed_page=None
    ):
        feed_page = feed_page or self.feed_page
        if not feed_page:
            raise ValueError("feed_page is None")
        while True:
            trxs = self.client.api.get_content(
                group_id=group_id, senders=[pubkey], start_trx=start_trx
            )
            if not trxs:
                break
            for trx in trxs:
                if get_trx_type(trx) == "post":
                    post_id = trx["Data"]["object"]["id"]
                    url = f"{feed_page}/api/posts/{post_id}"
                    if url not in self.del_posts:
                        resp = requests.delete(url, headers=feed_admin, timeout=15)
                        if resp.status_code == 200:
                            self.del_posts.append(url)
                            logger.info("del post %s", url)
                            time.sleep(1)

    def check_spam(self, content: str, group_id: str, times: int = 3):
        if len(self.data[group_id]["contents"][content]) < times:
            return

        senders = {}
        for sender in self.data[group_id]["contents"][content]:
            if sender in senders:
                senders[sender] += 1
            else:
                senders[sender] = 1
        banned = self.client.api.get_deny_list(group_id=group_id)
        benned_list = [i["Pubkey"] for i in banned]
        for sender, counts in senders.items():
            if sender in benned_list:
                continue
            if sender == self.client.api.group_info(group_id)["owner_pubkey"]:
                continue
            if self.white_list and sender in self.white_list:
                continue
            if counts >= times:
                self.client.api.add_deny_list(sender, group_id=group_id)
                logger.info("add to deny list. user %s content %s", sender, content)
                who = f"pubkey: {sender}"
                if self.feed_page:
                    who = f" {self.feed_page}/users/{pubkey_to_address(sender)} "
                info = feed.new_post(
                    f"🤖As producer I announce: \nuser({who}) ☠️ is banned to post trx to blockchain (group_id: {group_id}) for spam (post same content to blockchain more than three times). \nIf any question, please leave a comment below.🥰"
                )
                self.client.api.post_content(info, group_id=group_id)

    def ban_spam(self, group_id: str, num: int = 100, times: int = 3, seconds: int = 1):
        banned = self.client.api.get_deny_list(group_id=group_id)
        print(banned)

        if group_id not in self.data:
            trx_id = self.get_latest_trxid(group_id, num=num)
            self.data[group_id] = {"start_trx": trx_id, "contents": {}}

        while True:
            start_trx = self.data[group_id]["start_trx"]
            trxs = self.client.api.get_content(
                start_trx=start_trx, num=num, group_id=group_id
            )
            self.count_trxs_contents(group_id, trxs, times=times)
            time.sleep(seconds)
