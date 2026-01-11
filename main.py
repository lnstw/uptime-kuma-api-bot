import discord
from discord import app_commands, ui
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
            embed.add_field(name="運作率(24h)", value=f"{monitor.get('uptime24', 0)}%", inline=True)
            
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

@client.tree.command(name="status", description="查看所有監控器統計 & 延遲信息")
async def status(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            monitors = api.get_monitors()
            
            if not monitors:
                await interaction.followup.send("目前沒有任何監控器")
                return
            total = len(monitors)
            enabled = 0
            paused = 0
            maintenance = 0
            offline = 0
            
            for m in monitors:
                if m.get('maintenance'):
                    maintenance += 1
                elif not m.get('active'):
                    paused += 1
                else:
                    try:
                        beats = api.get_monitor_beats(m['id'], 24)
                        if beats and len(beats) > 0:
                            status = beats[-1].get('status')
                            status_value = status.value if hasattr(status, 'value') else status
                            if status_value == 1:
                                enabled += 1
                            elif status_value == 0:
                                offline += 1
                    except:
                        offline += 1
            
            if offline > 0:
                status_color = discord.Color.red()
            elif paused > 0:
                status_color = discord.Color.light_grey()
            else:
                status_color = discord.Color.green()
            
            embed_status = discord.Embed(
                title="📊 監控統計",
                color=status_color,
                timestamp=discord.utils.utcnow()
            )
            
            embed_status.add_field(name="共計監控器", value=str(total), inline=True)
            embed_status.add_field(name="🟢 運行中", value=str(enabled), inline=True)
            embed_status.add_field(name="⏸️ 暫停中", value=str(paused), inline=True)
            embed_status.add_field(name="🔧 維護中", value=str(maintenance), inline=True)
            embed_status.add_field(name="⚠️ 運行中但離線", value=str(offline), inline=True)
            await interaction.followup.send(embed=embed_status)
            items_per_page = 1
            total_pages = (len(monitors) + items_per_page - 1) // items_per_page
            class MonitorPagination(ui.View):
                def __init__(self):
                    super().__init__(timeout=300)
                    self.current_page = 0
                    self.update_buttons()
                
                async def on_timeout(self):
                    self.previous_button.disabled = True
                    self.next_button.disabled = True
                
                def update_buttons(self):
                    self.previous_button.disabled = self.current_page == 0
                    self.next_button.disabled = self.current_page == total_pages - 1
                
                def get_embed(self):
                    start_idx = self.current_page * items_per_page
                    end_idx = start_idx + items_per_page
                    page_monitors = monitors[start_idx:end_idx]
                    
                    has_offline = False
                    has_maintenance = False
                    has_paused = False
                    
                    for m in page_monitors:
                        if m.get('maintenance'):
                            has_maintenance = True
                        elif not m.get('active'):
                            has_paused = True
                        else:
                            try:
                                with UptimeKumaApi(KUMA_URL) as api_temp:
                                    api_temp.login(KUMA_USERNAME, KUMA_PASSWORD)
                                    beats = api_temp.get_monitor_beats(m['id'], 24)
                                    if beats and len(beats) > 0:
                                        status = beats[-1].get('status')
                                        status_value = status.value if hasattr(status, 'value') else status
                                        if status_value == 0:
                                            has_offline = True
                            except:
                                has_offline = True
                    
                    if has_offline:
                        embed_color = discord.Color.red()
                    elif has_maintenance:
                        embed_color = discord.Color.dark_blue()
                    elif has_paused:
                        embed_color = discord.Color.light_grey()
                    else:
                        embed_color = discord.Color.green()
                        
                    embed_list = discord.Embed(
                        title="🔍 全部監控器 & 延遲",
                        color=embed_color,
                        timestamp=discord.utils.utcnow()
                    )
                    for monitor in page_monitors:
                        status_emoji = "❓"
                        if not monitor.get('active'):
                            status_emoji = "⏸️"
                        else:
                            try:
                                with UptimeKumaApi(KUMA_URL) as api_temp:
                                    api_temp.login(KUMA_USERNAME, KUMA_PASSWORD)
                                    beats = api_temp.get_monitor_beats(monitor['id'], 24)
                                    if beats and len(beats) > 0:
                                        status = beats[-1].get('status')
                                        status_value = status.value if hasattr(status, 'value') else status
                                        if status_value == 1:
                                            status_emoji = "🟢"
                                        elif status_value == 0:
                                            status_emoji = "🔴"
                            except Exception as e:
                                print(f"獲取狀態異常 (ID {monitor['id']}): {str(e)}")
                                status_emoji = "❓"
                        
                        maintenance_tag = " 🔧" if monitor.get('maintenance') else ""
                        try:
                            with UptimeKumaApi(KUMA_URL) as api_temp:
                                api_temp.login(KUMA_USERNAME, KUMA_PASSWORD)
                                beats = api_temp.get_monitor_beats(monitor['id'], 24)
                                if beats and len(beats) > 0:
                                    latest_ping = beats[-1].get('ping')
                                    ping_str = f"{latest_ping:.1f}ms" if latest_ping is not None else "N/A"
                                else:
                                    ping_str = "N/A"
                        except Exception as e:
                            print(f"獲取ping異常 (ID {monitor['id']}): {str(e)}")
                            ping_str = "N/A"
                        
                        value = f"**狀態**: {status_emoji}\n"
                        value += f"**延遲**: {ping_str}{maintenance_tag}\n"
                        if monitor.get('url'):
                            value += f"**URL**: {monitor.get('url')}\n"
                        if monitor.get('maintenance'):
                            value += "⚠️ 維護中"
                        embed_list.add_field(
                            name=f"ID {monitor['id']}: {monitor['name']}",
                            value=value.strip(),
                            inline=False
                        )
                    embed_list.set_footer(text=f"頁面 {self.current_page + 1}/{total_pages}")
                    return embed_list
                @ui.button(label="◀️ 上一頁", style=discord.ButtonStyle.primary)
                async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
                    if self.current_page > 0:
                        self.current_page -= 1
                        self.update_buttons()
                        embed = self.get_embed()
                        await interaction.response.edit_message(embed=embed, view=self)
                
                @ui.button(label="下一頁 ▶️", style=discord.ButtonStyle.primary)
                async def next_button(self, interaction: discord.Interaction, button: ui.Button):
                    if self.current_page < total_pages - 1:
                        self.current_page += 1
                        self.update_buttons()
                        embed = self.get_embed()
                        await interaction.response.edit_message(embed=embed, view=self)
            if total_pages > 0:
                view = MonitorPagination()
                embed = view.get_embed()
                await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        await interaction.followup.send(f"❌ 錯誤：{str(e)}")

@client.tree.command(name="list_maintenances", description="列出所有維護時段")
async def list_maintenances(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            maintenances = api.get_maintenances()
            
            if not maintenances:
                await interaction.followup.send("目前沒有任何維護時段")
                return
            
            embed = discord.Embed(
                title="🔧 維護時段列表",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            
            for maintenance in maintenances:
                status = "🟢 啟用" if maintenance.get('active') else "🔴 停用"
                strategy = maintenance.get('strategy', 'N/A')
                
                value = f"**狀態**: {status}\n"
                value += f"**策略**: {strategy}\n"
                
                if maintenance.get('description'):
                    value += f"**描述**: {maintenance['description']}\n"
                
                embed.add_field(
                    name=f"ID {maintenance['id']}: {maintenance['title']}",
                    value=value.strip(),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 錯誤：{str(e)}")

@client.tree.command(name="create_maintenance", description="建立新的維護時段")
@app_commands.describe(
    title="維護時段名稱",
    description="維護描述",
    strategy="維護策略"
)
@app_commands.choices(strategy=[
    app_commands.Choice(name="單次", value="single"),
    app_commands.Choice(name="每日重複", value="recurring-interval"),
    app_commands.Choice(name="每週重複", value="recurring-weekday"),
    app_commands.Choice(name="每月重複", value="recurring-day-of-month")
])
async def create_maintenance(
    interaction: discord.Interaction,
    title: str,
    strategy: str,
    description: Optional[str] = None
):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            
            result = api.add_maintenance(
                title=title,
                description=description or "",
                strategy=strategy,
                active=True,
                intervalDay=1,
                dateRange=[]
            )
            
            embed = discord.Embed(
                title="✅ 維護時段已建立",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="名稱", value=title, inline=True)
            embed.add_field(name="策略", value=strategy, inline=True)
            if description:
                embed.add_field(name="描述", value=description, inline=False)
            embed.add_field(name="ID", value=result.get('maintenanceID', 'N/A'), inline=False)
            
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 建立失敗：{str(e)}")

@client.tree.command(name="delete_maintenance", description="刪除維護時段")
@app_commands.describe(maintenance_id="維護時段 ID")
async def delete_maintenance(interaction: discord.Interaction, maintenance_id: int):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            api.delete_maintenance(maintenance_id)
            
            embed = discord.Embed(
                title="🗑️ 維護時段已刪除",
                description=f"已成功刪除維護時段 ID: {maintenance_id}",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 刪除失敗：{str(e)}")

@client.tree.command(name="toggle_maintenance", description="啟用或停用維護時段")
@app_commands.describe(
    maintenance_id="維護時段 ID",
    action="動作"
)
@app_commands.choices(action=[
    app_commands.Choice(name="啟用", value="enable"),
    app_commands.Choice(name="停用", value="disable")
])
async def toggle_maintenance(interaction: discord.Interaction, maintenance_id: int, action: str):
    await interaction.response.defer()
    
    try:
        with UptimeKumaApi(KUMA_URL) as api:
            api.login(KUMA_USERNAME, KUMA_PASSWORD)
            
            maintenance = api.get_maintenance(maintenance_id)
            
            maintenance['active'] = (action == "enable")
            api.edit_maintenance(maintenance_id, **maintenance)
            
            status_text = "啟用" if action == "enable" else "停用"
            emoji = "✅" if action == "enable" else "⏸️"
            
            embed = discord.Embed(
                description=f"{emoji} 已{status_text}維護時段 ID: {maintenance_id}",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        await interaction.followup.send(f"❌ 操作失敗：{str(e)}")

@client.tree.command(name="help", description="顯示所有可用命令")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(
        title="🤖 Uptime Kuma Bot 幫助",
        description="以下是所有可用的斜線命令：",
        color=discord.Color.purple()
    )
    
    commands = await client.tree.fetch_commands()
    cmd_dict = {cmd.name: cmd.id for cmd in commands}

    commands_info = {
        "status": "查看統計 & 全部監控器延遲",
        "list_monitors": "列出所有監控器(簡要)",
        "monitor_info": "查看特定監控器詳情",
        "add_monitor": "新增網站監控",
        "delete_monitor": "刪除監控器",
        "toggle_monitor": "暫停/恢復監控器",
        "list_maintenances": "列出所有維護時段",
        "create_maintenance": "建立新的維護時段",
        "delete_maintenance": "刪除維護時段",
        "toggle_maintenance": "啟用/停用維護時段",
        "help": "顯示此幫助訊息"
    }
    for cmd_name, desc in commands_info.items():
        cmd_id = cmd_dict.get(cmd_name, "00")
        embed.add_field(name=f"</{cmd_name}:{cmd_id}>", value=desc, inline=False)
    embed.set_footer(text="點擊命令即可執行")
    await interaction.followup.send(embed=embed)

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)