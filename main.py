import discord
from discord import app_commands
from uptime_kuma_api import UptimeKumaApi, MonitorType
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
KUMA_URL = os.getenv("KUMA_URL")
KUMA_USERNAME = os.getenv("KUMA_USERNAME")
KUMA_PASSWORD = os.getenv("KUMA_PASSWORD")

if not all([DISCORD_TOKEN, KUMA_URL, KUMA_USERNAME, KUMA_PASSWORD]):
    raise ValueError("Missing required environment variables for Discord or Uptime Kuma")

class UptimeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"已同步 {len(self.tree.get_commands())} 個斜線命令")

client = UptimeBot()

@client.event
async def on_ready():
    print(f'Bot 已登入為 {client.user}')
    print(f'Bot ID: {client.user.id}')
    print('------')
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            print("成功連接到 Uptime Kuma")
            print(f"已登入為: {KUMA_URL}|{KUMA_USERNAME}")
    except Exception as e:
        print(f"無法連接到 Uptime Kuma: {str(e)}")
        await client.close()
        return

@client.tree.command(name="status", description="查看所有監控器狀態")
async def status(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            monitors = api.get_monitors()
            
            if not monitors:
                await interaction.followup.send("目前沒有任何監控器")
                return
            
            embed = discord.Embed(
                title="🔍 監控器狀態",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            for monitor in monitors:
                status_emoji = "🟢" if monitor.get('active') else "🔴"
                uptime = monitor.get('uptime', 0)
                
                value = f"URL: {monitor.get('url', 'N/A')}\n"
                
                # 改進顯示:如果是新監控器(uptime為0),顯示提示訊息
                if uptime == 0:
                    value += f"正常運行時間: {uptime}% ⏳ (數據收集中)"
                else:
                    value += f"正常運行時間: {uptime}%"
                
                embed.add_field(
                    name=f"{status_emoji} {monitor['name']}",
                    value=value,
                    inline=False
                )
            
            embed.set_footer(text="Uptime Kuma 監控系統")
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 錯誤：{str(e)}")

@client.tree.command(name="add_monitor", description="新增一個網站監控")
@app_commands.describe(
    name="監控器名稱",
    url="要監控的網址",
    interval="檢查間隔(秒)|未設定為60秒"
)
async def add_monitor(
    interaction: discord.Interaction,
    name: str,
    url: str,
    interval: Optional[int] = 60
):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            
            # 構建完整的監控器資料,包含必要的 conditions 欄位
            monitor_data = {
                "type": MonitorType.HTTP,
                "name": name,
                "url": url,
                "interval": interval,
                "conditions": "[]",  # 空條件列表
                "maxretries": 1,
                "retryInterval": 60,
                "resendInterval": 0,
                "maxredirects": 10,
                "accepted_statuscodes": ["200-299"],
                "method": "GET"
            }
            
            result = api._call('add', monitor_data)
            
            embed = discord.Embed(
                title="✅ 監控器已新增",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="名稱", value=name, inline=True)
            embed.add_field(name="URL", value=url, inline=True)
            embed.add_field(name="間隔", value=f"{interval}秒", inline=True)
            embed.add_field(name="ID", value=result.get('monitorID', 'N/A'), inline=False)
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 新增失敗：{str(e)}")

@client.tree.command(name="delete_monitor", description="刪除一個監控器")
@app_commands.describe(monitor_id="監控器 ID")
async def delete_monitor(interaction: discord.Interaction, monitor_id: int):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            api.delete_monitor(monitor_id)
            
            embed = discord.Embed(
                title="🗑️ 監控器已刪除",
                description=f"已成功刪除監控器 ID: {monitor_id}",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 刪除失敗：{str(e)}")

@client.tree.command(name="monitor_info", description="查看特定監控器的詳細資訊")
@app_commands.describe(monitor_id="監控器 ID")
async def monitor_info(interaction: discord.Interaction, monitor_id: int):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            monitor = api.get_monitor(monitor_id)
            
            embed = discord.Embed(
                title=f"📊 {monitor['name']}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="ID", value=monitor['id'], inline=True)
            embed.add_field(name="類型", value=monitor['type'], inline=True)
            embed.add_field(name="URL", value=monitor.get('url', 'N/A'), inline=False)
            embed.add_field(name="間隔", value=f"{monitor['interval']}秒", inline=True)
            embed.add_field(name="狀態", value="🟢 啟用" if monitor['active'] else "🔴 停用", inline=True)
            embed.add_field(name="正常運行時間", value=f"{monitor.get('uptime', 0)}%", inline=True)
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 查詢失敗：{str(e)}")

@client.tree.command(name="list_monitors", description="列出所有監控器(簡要資訊)")
async def list_monitors(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            monitors = api.get_monitors()
            
            if not monitors:
                await interaction.followup.send("目前沒有任何監控器")
                return
            
            message = "**📋 監控器列表**\n\n"
            for monitor in monitors:
                status = "🟢" if monitor.get('active') else "🔴"
                message += f"{status} **ID {monitor['id']}**: {monitor['name']}\n"
            
            await interaction.followup.send(message)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 錯誤：{str(e)}")

@client.tree.command(name="toggle_monitor", description="暫停或恢復一個監控器")
@app_commands.describe(
    monitor_id="監控器 ID",
    action="動作"
)
@app_commands.choices(action=[
    app_commands.Choice(name="暫停", value="pause"),
    app_commands.Choice(name="恢復", value="resume")
])
async def toggle_monitor(interaction: discord.Interaction, monitor_id: int, action: str):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            
            if action == "pause":
                api.pause_monitor(monitor_id)
                message = f"⏸️ 已暫停監控器 ID: {monitor_id}"
            else:
                api.resume_monitor(monitor_id)
                message = f"▶️ 已恢復監控器 ID: {monitor_id}"
            
            embed = discord.Embed(
                description=message,
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 操作失敗：{str(e)}")

@client.tree.command(name="help", description="顯示所有可用命令")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Uptime Kuma Bot 幫助",
        description="以下是所有可用的斜線命令：",
        color=discord.Color.purple()
    )
    
    commands_info = [
        ("/status", "查看所有監控器狀態"),
        ("/list_monitors", "列出所有監控器(簡要)"),
        ("/monitor_info", "查看特定監控器詳情"),
        ("/add_monitor", "新增網站監控"),
        ("/delete_monitor", "刪除監控器"),
        ("/toggle_monitor", "暫停/恢復監控器"),
        ("/help", "顯示此幫助訊息")
    ]
    
    for cmd, desc in commands_info:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text="使用 / 來查看所有命令")
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)