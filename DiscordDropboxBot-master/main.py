import os
import discord
import dropbox
import gspread
import requests
import json
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from dropbox.exceptions import AuthError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from refresh_token import get_dropbox_access_token

# Input all discord API requirements below
TOKEN = "MTM1MzcwNjIxMDE1MDMyMjMyNw.GkvyWb.K9mg0bMygjkq4MXKuPrC28h4T9jAEoF6NcmZT4"
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
load_dotenv()
bot = commands.Bot(command_prefix="/", intents=intents)

# Dropbox token (sẽ được làm mới tự động)
DROPBOX_ACCESS_TOKEN = get_dropbox_access_token()

# Google Sheets API setup
GOOGLE_SHEETS_CREDENTIALS_FILE = "credentials.json"  # File JSON chứa thông tin xác thực
GOOGLE_SHEET_ID = "1unyoY6b06Z3IvN5NTUdF6xhAXSbZEQaNOhQ034pQtqE"  # Thay bằng ID Google Sheet của bạn

# Google Drive API setup
GOOGLE_DRIVE_CREDENTIALS_FILE = "bot-discord-454817-6d8f873af109.json"  # File JSON chứa thông tin xác thực
GOOGLE_DRIVE_FOLDER_ID = "1H4pZl5mrbpsiR3SI80_-QzkPK4ANEa13"  # Thay bằng ID thư mục Google Drive của bạn

# File lưu role setup
ROLE_DATA_FILE = "roles.json"

# Role được phép tải file từ Dropbox
allowed_role_name = None

# Thông tin donate
KOFI_API_KEY = "KF_API_04f29fec-d1ca-4e64-82f6-55a326c1f590"  # Thay bằng API Key của bạn từ Ko-fi
KOFI_GOAL_AMOUNT = 65  # Mục tiêu donate (ví dụ: 100 USD)
KOFI_ZIP_FILE_PATH = "C:\\Users\\borok\\Downloads\\DiscordDropboxBot-master\\Black Myth Wukong Clean File.zip"  # Đường dẫn tới file .zip sẽ gửi khi đạt mục tiêu

# ============================
# Utility Functions
# ============================

def load_roles():
    """
    Tải dữ liệu role từ file JSON.
    """
    if os.path.exists(ROLE_DATA_FILE):
        with open(ROLE_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_roles(roles):
    """
    Lưu dữ liệu role vào file JSON.
    """
    with open(ROLE_DATA_FILE, "w") as f:
        json.dump(roles, f, indent=4)

def dropbox_connect():
    """
    Tries to establish a connection to Dropbox. Refreshes token if needed.
    """
    global DROPBOX_ACCESS_TOKEN
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        # Test the connection
        dbx.users_get_current_account()
        return dbx
    except AuthError:
        print("Dropbox token expired or invalid. Attempting to refresh token...")
        DROPBOX_ACCESS_TOKEN = get_dropbox_access_token()  # Làm mới token
        if not DROPBOX_ACCESS_TOKEN:
            print("❌ Failed to refresh Dropbox Access Token.")
            return None
        try:
            dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
            dbx.users_get_current_account()
            return dbx
        except AuthError:
            print("❌ Failed to connect to Dropbox even after refreshing token.")
            return None

def dropbox_download(appid):
    """
    Downloads a file from Dropbox based on the exact appid.
    """
    dbx = dropbox_connect()
    if not dbx:
        return None, None

    # Get the list of files in Dropbox
    try:
        for entry in dbx.files_list_folder('', recursive=True).entries:
            if isinstance(entry, dropbox.files.FileMetadata) and entry.name == f"{appid}.file":
                # Download the matching file
                file_name = entry.name  # Lấy tên file gốc
                local_path = os.path.join(os.getcwd(), file_name)
                with open(local_path, "wb") as f:
                    metadata, res = dbx.files_download(entry.path_display)
                    f.write(res.content)
                return local_path, file_name
    except Exception as e:
        print(f"Error downloading file from Dropbox: {str(e)}")
        return None, None

    return None, None

def google_drive_connect():
    """
    Kết nối tới Google Drive API.
    """
    try:
        credentials = Credentials.from_service_account_file(GOOGLE_DRIVE_CREDENTIALS_FILE)
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"❌ Error connecting to Google Drive: {str(e)}")
        return None

