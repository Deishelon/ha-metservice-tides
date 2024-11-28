import json
import logging
from dataclasses import dataclass
from datetime import datetime

import aiohttp
import requests

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class TideInfo:
    height: float
    time: str
    timeISO: str
    timestamp: float
    type: str


@dataclass(frozen=True)
class TidesData:
    maxHeight: float
    minHeight: float
    tides: list[TideInfo]


class MetserviceTideApi:
    """This class provides an abstraction for reading data from a Tesla Wall Connector"""

    def __init__(self, session: aiohttp.ClientSession = aiohttp.ClientSession()):
        self.session = session

    async def async_request(self) -> TidesData:
        url = 'https://www.metservice.com/publicData/webdata/favourites/tidal/east-auckland/weiti-river-entrance'
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await self.decode_response(response)

    async def decode_response(self, response: aiohttp.ClientResponse) -> TidesData:
        """Decode response applying potentially needed workarounds."""
        raw_body = await response.text()
        json_data = json.loads(raw_body)

        tides = [
            TideInfo(
                height=float(entry["height"]),
                time=entry["time"],
                timeISO=entry["timeISO"],
                timestamp=datetime.fromisoformat(entry["timeISO"]).timestamp(),
                type=entry["type"]
            ) for entry in json_data["value"]["tides"]["tideData"]]

        ret = TidesData(
            maxHeight=json_data["value"]["tides"]["maxHeight"],
            minHeight=json_data["value"]["tides"]["minHeight"],
            tides=tides,
        )
        _LOGGER.warning(f"TidesData: {ret}")
        return ret


def fetch_metservice_tide(station_id: str) -> TidesData | None:
    url = 'https://www.metservice.com/publicData/webdata/favourites/tidal/east-auckland/weiti-river-entrance'
    headers = {
        # 'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'Referer': 'https://www.metservice.com/marine/regions/east-auckland/tides/locations/weiti-river-entrance',
        # 'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        # 'sec-ch-ua-platform': '"Windows"',
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        json_data = json.loads(response.text)
        return TidesData(
            maxHeight=json_data["value"]["tides"]["maxHeight"],
            minHeight=json_data["value"]["tides"]["minHeight"],
            tides=[],
        )
    else:
        return None
