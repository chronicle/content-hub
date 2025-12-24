from __future__ import annotations

from collections.abc import Iterable

USER_TYPES: dict[str, str] = {"Basic": "1", "Licensed": "2", "On-prem": "3"}


class UserAction:
    DELETE = "delete"


class Meeting:
    INSTANT = "Instant"
    SCHEDULED = "Scheduled"


SUPPORTED_MEETING_TYPES: dict[str, str] = {Meeting.INSTANT: "1", Meeting.SCHEDULED: "2"}

AUTO_RECORDING_TYPES: Iterable[str] = (
    "local",  # Recording on local
    "cloud",  # Recording on cloud
    "none",  # Disabled
)

RECORDINGS_TRASH_TYPE: Iterable[str] = (
    "meeting_recordings",  # for list all meeting recordings from the trash
    "recording_file",  # for list all individual recording files from the trash
)

API_ROOT: str = "https://api.zoom.us/v2"
OAUTH_TOKEN_URL: str = "https://zoom.us/oauth/token"

HEADERS: dict[str, str] = {
    "Authorization": "Bearer jwt_token",
    "content-type": "application/json",
}

TIMEZONES: Iterable[str] = (
    "Pacific/Midway",
    "Pacific/Pago_Pago",
    "Pacific/Honolulu",
    "America/Anchorage",
    "America/Vancouver",
    "America/Los_Angeles",
    "America/Tijuana",
    "America/Edmonton",
    "America/Denver",
    "America/Phoenix",
    "America/Mazatlan",
    "America/Winnipeg",
    "America/Regina",
    "America/Chicago",
    "America/Mexico_City",
    "America/Guatemala",
    "America/El_Salvador",
    "America/Managua",
    "America/Costa_Rica",
    "America/Montreal",
    "America/New_York",
    "America/Indianapolis",
    "America/Panama",
    "America/Bogota",
    "America/Lima",
    "America/Halifax",
    "America/Puerto_Rico",
    "America/Caracas",
    "America/Santiago",
    "America/St_Johns",
    "America/Montevideo",
    "America/Araguaina",
    "America/Argentina/Buenos_Aires",
    "America/Godthab",
    "America/Sao_Paulo",
    "Atlantic/Azores",
    "Canada/Atlantic",
    "Atlantic/Cape_Verde",
    "UTC",
    "Etc/Greenwich",
    "Europe/Belgrade",
    "CET",
    "Atlantic/Reykjavik",
    "Europe/Dublin",
    "Europe/London",
    "Europe/Lisbon",
    "Africa/Casablanca",
    "Africa/Nouakchott",
    "Europe/Oslo",
    "Europe/Copenhagen",
    "Europe/Brussels",
    "Europe/Berlin",
    "Europe/Helsinki",
    "Europe/Amsterdam",
    "Europe/Rome",
    "Europe/Stockholm",
    "Europe/Vienna",
    "Europe/Luxembourg",
    "Europe/Paris",
    "Europe/Zurich",
    "Europe/Madrid",
    "Africa/Bangui",
    "Africa/Algiers",
    "Africa/Tunis",
    "Africa/Harare",
    "Africa/Nairobi",
    "Europe/Warsaw",
    "Europe/Prague",
    "Europe/Budapest",
    "Europe/Sofia",
    "Europe/Istanbul",
    "Europe/Athens",
    "Europe/Bucharest",
    "Asia/Nicosia",
    "Asia/Beirut",
    "Asia/Damascus",
    "Asia/Jerusalem",
    "Asia/Amman",
    "Africa/Tripoli",
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Europe/Moscow",
    "Asia/Baghdad",
    "Asia/Kuwait",
    "Asia/Riyadh",
    "Asia/Bahrain",
    "Asia/Qatar",
    "Asia/Aden",
    "Asia/Tehran",
    "Africa/Khartoum",
    "Africa/Djibouti",
    "Africa/Mogadishu",
    "Asia/Dubai",
    "Asia/Muscat",
    "Asia/Baku",
    "Asia/Kabul",
    "Asia/Yekaterinburg",
    "Asia/Tashkent",
    "Asia/Calcutta",
    "Asia/Kathmandu",
    "Asia/Novosibirsk",
    "Asia/Almaty",
    "Asia/Dacca",
    "Asia/Krasnoyarsk",
    "Asia/Dhaka",
    "Asia/Bangkok",
    "Asia/Saigon",
    "Asia/Jakarta",
    "Asia/Irkutsk",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Taipei",
    "Asia/Kuala_Lumpur",
    "Asia/Singapore",
    "Australia/Perth",
    "Asia/Yakutsk",
    "Asia/Seoul",
    "Asia/Tokyo",
    "Australia/Darwin",
    "Australia/Adelaide",
    "Asia/Vladivostok",
    "Pacific/Port_Moresby",
    "Australia/Brisbane",
    "Australia/Sydney",
    "Australia/Hobart",
    "Asia/Magadan",
    "SST",
    "Pacific/Noumea",
    "Asia/Kamchatka",
    "Pacific/Fiji",
    "Pacific/Auckland",
    "Asia/Kolkata",
    "Europe/Kiev",
    "America/Tegucigalpa",
    "Pacific/Apia",
)
