import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

##
# 1. 改进：每个群有单独的队列

lottery_list = []
admin="user"
# lottery_list = ["aaa", "bbb", "ccc", "ddd", "eee", "fff", "ggg", "hhh", "iii", "jjj", "kkk", "lll", "mmm", "nnn", "ooo", "ppp", "qqq", "rrr", "sss"]

# 定义抽奖命令的处理函数
async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 获取群组ID和参与抽奖的用户列表
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    username = update.message.from_user.username

    # prize_member = [prize_1_member, prize_2_member, prize_3_member]
    prize_member = [5]
    prize = []

    if username == admin:
        print("管理员：%s 开奖" % username)
        # 从参与者列表中随机选择一个中奖者
        if len(lottery_list) == 0:
            await context.bot.send_message(chat_id=chat_id, text="参与者为0，无法开奖", reply_to_message_id=message_id)
            return
        
        prize_message = ''
        for index, item in enumerate(prize_member):
            prize.append([])
            for _ in range(item):
                winner = random.choice(lottery_list)
                lottery_list.remove(winner)
                prize[index].append('@'+winner)
            print(index)
            # print(prize[index])
            # if index == 0:
            #     prize_message = prize_message + '特等奖\n' + '\n'.join(prize[index]) + '\n'
            #     continue
            # prize_message = prize_message + str(index+1)+ '等奖\n' + '\n'.join(prize[index]) + '\n'
            prize_message = prize_message + '幸运奖\n' + '\n'.join(prize[index]) + '\n'
        
        # 发送中奖者信息到群组
        lottery_list.clear()
        await context.bot.send_message(chat_id=chat_id, text=prize_message)
    else:
        await context.bot.send_message(chat_id=chat_id, text="你不是管理员，无法开奖", reply_to_message_id=message_id)

async def lottery(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    username = update.message.from_user.username

    if username in lottery_list:
        await context.bot.send_message(chat_id=chat_id, text="已参与", reply_to_message_id=message_id)
        return

    if username is None:
        return
    print(username)
    lottery_list.append(username)

    await context.bot.send_message(chat_id=chat_id, text="成功参与", reply_to_message_id=message_id)

async def listmember(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    username = update.message.from_user.username

    if username == admin:
        print(lottery_list)
        listlen=len(lottery_list)
        if len(lottery_list) == 0:
            await context.bot.send_message(chat_id=chat_id, text="队列为空", reply_to_message_id=message_id)
            return
        await context.bot.send_message(chat_id=chat_id, text='\n'.join(lottery_list)+"\n参数人数："+str(listlen))
    else:
        await context.bot.send_message(chat_id=chat_id, text="无权调用", reply_to_message_id=message_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    username = update.message.from_user.username

    if username == admin:
        application.add_handler(CommandHandler("lottery", lottery))
        application.add_handler(CommandHandler("draw", draw))
        application.add_handler(CommandHandler("list", listmember))
        await context.bot.send_message(chat_id=chat_id, text="开始抽奖，请玩家点击或输入'/lottery'命令进行抽奖")
    else:
        await context.bot.send_message(chat_id=chat_id, text="无权调用", reply_to_message_id=message_id)

# 创建Updater对象并设置访问令牌
token="bot_token"
application = Application.builder().token(token).build()
application.add_handler(CommandHandler("start", start))

# 启动机器人
application.run_polling()
