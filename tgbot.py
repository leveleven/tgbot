import time
import telepot
from telepot.loop import MessageLoop

def handleRaffle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(content_type, chat_type, chat_id)

    if msg['text'] == '/raffle':
        bot.sendMessage(chat_id, 'winwinwin')

TOKEN = 'bot_token'

bot = telepot.Bot(TOKEN)
MessageLoop(bot, handleRaffle).run_as_thread()
print ('Listening ...')

# Keep the program running.
while 1:
    time.sleep(10)
