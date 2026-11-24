from __future__ import annotations
INTEGRATION_NAME = "ExabeamAdvancedAnalytics"
INTEGRATION_DISPLAY_NAME = "Exabeam Advanced Analytics"

# Action Script names
PING_SCRIPT_NAME = "Ping"
LIST_WATCHLISTS_SCRIPT_NAME = "List Watchlists"
ADD_ENTITY_COMMENT_SCRIPT_NAME = "Add Comments To Entity"
LIST_WATCHLIST_ITEMS_SCRIPT_NAME = "List Watchlist Items"
ADD_ENTITY_TO_WATCHLIST_SCRIPT_NAME = "Add Entity To Watchlist"
CREATE_WATCHLIST_SCRIPT_NAME = "Create Watchlist"
DELETE_WATCHLIST_SCRIPT_NAME = "Delete Watchlist"
REMOVE_ENTITY_FROM_WATCHLIST_SCRIPT_NAME = "Remove Entity From Watchlist"
ENRICH_ENTITIES_SCRIPT_NAME = "Enrich Entities"

DEFAULT_MAX_WATCHLISTS_TO_RETURN = 100
MIN_WATCHLISTS_TO_RETURN = 1
DEFAULT_MAX_WATCHLIST_ITEMS_TO_RETURN = 100
MIN_WATCHLIST_ITEMS_TO_RETURN = 1
DEFAULT_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS = 1
MIN_WATCHLIST_ITEMS_MAX_DAYS_BACKWARDS_TO_RETURN = 0

MAX_WATCHLIST_ITEMS = 10000

ENTITY_USER_TYPE = "user"
ENTITY_ASSET_TYPE = "asset"

WATCHLIST_USERS_CATEGORIES = ["Users", "UserLabels"]
WATCHLIST_USERS_TYPE = "Users"
WATCHLIST_ASSETS_TYPE = "Assets"

DEFAULT_WATCHLIST_CATEGORY = "User"
DEFAULT_WATCHLIST_ACCESS_CONTROL = "Private"

WATCHLIST_ACCESS_CONTROL_MAPPINGS = {"Public": "public", "Private": "private"}

WATCHLIST_CATEGORY_MAPPINGS = {"User": "Users", "Asset": "Assets"}

DEFAULT_WATCHLIST_LIST_ITEMS_MAX_DAYS_BACKWARDS = 300
ENRICHMENT_PREFIX = "EXBAA"

DEFAULT_EVENT_TIME_FRAME_HOURS = 24
DEFAULT_MAX_COMMENTS_TO_RETURN = 10
LOWEST_EVENT_RISK_SCORE = 0
DEFAULT_MAX_EVENTS_TO_FETCH = 1000

EVENT_TIME_FRAME_BUFFER_HOURS = 24 * 31  # 1 month in hours

HTML_LINK = '<a target="_blank" href="{link}">{link}</a>'

RED = "#ff0000"
NO_COLOR = "none"

NOT_ASSIGNED = "N/A"

USER_INSIGHT_HTML = """
{risk}
<h3><strong>General Information</strong></h3>
<div style="display: flex; height:150px; flex-direction: row;">
    <table style="border-collapse:separate;">
        <tbody>
            <tr>
                <td width="30%"><strong>Notable</strong></td>
                <td width="50%">{is_notable}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Executive</strong></td>
                <td width="50%">{is_executive}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Last Activity Type</strong></td>
                <td width="50%">{last_activity_type}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Last Activity Time</strong></td>
                <td width="50%">{last_activity_time}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Last Session</strong></td>
                <td width="50%">{last_session_id}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Labels</strong></td>
                <td width="50%">{labels}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Source Link</strong></td>
                <td width="50%"> <a href="{report_link}" target="_blank">{report_link}</a></p></td>
            </tr>
        </tbody>
    </table>
</div>
<br />
{comments_table}
{events_table}
"""

RISK_SCORE_HTML = """
<div style="display: flex; flex-direction: row; justify-content: space-evenly;">
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center;">
<h2 style="text-transform: uppercase;">Risk Score:</h2>
</div>
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center;">
<h2 style="text-transform: uppercase; color: {risk_color};">{risk_score}</h2>
</div>
</div>
"""

BOLD_TITLE = """<h3><strong>{text}</strong></h3>"""
BOLD_TEXT = """<p><strong>{text}</strong></p>"""
TEXT = """<p>{text}</p>"""

NO_COMMENT_FOUND_HTML = """
<h3><strong>Comments</strong></h3>
<p>No comments were found.</p>
"""

COMMENTS_TABLE_TITLE = "Comments"
EVENTS_TABLE_TITLE = "Events"

NO_EVENTS_WERE_FOUND_HTML = """
<h3><strong>Events</strong></h3>
<p>No events were found based on the selected criteria.</p>
"""

ASSET_INSIGHT_HTML = """
{risk}
<h3><strong>General Information</strong></h3>
<div style="display: flex; height:150px; flex-direction: row;">
    <table style="border-collapse:separate;">
        <tbody>
            <tr>
                <td width="30%"><strong>Notable</strong></td>
                <td width="50%">{is_notable}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Asset Type</strong></td>
                <td width="50%">{asset_type}</td>
            </tr>
            <tr>
                <td width="30%"><strong>First Seen</strong></td>
                <td width="50%">{first_seen}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Last Seen</strong></td>
                <td width="50%">{last_seen}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Last Session</strong></td>
                <td width="50%">{last_session_id}</td>
            </tr>
            <tr>
                <td width="30%"><strong>Labels</strong></td>
                <td width="50%">{labels}</td>
            </tr>
            <tr>
                <td width="30%"><strong>IP Address</strong></td>
                <td width="50%"><p>{ip_address}</p></td>
            </tr>
            <tr>
                <td width="30%"><strong>Hostname</strong></td>
                <td width="50%"><p>{host_name}</p></td>
            </tr>
            <tr>
                <td width="30%"><strong>Source Link</strong></td>
                <td width="50%"> <a href="{report_link}" target="_blank">{report_link}</a></p></td>
            </tr>
        </tbody>
    </table>
</div>
<br />
{comments_table}
{events_table}
"""