def google_drive_download(file_name):
    """
    Tải file từ Google Drive dựa trên tên file.
    """
    service = google_drive_connect()
    if not service:
        return None, None

    try:
        # Thay đổi phần mở rộng file từ .file thành .zip
        if not file_name.endswith(".zip"):
            file_name = file_name.replace(".file", ".zip")

        # Tìm file trong thư mục Google Drive
        query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and name='{file_name}' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])

        if not files:
            print(f"❌ File '{file_name}' not found in Google Drive.")
            return None, None

        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        file_path = f"./{file_name}"  # Lưu file vào thư mục hiện tại

        with open(file_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"✅ Downloading {file_name}: {int(status.progress() * 100)}%")

        return file_path, file_name
    except Exception as e:
        print(f"❌ Error downloading file from Google Drive: {str(e)}")
        return None, None

def get_google_sheet_data():
    """
    Fetches data from Google Sheets.
    """
    try:
        # Xác thực và kết nối với Google Sheets
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        credentials = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(credentials)

        # Mở Google Sheet bằng ID
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1  # Mở sheet đầu tiên
        data = sheet.get_all_records()  # Lấy tất cả dữ liệu dưới dạng danh sách các dict
        print("✅ Fetched data from Google Sheets:", data)  # In dữ liệu để kiểm tra
        return data
    except Exception as e:
        print(f"Error fetching data from Google Sheets: {str(e)}")
        return None

# ============================
# Discord Bot Commands
# ============================

@bot.tree.command(name="send", description="Send a file from Dropbox or Google Drive or a link based on appid")
async def send(interaction: discord.Interaction, appid: str):
    """
    Sends game information from Steam API as a public embed, then sends a file or link privately to the user.
    """
    global allowed_role_name

    # Trì hoãn phản hồi ngay từ đầu
    await interaction.response.defer()

    # Lấy thông tin game từ Steam API
    steam_api_key = "your_steam_api_key"  # Thay bằng Steam API Key của bạn
    steam_url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    try:
        response = requests.get(steam_url)
        if response.status_code == 200:
            game_data = response.json().get(appid, {}).get("data", {})
            if game_data:
                # Xử lý tên game: Viết hoa chữ cái đầu của mỗi từ
                game_name = game_data.get("name", "Unknown").title()

                # Xử lý mô tả: Viết hoa chữ cái đầu sau dấu "."
                game_description = game_data.get("short_description", "No description available.")
                game_description = ". ".join(sentence.strip().capitalize() for sentence in game_description.split(". "))

                # Xử lý ngày phát hành: Viết hoa chữ cái đầu của tháng
                game_release_date = game_data.get("release_date", {}).get("date", "Unknown release date")
                game_release_date = game_release_date.title()

                # Lấy ảnh game
                game_image = game_data.get("header_image", None)

                # Tạo embed để gửi thông tin game
                embed = discord.Embed(
                    title="**Manifest**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="**Name**", value=game_name, inline=False)
                embed.add_field(name="**Description**", value=game_description, inline=False)
                embed.add_field(name="**Release Date**", value=game_release_date, inline=False)
                embed.add_field(name="**Steam Link**", value=f"https://store.steampowered.com/app/{appid}", inline=False)
                embed.set_footer(text="Game information fetched from Steam")

                # Thêm ảnh game nếu có
                if game_image:
                    embed.set_image(url=game_image)

                # Gửi embed công khai
                await interaction.followup.send(embed=embed)  # Công khai embed
            else:
                await interaction.followup.send(
                    f"Game not available or invalid App ID.",
                    ephemeral=True
                )
                return
        else:
            await interaction.followup.send(
                f"❌ Failed to fetch game information from Steam API. Status code: {response.status_code}",
                ephemeral=True
            )
            return
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error fetching game information: {str(e)}",
            ephemeral=True
        )
        return

    # Lấy dữ liệu từ Google Sheets
    data = get_google_sheet_data()
    if not data:
        await interaction.followup.send("Failed to fetch data from Google Sheets.", ephemeral=True)
        return

    # Tìm link tương ứng với appid
    link = next((row["Link"] for row in data if str(row["AppID"]) == appid), None)

    # Kiểm tra role đã setup
    roles = load_roles()
    allowed_role_name = roles.get(str(interaction.guild.id))

    if allowed_role_name:
        user_roles = [role.name for role in interaction.user.roles]
        if allowed_role_name in user_roles:
            # Nếu người dùng có role, kiểm tra Dropbox
            file_path, file_name = dropbox_download(appid)
            if not file_path:
                # Nếu file không tồn tại trong Dropbox, kiểm tra Google Drive
                file_name = f"{appid}.file"  # Định dạng tên file
                file_path, file_name = google_drive_download(file_name)
                if not file_path:
                    # Nếu file không tồn tại trong Google Drive, thông báo lỗi
                    await interaction.followup.send(f"No file found with appid: {appid} in Dropbox or Google Drive.", ephemeral=True)
                    return

            # Gửi file từ Dropbox hoặc Google Drive (riêng tư)
            with open(file_path, 'rb') as f:
                file_to_send = discord.File(f, filename=file_name)
                await interaction.followup.send(file=file_to_send, ephemeral=True)
            return

    # Nếu chưa setup role hoặc người dùng không có role, gửi link từ Google Sheets (riêng tư)
    if not link:
        await interaction.followup.send(f"No link found for appid: {appid}", ephemeral=True)
        return

    await interaction.followup.send(f"Here is the link for appid {appid}: {link}", ephemeral=True)

