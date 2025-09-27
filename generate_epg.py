import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz

# ============= CONFIGURAÇÕES =============
LOCATIONS = [
    # cada entrada pode ter (location, channelIds)
    ("SAO PAULO,SAO PAULO", ""),
    ("RECIFE,PERNAMBUCO", "128,463,378,403,418"),
    ("CARUARU,PERNAMBUCO", "191"),
    ("JOAO PESSOA,PARAIBA", "196"),
    ("CAMPINA GRANDE,PARAIBA", "190"),
    ("RIBEIRAO PRETO,SAO PAULO", "221,459"),
    ("FORTALEZA,CEARA", "203,356,359"),
    # exemplo: ("SAO PAULO,SAO PAULO", "101,102,103")  # só alguns canais
]

TIMEZONE = "America/Recife"
OUTPUT_FILE = "epg.xml"
GENERATOR_NAME = "Neto Souza"
GENERATOR_URL = "http://netosouza.net"
# =========================================


def unix_to_xmltv(ts, tz):
    """Converte unix timestamp -> formato XMLTV (YYYYMMDDHHMM ±ZZZZ)"""
    dt = datetime.fromtimestamp(ts, tz)
    return dt.strftime("%Y%m%d%H%M %z")


def fetch_json(location, channel_ids, start_ts, end_ts):
    url = (
        "https://www.clarotvmais.com.br/avsclient/1.2/epg/livechannels"
        f"?types=&channelIds={channel_ids}&startTime={start_ts}&endTime={end_ts}"
        f"&location={location}&channel=ANDROIDTV"
    )
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def build_xml(channels_data):
    tv = ET.Element("tv", {
        "generator-info-name": GENERATOR_NAME,
        "generator-info-url": GENERATOR_URL
    })

    # canais primeiro
    for channel in channels_data:
        name = channel.get("name")
        channel_el = ET.SubElement(tv, "channel", id=name)
        display_name = ET.SubElement(channel_el, "display-name", lang="pt")
        display_name.text = name

    # programas depois
    for channel in channels_data:
        name = channel.get("name")
        schedules = channel.get("schedules", [])

        for prog in schedules:
            title = prog.get("title")
            epname = prog.get("episodeName")
            if epname:
                title = f"{title} - {epname}"

            desc = prog.get("description", "")

            start = unix_to_xmltv(prog.get("startTime"), pytz.timezone(TIMEZONE))
            stop = unix_to_xmltv(prog.get("endTime"), pytz.timezone(TIMEZONE))

            prog_el = ET.SubElement(tv, "programme", {
                "start": start,
                "stop": stop,
                "channel": name
            })

            title_el = ET.SubElement(prog_el, "title", lang="pt")
            title_el.text = title

            if desc:
                desc_el = ET.SubElement(prog_el, "desc", lang="pt")
                desc_el.text = desc

    return tv


def main():
    tz = pytz.timezone(TIMEZONE)

    # sempre gera EPG do dia atual 00h00 até +3 dias
    now = datetime.now(tz)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    start_ts = int(today_midnight.timestamp())
    end_ts = int((today_midnight + timedelta(days=3)).timestamp())  # até 00h do 4º dia

    all_channels = []

    for location, channel_ids in LOCATIONS:
        data = fetch_json(location, channel_ids, start_ts, end_ts)
        live_channels = data.get("response", {}).get("liveChannels", [])
        all_channels.extend(live_channels)

    tv = build_xml(all_channels)

    tree = ET.ElementTree(tv)
    tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
