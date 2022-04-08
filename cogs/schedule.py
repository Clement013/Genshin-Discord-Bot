import json
import asyncio
import discord
from datetime import datetime
from utility.GenshinApp import genshin_app
from discord.ext import commands, tasks
from utility.config import config
from utility.utils import log

class Schedule(commands.Cog, name='自動化(BETA)'):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.__daily_reward_filename = 'data/schedule_daily_reward.json'
        self.__resin_notifi_filename = 'data/schedule_resin_notification.json'
        try:
            with open(self.__daily_reward_filename, 'r', encoding='utf-8') as f:
                self.__daily_dict = json.load(f)
        except:
            self.__daily_dict = { }
        try:
            with open(self.__resin_notifi_filename, 'r', encoding='utf-8') as f:
                self.__resin_dict = json.load(f)
        except:
            self.__resin_dict = { }
        
        self.schedule.start()

    @commands.command(
        brief='設定自動化功能(論壇簽到、樹脂溢出提醒)',
        description='設定自動化功能，會在特定時間執行功能，執行結果會在當初設定指令的頻道推送，若要更改頻道，請在新的頻道重新設定指令一次',
        usage='<daily|resin> <on|off>',
        help=f'每日 {config.auto_daily_reward_time} 點左右自動論壇簽到，使用範例：\n'
            f'{config.bot_prefix}set daily on　　　開啟每日自動簽到\n'
            f'{config.bot_prefix}set daily off 　　關閉每日自動簽到\n\n'
            f'每小時檢查，當樹脂超過 {config.auto_check_resin_threshold} 時會發送提醒，使用範例：\n'
            f'{config.bot_prefix}set resin on　　　開啟樹脂提醒\n'
            f'{config.bot_prefix}set resin off 　　關閉樹脂提醒\n'
    )
    async def set(self, ctx, cmd: str, switch: str):
        log.info(f'set(user_id={ctx.author.id}, cmd={cmd} , switch={switch})')
        check, msg = genshin_app.checkUserData(str(ctx.author.id))
        if check == False:
            await ctx.reply(msg)
            return
        if cmd == 'daily':
            if switch == 'on':
                self.__add_user(str(ctx.author.id), str(ctx.channel.id), self.__daily_dict, self.__daily_reward_filename)
                await ctx.reply('每日自動簽到已開啟')
            elif switch == 'off':
                self.__remove_user(str(ctx.author.id), self.__daily_dict, self.__daily_reward_filename)
                await ctx.reply('每日自動簽到已關閉')
        if cmd == 'resin':
            if switch == 'on':
                self.__add_user(str(ctx.author.id), str(ctx.channel.id), self.__resin_dict, self.__resin_notifi_filename)
                await ctx.reply('樹脂額滿提醒已開啟')
            elif switch == 'off':
                self.__remove_user(str(ctx.author.id), self.__resin_dict, self.__resin_notifi_filename)
                await ctx.reply('樹脂額滿提醒已關閉')

    @tasks.loop(minutes=10)
    async def schedule(self):
        log.info(f'schedule() is called')
        now = datetime.now()
        # 每日 X 點自動簽到
        if now.hour == config.auto_daily_reward_time and now.minute < 10:
            log.info('每日自動簽到開始')
            # 複製一份避免衝突
            daily_dict = dict(self.__daily_dict)
            for user_id, value in daily_dict.items():
                channel = self.bot.get_channel(int(value['channel']))
                if channel == None:
                    self.__remove_user(str(user_id), self.__daily_dict, self.__daily_reward_filename)
                    continue
                result = await genshin_app.claimDailyReward(user_id)
                await channel.send(f'[自動簽到] <@{user_id}> {result}')
                await asyncio.sleep(3)
            log.info('每日自動簽到結束')
        # 每小時檢查樹脂
        if 30 <= now.minute < 40:
            log.info('自動檢查樹脂開始')
            resin_dict = dict(self.__resin_dict)
            for user_id, value in resin_dict.items():
                channel = self.bot.get_channel(int(value['channel']))
                if channel == None:
                    self.__remove_user(str(user_id), self.__resin_dict, self.__resin_notifi_filename)
                    continue
                result = await genshin_app.getRealtimeNote(user_id, True)
                if result != None:
                    embed = discord.Embed(title='', description=result, color=0xff2424)
                    await channel.send(f'<@{user_id}>，樹脂快要溢出啦！', embed=embed)
                await asyncio.sleep(3)
            log.info('自動檢查樹脂結束')


    @schedule.before_loop
    async def before_schedule(self):
        await self.bot.wait_until_ready()

    def __add_user(self, user_id: str, channel: str, data: dict, filename: str) -> None:
        data[user_id] = { }
        data[user_id]['channel'] = channel
        self.__saveScheduleData(data, filename)

    def __remove_user(self, user_id: str, data: dict, filename: str) -> None:
        try:
            del data[user_id]
        except:
            log.error(f'__remove_user(self, user_id={user_id}, data: dict)')
        else:
            self.__saveScheduleData(data, filename)
    
    def __saveScheduleData(self, data: dict, filename: str):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except:
            log.error(f'__saveScheduleData(data: dict, filename: {filename})')

def setup(client):
    client.add_cog(Schedule(client))