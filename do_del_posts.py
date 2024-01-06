"""手动触发删除 feed page 上指定用户自某个 trx 后的所有 trx（不在网页上显示）"""
from config_private import FEED_ADMIN, FEED_PAGES, GROUP_ID, PORT
from src.ban_spam import BanSpamBot

bot = BanSpamBot(port=PORT)

# update these
pubkey = ""
start_trx = ""

for feed_page in FEED_PAGES:
    bot.delte_from_feed_page(GROUP_ID, pubkey, start_trx, FEED_ADMIN, feed_page)
