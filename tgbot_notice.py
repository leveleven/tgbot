#/usr/bin/python3
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import shutil
import datetime

import ansible.constants as C
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager
import ansible.context as a_context

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ansible host组
groups = ['group1', 'group2']

# Enable logging
# logging.basicConfig(
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
# )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    chat_id = update.effective_message.chat_id
    context.job_queue.run_daily(reward, time=datetime.time(18, 0), chat_id=chat_id, name="get reward", data=groups)
    await update.message.reply_text("每日自动统计开启，使用/help获取更多信息")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("/start 每日自动统计开启\n/set {time second} 设置自动检查（单位：秒）\n/unset 取消自动检查\n/get_reward 获取当前总收益\n/help 获取帮助")

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    print(current_jobs)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

async def get_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    try:
        # context.job_queue.run_daily(healthy_check, time=datetime.time(18, 0), chat_id=chat_id, name="get reward")
        context.job_queue.run_once(reward, when=1, chat_id=chat_id, data=groups)
        await update.effective_message.reply_text("正在获取收益，请等待")
    except (IndexError, ValueError):
        await update.effective_message.reply_text("用法：/get_reward")

async def set_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = float(context.args[0])
        if due < 0:
            await update.effective_message.reply_text("时间不能为负数")
            return
        elif due < 179:
            await update.effective_message.reply_text("时间必须大于180秒")
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        now = datetime.datetime.now()
        context.job_queue.run_repeating(healthy_check, interval=due, chat_id=chat_id, name="healthy check")

        text = "计划任务创建成功！"
        if job_removed:
            text += "旧任务被移除。"
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("用法：/set <seconds>")

async def unset_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists("healthy check", context)
    text = "定时检查已取消" if job_removed else "并没有找到定时检查任务"
    await update.message.reply_text(text)

class ResultsCollectorJSONCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in.

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin.
    """

    def __init__(self, *args, **kwargs):
        super(ResultsCollectorJSONCallback, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

    def v2_runner_on_unreachable(self, result):
        host = result._host
        self.host_unreachable[host.get_name()] = result

    def v2_runner_on_ok(self, result, *args, **kwargs):
        """Print a json representation of the result.

        Also, store the result in an instance attribute for retrieval later
        """
        host = result._host
        self.host_ok[host.get_name()] = result
        # print(json.dumps({host.name: result._result}, indent=4))

    def v2_runner_on_failed(self, result, *args, **kwargs):
        host = result._host
        self.host_failed[host.get_name()] = result

def ansible_init(results_callback):
    # Set up CLI arguments for Ansible context
    a_context.CLIARGS = ImmutableDict(
        connection='ssh',
        module_path=['/usr/local/lib/python3.9/dist-packages/ansible', '/usr/share/ansible/plugins/modules'],
        forks=10,
        become=None,
        become_method=None,
        become_user=None,
        check=False,
        diff=False,
        verbosity=0,
        syntax=None,
        start_at_task=None,
        ansible_cfg='/etc/ansible/ansible.cfg',  # 假设ansible.cfg位于默认位置或通过ANSIBLE_CONFIG设置
    )

    # DataLoader handles finding and reading yaml, json, and ini files
    loader = DataLoader()
    passwords = dict(vault_pass='secret')

    # Define your inventory source, ensure this path is correct
    inventory_source = '/etc/ansible/hosts'

    # Set up inventory, using a path to ansible inventory file
    inventory = InventoryManager(loader=loader, sources=inventory_source)

    # Set up variable manager, which will hold all the variable information
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    # Create the TaskQueueManager, which handles the execution of tasks
    tqm = TaskQueueManager(
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        passwords=passwords,
        stdout_callback=results_callback,
    )

    return results_callback, variable_manager, loader, tqm

def ansible_play(play_source, variable_manager, loader, tqm):
    # Create the play object from the play_source and the objects above
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    # Execute the play and store the result
    try:
        result = tqm.run(play)
    except Exception as e:
        # Print any exception that occurs during the play execution
        print(f"Exception during play execution: {e}")
        return None
    finally:
        # Clean up after the TaskQueueManager
        tqm.cleanup()

        # Clean up any temporary files created by DataLoader
        if loader:
            loader.cleanup_all_tmp_files()

    # Remove Ansible's temporary directory
    shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

async def healthy_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    results_callback = ResultsCollectorJSONCallback()

    results_callback, variable_manager, loader, tqm = ansible_init(results_callback)

    # Define a simple play to ping all hosts
    cmd = 'docker container ls --format json | jq -s'
    play_source = dict(
        name="Ansible Play",
        hosts='all',
        gather_facts='no',
        tasks=[
            dict(action=dict(module='shell', args=cmd))
        ],
    )
    ansible_play(play_source=play_source, variable_manager=variable_manager, loader=loader, tqm=tqm)

    host_status = {'ok': [], 'failed': []}
    for host, result in results_callback.host_ok.items():
        for container in json.loads(str(result._result['stdout'])):
            if container['Image'] == "leveleven/ceremony":
                host_status['ok'].append({'host': host, 'content': container})
    if (results_callback.host_failed.items().__len__() != 0) or (results_callback.host_unreachable.items().__len__() != 0):
        for host, result in results_callback.host_failed.items():
            host_status['failed'].append({'host': host, 'msg': result._result['msg']})
        for host, result in results_callback.host_unreachable.items():
            host_status['failed'].append({'host': host, 'msg': result._result['msg']})

    # return host_status
    job = context.job
    if len(host_status['failed']):
        text = "🟢 正常运行的节点数量：" + str(len(host_status['ok'])) + "\n\n" + "🔴 故障的节点数量" + str(len(host_status['failed'])) + "\n"
        for node in host_status['failed']:
            text += node['host'] + ": " + node['msg'] + "\n-------------------------"
        await context.bot.send_message(job.chat_id, text=text)

async def reward(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    text = '收益列表: \n'

    for group in job.data:
        results_callback = ResultsCollectorJSONCallback()
        results_callback, variable_manager, loader, tqm = ansible_init(results_callback)

        cmd = 'docker exec -it quilibrium-node-1 node -balance -signature-check\=false | grep QUIL | awk {"print \$3"}'

        play_source = dict(
            name="Ansible Play",
            hosts=group,
            gather_facts='no',
            tasks=[
                dict(action=dict(module='shell', args=cmd))
            ],
        )

        ansible_play(play_source=play_source, variable_manager=variable_manager, loader=loader, tqm=tqm)
        host_status = {'ok': [], 'failed': []}
        reward_sum = 0
        for host, result in results_callback.host_ok.items():
            host_status['ok'].append({'host': host, 'reward': result._result['stdout']})
            reward_sum += float(result._result['stdout'])
        if (results_callback.host_failed.items().__len__() != 0) or (results_callback.host_unreachable.items().__len__() != 0):
            for host, result in results_callback.host_failed.items():
                host_status['failed'].append({'host': host, 'msg': result._result['msg']})
            for host, result in results_callback.host_unreachable.items():
                host_status['failed'].append({'host': host, 'msg': result._result['msg']})
        text += f'{group}总收益: {reward_sum}\n'
        if host_status['failed']:
            text += '未计入收益节点:\n'
            for node in host_status['failed']:
                text += f'{node["host"]}\n'
    await context.bot.send_message(job.chat_id, text=text)

def main() -> None:

    token = "bot_token"
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set", set_check))
    application.add_handler(CommandHandler("unset", unset_check))
    application.add_handler(CommandHandler("get_reward", get_reward))
    application.add_handler(CommandHandler("help", help))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
