"""持续运行，监控 spam 行为"""
from config_private import FEED_PAGE, GROUP_ID, PORT, WHITE_LIST
from src.ban_spam import BanSpamBot

bot = BanSpamBot(port=PORT, feed_page=FEED_PAGE, white_list=WHITE_LIST)
bot.ban_spam(GROUP_ID)
