import discord
import os
import requests
import datetime
import asyncio
from zoneinfo import ZoneInfo

from keep_alive import keep_alive

# --- Konfiguracja Bota ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1392322488519757834  # ID kanału do wysyłania

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last_message_id = None  # Zapamiętujemy ID wiadomości, żeby edytować a nie spamować

keep_alive()

# --- Funkcja Pobierania Danych ---
def fetch_data():
    """
    Pobiera dane o organizacjach i przejęciach z API.
    Obsługuje błędy pobierania.
    """
    orgs_url = "https://api.nxtrp.pl/api/orgs"
    captures_url = "https://api.nxtrp.pl/api/captures"
    orgs = []
    captures = []
    try:
        r_orgs = requests.get(orgs_url)
        r_captures = requests.get(captures_url)

        if r_orgs.status_code == 200:
            orgs = r_orgs.json()
        else:
            print(f"Błąd pobierania organizacji: Status {r_orgs.status_code}")

        if r_captures.status_code == 200:
            captures = r_captures.json()
        else:
            print(f"Błąd pobierania przejęć: Status {r_captures.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia z API: {e}")
    except ValueError as e:
        print(f"Błąd parsowania JSON: {e}")
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd podczas pobierania danych: {e}")
    return orgs, captures

# --- Funkcja Tworzenia Estetycznego Embedu ---
def create_embed(orgs, captures):
    """
    Tworzy ładnie sformatowany embed Discorda z topką organizacji
    i ostatnimi przejęciami stref.
    """
    embed = discord.Embed(
        title="🏆 Ranking Organizacji i Ostatnie Przejęcia Stref 🌍",
        description="", # Usunięto opis zgodnie z prośbą
        color=0x3498db
    )

    # Lewa kolumna - Topka organizacji
    top_text = ""
    if orgs:
        sorted_orgs = sorted(orgs, key=lambda x: x.get('points', 0), reverse=True)
        for i, org in enumerate(sorted_orgs[:10]): # Ogranicz do top 10
            emoji = ""
            if i == 0: emoji = "🥇 "
            elif i == 1: emoji = "🥈 "
            elif i == 2: emoji = "🥉 "
            elif i < 5: emoji = "🏅 "
            else: emoji = f"#{i+1}. " # Numeracja dla kolejnych miejsc

            top_text += f"{emoji}**{org.get('name', 'N/A')}**: `{org.get('points', 0)} pkt`\n"
    else:
        top_text = "Niestety, brak danych o organizacjach."

    embed.add_field(name="📈 Top Organizacje", value=top_text, inline=True)

    # Prawa kolumna - 3 ostatnie przejęcia
    captures_text = ""
    last_three = captures[:3] if captures else []
    if last_three:
        for i, cap in enumerate(last_three):
            status_emoji = "✅" if cap.get("success", 0) == 1 else "❌"
            # Dodanie nagłówka dla każdego przejęcia i użycie code blocków dla czytelności
            captures_text += (
                f"**#{i+1} Przejęcie:**\n"
                f"```yaml\n"
                f"Czas: {cap.get('at', 'N/A')}\n"
                f"Przez: {cap.get('by', 'N/A')}\n"
                f"Strefa: {cap.get('zone', 'N/A')}\n"
                f"Status: {status_emoji}\n"
                f"```\n"
            )
    else:
        captures_text = "Brak zarejestrowanych przejęć."

    embed.add_field(name="⏳ Ostatnie Przejęcia Stref", value=captures_text, inline=True)

    # Ustawienie stopki z ikoną i dynamicznym czasem
     # Importuj ZoneInfo na początku pliku, jeśli go tam jeszcze nie ma

    poland_tz = ZoneInfo("Europe/Warsaw")
    current_time = datetime.datetime.now(poland_tz).strftime('%Y-%m-%d       %H:%M:%S')

    embed.set_footer(
        text=f"Ostatnia aktualizacja: {current_time}",
        icon_url="https://cdn-icons-png.flaticon.com/512/1040/1040220.png"
    )
    return embed

# --- Funkcja Aktualizująca Wiadomość ---
async def update_message(channel):
    """
    Pobiera dane, tworzy embed i wysyła/edytuje wiadomość na kanale.
    """
    global last_message_id
    orgs, captures = await asyncio.to_thread(fetch_data)
    embed = create_embed(orgs, captures)

    if last_message_id is None:
        msg = await channel.send(embed=embed)
        last_message_id = msg.id
    else:
        try:
            msg = await channel.fetch_message(last_message_id)
            await msg.edit(embed=embed)
        except discord.NotFound:
            print(f"Wiadomość o ID {last_message_id} nie znaleziona. Wysyłam nową.")
            msg = await channel.send(embed=embed)
            last_message_id = msg.id
        except discord.Forbidden:
            print("Brak uprawnień do edycji wiadomości. Sprawdź uprawnienia bota.")
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas edycji wiadomości: {e}")


# --- Zadanie w Tle ---
async def background_task():
    """
    Pętla odpowiedzialna za regularne odświeżanie wiadomości.
    """
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Błąd: Nie znaleziono kanału o ID {CHANNEL_ID}. Sprawdź, czy ID jest poprawne i bot ma dostęp do kanału.")
        return

    while not client.is_closed():
        await update_message(channel)
        await asyncio.sleep(60)

# --- Obsługa Zdarzeń Bota ---
@client.event
async def on_ready():
    """
    Wywoływane, gdy bot jest gotowy i zalogowany.
    """
    print(f"Zalogowano jako {client.user}!")
    print(f"Bot jest aktywny na {len(client.guilds)} serwerach.")
    client.loop.create_task(background_task())

# --- Uruchomienie Bota ---
client.run(TOKEN)