@bot.tree.command(name="setup_role", description="Setup the role allowed to download files")
async def setup_role(interaction: discord.Interaction, role_name: str):
    """
    Allows the bot owner to set up the role allowed to download files.
    """
    bot_owner_id = 1138043843489570836  # Thay bằng ID Discord của bạn
    if interaction.user.id != bot_owner_id:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Lấy danh sách các role trong server
    guild_roles = [role.name for role in interaction.guild.roles]

    # Kiểm tra nếu role không tồn tại trong server
    if role_name not in guild_roles:
        await interaction.response.send_message(f"❌ Role '{role_name}' không tồn tại trong server.", ephemeral=True)
        return

    # Kiểm tra nếu role đã được setup trước đó
    roles = load_roles()
    current_role = roles.get(str(interaction.guild.id))
    if current_role == role_name:
        await interaction.response.send_message(f"✅ Role '{role_name}' đã được setup trước đó.", ephemeral=True)
        return

    # Lưu role vào file JSON
    roles[str(interaction.guild.id)] = role_name
    save_roles(roles)

    await interaction.response.send_message(f"✅ Role '{role_name}' đã được setup thành công.", ephemeral=True)

@setup_role.autocomplete("role_name")
async def role_name_autocomplete(interaction: discord.Interaction, current: str):
    """
    Gợi ý danh sách role trong server dựa trên input của người dùng.
    """
    roles = [role.name for role in interaction.guild.roles if current.lower() in role.name.lower()]
    return [app_commands.Choice(name=role, value=role) for role in roles[:25]]  # Giới hạn 25 role

@bot.tree.command(name="remove_role", description="Remove the role allowed to download files")
async def remove_role(interaction: discord.Interaction):
    """
    Allows the bot owner to remove the role allowed to download files.
    """
    bot_owner_id = 1138043843489570836
    if interaction.user.id != bot_owner_id:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    roles = load_roles()
    if str(interaction.guild.id) not in roles:
        await interaction.response.send_message("No role is currently set up for this server.", ephemeral=True)
        return

    removed_role = roles.pop(str(interaction.guild.id))
    save_roles(roles)

    await interaction.response.send_message(f"Role '{removed_role}' has been removed.", ephemeral=True)

@bot.event
async def on_ready():
    """
    Event triggered when the bot is ready.
    """
    print(f"Bot is ready. Logged in as {bot.user}.")
    await bot.tree.sync()

# Run the bot
bot.run(TOKEN)