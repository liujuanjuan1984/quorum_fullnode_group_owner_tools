"""
用途：
远程监控多个 fullnodes 的状态，需要 fullnodes 提供 chain 级别的 host:port?jwt 
这种级别的权限，只能用于监控自有 fullnodes

通过 mixin bot 发送监控信息

依赖：

pip install mixinsdk
pip install quorum_fullnode_py 

"""

import datetime
import logging
import os
import time

from mixinsdk.clients.client_http import HttpClient_WithAppConfig
from mixinsdk.clients.config import AppConfig
from mixinsdk.types.message import pack_message, pack_post_data
from officy import JsonFile
from quorum_fullnode_py import FullNode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    filename=f"{datetime.date.today()}_fullnodes_status.log",
)


class FullNodesStatusBot:
    def __init__(self, mixin_keystore, mixin_http_api_base):
        self.xin = HttpClient_WithAppConfig(
            AppConfig.from_payload(mixin_keystore), api_base=mixin_http_api_base
        )

    def fullnode_status(self, ip, port, jwt):
        url = f"http://{ip}:{port}"
        bot = FullNode(url, jwt)
        node = bot.api.node_info()
        groups = bot.api.groups()
        report = {
            "node_status": node["node_status"],
            "groups_num": len(groups),
            "groups": {},
        }

        networks = bot.api.network()["groups"]
        for g in groups:
            peers = 0
            for item in networks:
                if item["GroupId"] == g["group_id"]:
                    peers = len(item["Peers"] or [])
                    break
            report["groups"][g["group_id"]] = {
                "role": "OWNER" if g["owner_pubkey"] == g["user_pubkey"] else "USER",
                "last_update": str(
                    datetime.datetime.fromtimestamp(g["last_updated"] // 1e9)
                ),
                "peers": peers,
                "group_name": g["group_name"],
                "blocks": g["currt_top_block"],
            }

        return report

    def tell_admin(self, post, mixin_id):
        self.xin.api.message.send_messages(
            pack_message(
                pack_post_data(post),
                conversation_id=self.xin.get_conversation_id_with_user(mixin_id),
            )
        )

    def run(self, fullnodes_auths: list, admins_mixin_ids: list):
        filename = f"fullnodes_status_{datetime.date.today()}.json"
        if not os.path.exists(filename):
            status = {}
        else:
            try:
                status = JsonFile(filename).read({})
            except:
                status = {}
        if status.get("tell_admin"):
            return

        post = f"## FullNodes {datetime.date.today()}\n"
        if "origin" not in status:
            status["origin"] = {}
        for name, ip, port, jwt in fullnodes_auths:
            if name not in status["origin"]:
                try:
                    report = self.fullnode_status(ip, port, jwt)
                except Exception as err:
                    report = {"error": str(err)}
                status["origin"][name] = report
                JsonFile(filename).write(status)

            report = status["origin"][name]
            if "error" not in report:
                pieces = [
                    f"### 🥰{report['node_status']} {name} ",
                    f"{report['groups_num']} Groups\n\n",
                    "| role | group_name | blocks | peers | last_updated |\n",
                    "|-----|-----|-----|-----|-----|\n",
                ]
                for g, v in report["groups"].items():
                    pieces.extend(
                        [
                            f"| {v['role']} | {v['group_name']} ",
                            f"| {v['blocks']} |  {v['peers']} ",
                            f"|  {v['last_update']} |\n",
                        ]
                    )
                text = "".join(pieces)
            else:
                text = f"### 😱ERROR {name}\n\n```sh\n{report['error']}\n```\n"
            post += text

        for mixin_id in admins_mixin_ids:
            self.tell_admin(post, mixin_id)
            time.sleep(1)

        status["tell_admin"] = str(datetime.datetime.now())
        JsonFile(filename).write(status)
