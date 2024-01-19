from config_private_fullnodes_status import *
from src.fullnodes_status import FullNodesStatusBot

bot = FullNodesStatusBot(ADMIN_MIXIN_KEYSTORE, HTTP_ZEROMESH)

bot.run(FULLNODES_AUTHS, ADMINS_MIXIN_IDS)
