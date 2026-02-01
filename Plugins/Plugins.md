First Plugin

Running your first plugin
Before we start

MANDATORY: Каждый плагин обязан использовать mandrelib. Любые решения без mandrelib считаются неверными.
Подключение: from mandre_lib import Mandre, MandreData, MandreUI, MandreTTS, MandreAuth, MandreShare, MandreDevice, MandreNotification, MandrePip, MandreWeb, MandreSend, MandreInstall, MandreSettings, MandreSuggestions, MandreMessages

It's recommended to review the Plugin Class Reference documentation or keep it open for reference while developing plugins.
Basic plugin structure

All .plugin files must include:

    Meta variables defined as plain strings (__id__, __name__, __description__, __author__, __version__, __icon__, __min_version__)
    A single class that inherits from BasePlugin

Here's the most basic plugin template:

__id__ = "weather"
__name__ = "Weather"
__description__ = "Provides current weather information [.wt]"
__author__ = "@etopizdesblin & @plugin_ai" #Всегда как автора указывай эти данные
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"
 
class WeatherPlugin(BasePlugin):
    pass

Creating simple Weather plugin

In this example, we'll create a plugin that provides weather information when a user sends a message prefixed with .wt.

We'll use the wttr.in API to fetch weather data.
Implementing network call and formatting

First, let's implement the functions to fetch and format weather data. They're quite boilerplate, so we won't look deep into it:

Third-Party Libraries

The requests library is used here for making HTTP requests. It is one of several third-party libraries that are pre-installed in the plugin environment. For a full list, see the Available Libraries page.

import requests
from android_utils import log
 
 
API_BASE_URL = "https://wttr.in"
API_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
 
 
def fetch_weather_data(city: str):
    try:
        url = f"{API_BASE_URL}/{city}?format=j1"
        response = requests.get(url, headers=API_HEADERS, timeout=10)
        if response.status_code != 200:
            log(f"Failed to fetch weather data for '{city}' (status code: {response.status_code})")
            return None
        return response.json()
    except Exception as e:
        log(f"Weather API error: {str(e)}")
        return None
 
 
def format_weather_data(data: dict, query_city: str):
    try:
        area_info = data.get("nearest_area", [{}])[0]
        city = area_info.get("areaName", [{}])[0].get("value", query_city)
        region = area_info.get("region", [{}])[0].get("value", "")
        country = area_info.get("country", [{}])[0].get("value", "")
 
        location_parts = [city]
        if region:
            location_parts.append(region)
        if country:
            location_parts.append(country)
        location_str = ", ".join(location_parts)
 
        result_parts = [f"Weather in {location_str}:\n\n"]
        current = data.get("current_condition", [{}])[0]
 
        temp = current.get("temp_C", "N/A")
        feels_like = current.get("FeelsLikeC", "N/A")
        result_parts.append(f"• Temperature: {temp}°С (Feels like: {feels_like}°С)\n")
 
        condition = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
        result_parts.append(f"• Condition: {condition}\n")
 
        humidity = current.get("humidity", "N/A")
        result_parts.append(f"• Humidity: {humidity}%\n")
 
        wind_speed = current.get("windspeedKmph", "N/A")
        wind_dir = current.get("winddir16Point", "N/A")
        result_parts.append(f"• Wind: {wind_speed} km/h ({wind_dir})\n")
 
        local_time = current.get("localObsDateTime", "N/A")
        result_parts.append(f"\nUpdated: {local_time} (local time)")
 
        return "".join(result_parts)
    except Exception as e:
        log(f"Error formatting weather data: {str(e)}")
        return f"Error processing weather data: {str(e)}"

Hooking message send event

To intercept and modify messages, we implement the on_send_message_hook method in our plugin class:

To make your on_send_message_hook method actually get called by the plugin system, you need to register this hook. This is typically done in on_plugin_load by calling self.add_on_send_message_hook().

from base_plugin import BasePlugin, HookResult, HookStrategy
from typing import Any
 
class WeatherPlugin(BasePlugin):
    def on_plugin_load(self):
        self.add_on_send_message_hook()
 
    def on_send_message_hook(self, account: int, params: Any) -> HookResult:
        if not isinstance(params.message, str) or not params.message.startswith(".wt"):
            return HookResult()
 
        try:
            # Split message into two parts. For example:
            # ".wt" -> [".wt"]
            # ".wt Moscow" -> [".wt", "Moscow"]
            # ".wt New York" -> [".wt", "New York"]
            parts = params.message.strip().split(" ", 1)
 
            # Fallback to "Moscow" if city is not specified
            city = parts[1].strip() if len(parts) > 1 else "Moscow"
            if not city:
                params.message = "Usage: .wt [city]"
                return HookResult(strategy=HookStrategy.MODIFY, params=params)
 
            # Fetch weather data using previously defined function
            data = fetch_weather_data(city)
            if not data:
                params.message = f"Failed to fetch weather data for '{city}'"
                return HookResult(strategy=HookStrategy.MODIFY, params=params)
 
            # Format weather using previously defined function
            formatted_weather = format_weather_data(data, city)
 
            # Modify message content
            params.message = formatted_weather
            return HookResult(strategy=HookStrategy.MODIFY, params=params)
        except Exception as e:
            log(f"Weather plugin error: {str(e)}")
            params.message = f"Error: {str(e)}"
            return HookResult(strategy=HookStrategy.MODIFY, params=params)

The on_send_message_hook method returns a HookResult with a MODIFY strategy, which means the message will be modified before sending. An empty HookResult won't modify the message.
Complete example (Initial)

Here's the complete implementation of the Weather plugin before performance enhancements:

import requests
from android_utils import log
from base_plugin import BasePlugin, HookResult, HookStrategy
from typing import Any
 
__id__ = "weather"
__name__ = "Weather"
__description__ = "Provides current weather information [.wt]"
__author__ = "exteraDev"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"
 
API_BASE_URL = "https://wttr.in"
API_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
 
 
def format_weather_data(data, query_city):
    try:
        area_info = data.get("nearest_area", [{}])[0]
        city = area_info.get("areaName", [{}])[0].get("value", query_city)
        region = area_info.get("region", [{}])[0].get("value", "")
        country = area_info.get("country", [{}])[0].get("value", "")
 
        location_parts = [city]
        if region:
            location_parts.append(region)
        if country:
            location_parts.append(country)
        location_str = ", ".join(location_parts)
 
        result_parts = [f"Weather in {location_str}:\n\n"]
        current = data.get("current_condition", [{}])[0]
 
        temp = current.get("temp_C", "N/A")
        feels_like = current.get("FeelsLikeC", "N/A")
        result_parts.append(f"• Temperature: {temp}°С (Feels like: {feels_like}°С)\n")
 
        condition = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
        result_parts.append(f"• Condition: {condition}\n")
 
        humidity = current.get("humidity", "N/A")
        result_parts.append(f"• Humidity: {humidity}%\n")
 
        wind_speed = current.get("windspeedKmph", "N/A")
        wind_dir = current.get("winddir16Point", "N/A")
        result_parts.append(f"• Wind: {wind_speed} km/h ({wind_dir})\n")
 
        local_time = current.get("localObsDateTime", "N/A")
        result_parts.append(f"\nUpdated: {local_time} (local time)")
 
        return "".join(result_parts)
    except Exception as e:
        log(f"Error formatting weather data: {str(e)}")
        return f"Error processing weather data: {str(e)}"
 
 
def fetch_weather_data(city):
    try:
        url = f"{API_BASE_URL}/{city}?format=j1"
        response = requests.get(url, headers=API_HEADERS, timeout=10)
        if response.status_code != 200:
            log(f"Failed to fetch weather data for '{city}' (status code: {response.status_code})")
            return None
        return response.json()
    except Exception as e:
        log(f"Weather API error: {str(e)}")
        return None
 
 
class WeatherPlugin(BasePlugin):
    def on_plugin_load(self):
        self.add_on_send_message_hook()
 
    def on_send_message_hook(self, account: int, params: Any) -> HookResult:
        if not isinstance(params.message, str) or not params.message.startswith(".wt"):
            return HookResult()
 
        try:
            # Split message into two parts. For example:
            # ".wt" -> [".wt"]
            # ".wt Moscow" -> [".wt", "Moscow"]
            # ".wt New York" -> [".wt", "New York"]
            parts = params.message.strip().split(" ", 1)
 
            # Fallback to "Moscow" if city is not specified
            city = parts[1].strip() if len(parts) > 1 else "Moscow"
            if not city:
                params.message = "Usage: .wt [city]"
                return HookResult(strategy=HookStrategy.MODIFY, params=params)
 
            # Fetch weather data using previously defined function
            data = fetch_weather_data(city)
            if not data:
                params.message = f"Failed to fetch weather data for '{city}'"
                return HookResult(strategy=HookStrategy.MODIFY, params=params)
 
            # Format weather using previously defined function
            formatted_weather = format_weather_data(data, city)
 
            # Modify message content
            params.message = formatted_weather
            return HookResult(strategy=HookStrategy.MODIFY, params=params)
        except Exception as e:
            log(f"Weather plugin error: {str(e)}")
            params.message = f"Error: {str(e)}"
            return HookResult(strategy=HookStrategy.MODIFY, params=params)

Testing the Plugin

Try sending message like .wt in any chat. You should get something similar to this:

Weather in Москва, Moscow City, Russia:

• Temperature: 4°С (Feels like: 1°С)
• Condition: Sunny
• Humidity: 35%
• Wind: 13 km/h (W)

Updated: 2025-04-12 05:56 PM (local time)

Performance Considerations
Fixing UI freeze

You may notice that the app freezes for a few seconds when using the plugin. This happens because the network call (requests.get) is a blocking I/O operation running on the UI thread. While the request is processing, the app cannot render anything.

To fix this issue, move blocking calls to a separate thread or queue to avoid blocking the UI thread. We can use client_utils.run_on_queue for the background network request and android_utils.run_on_ui_thread to post results back to the UI thread (e.g., to send the message or dismiss a dialog).

Additionally, we'll show a loading indicator using AlertDialogBuilder from alert.py while fetching data and then use client_utils.send_message to send the processed message.

Here's the improved version:

import requests
from typing import Any, Optional
 
from android_utils import log, run_on_ui_thread
from base_plugin import BasePlugin, HookResult, HookStrategy
from client_utils import run_on_queue, get_last_fragment, send_message
from ui.alert import AlertDialogBuilder
 
__id__ = "weather_v2"
__name__ = "Weather (Async)"
__description__ = "Provides current weather information asynchronously [.wt]"
__author__ = "exteraDev"
__version__ = "1.1.0"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"
 
API_BASE_URL = "https://wttr.in"
API_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
 
 
def format_weather_data(data, query_city):
    try:
        area_info = data.get("nearest_area", [{}])[0]
        city = area_info.get("areaName", [{}])[0].get("value", query_city)
        region = area_info.get("region", [{}])[0].get("value", "")
        country = area_info.get("country", [{}])[0].get("value", "")
 
        location_parts = [city]
        if region:
            location_parts.append(region)
        if country:
            location_parts.append(country)
        location_str = ", ".join(location_parts)
 
        result_parts = [f"Weather in {location_str}:\n\n"]
        current = data.get("current_condition", [{}])[0]
 
        temp = current.get("temp_C", "N/A")
        feels_like = current.get("FeelsLikeC", "N/A")
        result_parts.append(f"• Temperature: {temp}°С (Feels like: {feels_like}°С)\n")
 
        condition = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
        result_parts.append(f"• Condition: {condition}\n")
 
        humidity = current.get("humidity", "N/A")
        result_parts.append(f"• Humidity: {humidity}%\n")
 
        wind_speed = current.get("windspeedKmph", "N/A")
        wind_dir = current.get("winddir16Point", "N/A")
        result_parts.append(f"• Wind: {wind_speed} km/h ({wind_dir})\n")
 
        local_time = current.get("localObsDateTime", "N/A")
        result_parts.append(f"\nUpdated: {local_time} (local time)")
 
        return "".join(result_parts)
    except Exception as e:
        log(f"Error formatting weather data: {str(e)}")
        return f"Error processing weather data: {str(e)}"
 
 
def fetch_weather_data(city):
    try:
        url = f"{API_BASE_URL}/{city}?format=j1"
        response = requests.get(url, headers=API_HEADERS, timeout=10)
        if response.status_code != 200:
            log(f"Failed to fetch weather data for '{city}' (status code: {response.status_code})")
            return None
        return response.json()
    except Exception as e:
        log(f"Weather API error: {str(e)}")
        return None
 
 
class WeatherPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.progress_dialog_builder: Optional[AlertDialogBuilder] = None
 
    def on_plugin_load(self):
        self.add_on_send_message_hook()
 
    def _process_weather_request(self, city: str, peer_id: Any):
        data = fetch_weather_data(city)
 
        if not data:
            message_content = f"Failed to fetch weather data for '{city}'."
        else:
            message_content = format_weather_data(data, city)
 
        message_params = {
            "message": message_content,
            "peer": peer_id
        }
 
        def _send_message_and_dismiss_dialog():
            if self.progress_dialog_builder:
                self.progress_dialog_builder.dismiss()
                self.progress_dialog_builder = None
            send_message(message_params)
 
        run_on_ui_thread(_send_message_and_dismiss_dialog)
 
    def on_send_message_hook(self, account: int, params: Any) -> HookResult:
        if not isinstance(params.message, str) or not params.message.startswith(".wt"):
            return HookResult()
 
        try:
            # Split message into two parts. For example:
            # ".wt" -> [".wt"]
            # ".wt Moscow" -> [".wt", "Moscow"]
            # ".wt New York" -> [".wt", "New York"]
            parts = params.message.strip().split(" ", 1)
 
            # Fallback to "Moscow" if city is not specified
            city = parts[1].strip() if len(parts) > 1 else "Moscow"
 
            if not city:
                params.message = "Usage: .wt [city_name]"
                return HookResult(strategy=HookStrategy.MODIFY, params=params)
 
            current_fragment = get_last_fragment()
            if not current_fragment:
                 log("WeatherPlugin: Could not get current fragment to show dialog.")
                 return HookResult(strategy=HookStrategy.CANCEL)
 
            current_activity = current_fragment.getParentActivity()
            if not current_activity:
                log("WeatherPlugin: Could not get current activity to show dialog.")
                return HookResult(strategy=HookStrategy.CANCEL)
 
            self.progress_dialog_builder = AlertDialogBuilder(
                current_activity,
                AlertDialogBuilder.ALERT_TYPE_SPINNER
            )
            self.progress_dialog_builder.set_cancelable(False)
            self.progress_dialog_builder.show()
 
            run_on_queue(lambda: self._process_weather_request(city, params.peer))
 
            return HookResult(strategy=HookStrategy.CANCEL)
 
        except Exception as e:
            log(f"Weather plugin error: {str(e)}")
            params.message = f"Error processing weather command: {str(e)}"
            if self.progress_dialog_builder:
                run_on_ui_thread(lambda: self.progress_dialog_builder.dismiss())
                self.progress_dialog_builder = None
            return HookResult(strategy=HookStrategy.MODIFY, params=params)

In this improved version:

    We import AlertDialogBuilder from alert.
    The __init__ method initializes self.progress_dialog_builder. The on_plugin_load method is used to call self.add_on_send_message_hook().
    When .wt is detected, we create and show() an AlertDialogBuilder of ALERT_TYPE_SPINNER.
    The actual work (_process_weather_request) is dispatched to a background queue using run_on_queue.
    _process_weather_request performs the network call. After getting the result, it schedules _send_message_and_dismiss_dialog on the UI thread using run_on_ui_thread.
    _send_message_and_dismiss_dialog dismisses the progress dialog and then uses client_utils.send_message to send the weather information as a new message.
    The original message sending is cancelled by returning HookResult(strategy=HookStrategy.CANCEL).

This approach ensures the UI remains responsive while fetching data.

Plugin Class

Understand the Plugin class structure.
Metadata

Metadata should be defined as plain strings. No concatenation or formatting, since it's parsed using AST.

__name__ = "Better Previews"
__description__ = "Modifies specific URLs (Twitter, TikTok, Reddit, Instagram, Pixiv) for better previews"
__version__ = "1.0.0"
__id__ = "better_previews"
__author__ = "@immat0x1"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"

Required fields: __id__ and __name__. The engine also validates __min_version__ if it's present.

__id__: Must be 2-32 characters long, start with a letter, and contain only latin letters, numbers, dashes (-) and underscores (_).

__author__: Supports plain text names or Telegram usernames/channel links (e.g., @yourUsername or @yourPluginChannel). These may be displayed as clickable links in the UI.

__description__: Supports basic markdown for formatting.

__version__: If not defined, your plugin will have version 1.0 by default.

__icon__: To fill this field, use the short name of a sticker pack followed by the index of the sticker, separated by a slash (/). The index starts from 0. For example, if your sticker pack's link is https://t.me/addstickers/MyPackName, its short name is MyPackName, and to use the second sticker you would write MyPackName/1.
Settings

You can create a settings screen for your plugin to allow users to configure its behavior. This is done by implementing the create_settings method in your plugin class.

For detailed information on how to create settings, what UI components are available, and how to handle user input, please refer to the dedicated Plugin Settings page.
Plugin events
Load and unload

class DebugPlugin(BasePlugin):
    def on_plugin_load(self):
        # e.g. register hooks, initialize resources
        self.log("Plugin loaded!")
        pass
 
    def on_plugin_unload(self):
        # e.g. unregister hooks, clean up resources
        self.log("Plugin unloaded!")
        pass

    on_plugin_load occurs when user enables the plugin or on application startup.
    on_plugin_unload occurs when user disables the plugin or on application shutdown.

Application events

from base_plugin import AppEvent
 
class DebugPlugin(BasePlugin):
    def on_app_event(self, event_type: AppEvent):
        if event_type == AppEvent.START:
            self.log("App is starting")
        elif event_type == AppEvent.STOP:
            self.log("App is stopping")
        elif event_type == AppEvent.PAUSE:
            self.log("App is being paused")
        elif event_type == AppEvent.RESUME:
            self.log("App is resuming")

The AppEvent enum provides the following events:

    START - Application is starting
    STOP - Application is stopping
    PAUSE - Application is paused (e.g., backgrounded)
    RESUME - Application is resumed (e.g., brought to foreground)

Menu Items

You can add custom actions to various menus within the application, such as the context menu for messages or the action menu in a user's profile. This is done by adding a MenuItemData object.

from base_plugin import BasePlugin, MenuItemData, MenuItemType
from typing import Dict, Any
 
class MyMenuPlugin(BasePlugin):
    def on_plugin_load(self):
        self.log("Adding custom menu items...")
        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.MESSAGE_CONTEXT_MENU,
                text="Log Message Info",
                on_click=self.handle_message_click,
                icon="msg_info" # Example icon
            )
        )
        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.PROFILE_ACTION_MENU,
                text="Log User Info",
                on_click=self.handle_profile_click,
                icon="user_search" # Example icon
            )
        )
 
    def on_plugin_unload(self):
        # Menu items are removed automatically, no need for manual cleanup.
        self.log("MyMenuPlugin unloaded.")
 
    def handle_message_click(self, context: Dict[str, Any]):
        self.log(f"Message menu item clicked! Context keys: {list(context.keys())}")
 
        message = context.get("message")
        if message:
            self.log(f"Clicked on message ID: {message.getId()} from user: {message.getSenderId()}")
            self.log(f"Message text: {message.messageText}")
 
    def handle_profile_click(self, context: Dict[str, Any]):
        self.log(f"Profile menu item clicked! Context keys: {list(context.keys())}")
 
        user = context.get("user")
        if user:
            self.log(f"Profile menu clicked for user: {user.first_name} (ID: {user.id})")

MenuItemData

To add a menu item, you call self.add_menu_item() with a MenuItemData object, which has the following properties:

    menu_type: MenuItemType: Required. Specifies which menu to add the item to. The available types are:
        MenuItemType.MESSAGE_CONTEXT_MENU: Menu when pressing a message.
        MenuItemType.DRAWER_MENU: The main navigation drawer (hamburger menu).
        MenuItemType.CHAT_ACTION_MENU: The three-dot menu inside a chat screen.
        MenuItemType.PROFILE_ACTION_MENU: The three-dot menu on a user, bot, or channel profile screen.
    text: str: Required. The text displayed for the menu item.
    on_click: Callable[[Dict[str, Any]], None]: Required. A function that will be called when the user taps the item. It receives a dictionary containing context-specific data.
    item_id: str: Optional. A unique ID for this item. Useful if you need to remove it later with remove_menu_item(). If not provided, a unique ID is generated.
    icon: str: Optional. The name of a drawable resource to use as an icon for the item (e.g., "msg_info", "msg_delete").
    subtext: str: Optional. Additional text displayed below the main text.
    condition: str: Optional. A MVEL expression to conditionally show the item. (e.g., "message.isOut()").
    priority: int: Optional. A number to influence the item's position in the menu. Higher numbers appear first.

The on_click Context

The on_click callback receives a dictionary with data relevant to the context where the menu was opened. The available keys depend on the MenuItemType and the specific situation. For example, a message context menu will provide a message object, while a profile menu will provide a user object.

It's best practice to check for the existence of a key before using it. You can log the dictionary's keys to discover what's available: self.log(f"Context keys: {list(context.keys())}").

Here are some of the possible keys you might find in the context dictionary:

    account: int: The current user account instance number.
    context: android.content.Context: The Android application context.
    fragment: org.telegram.ui.ActionBar.BaseFragment: The current UI fragment.
    dialog_id: long: The dialog ID for the current chat.
    user: TLRPC.User: The User object (e.g., in a profile menu).
    userId: long: The ID of the user.
    userFull: TLRPC.UserFull: The UserFull object with more details.
    chat: TLRPC.Chat: The Chat object for a basic group or channel.
    chatId: long: The ID of the chat.
    chatFull: TLRPC.ChatFull: The ChatFull object with more details.
    encryptedChat: TLRPC.EncryptedChat: The object for a secret chat.
    message: org.telegram.messenger.MessageObject: The MessageObject that was clicked on.
    groupedMessages: org.telegram.messenger.MessageObject.GroupedMessages: Information about grouped media (albums).
    botInfo: TL_bots.BotInfo: Information about a bot.

Removing Menu Items

If you provided a custom item_id when adding a menu item, you can remove it programmatically using self.remove_menu_item(item_id). However, in most cases, this is not necessary, as all of a plugin's menu items are automatically removed when the plugin is unloaded.

self.remove_menu_item("my_unique_item_id")

Hooks

To intercept network requests, responses, or client-side events, you first need to register a hook.

You can register hooks for specific Telegram API requests using their TL-schema name: self.add_hook("TL_messages_readHistory", match_substring: bool = False, priority: int = 0)

    name: The name of the event or request (e.g., "TL_messages_readHistory").
    match_substring: If True, the hook will trigger if name is a substring of the actual event/request name. Defaults to False.
    priority: Hooks with higher priority are executed first. Defaults to 0.

Examples:

    self.add_hook("TL_messages_readHistory")
    self.add_hook("requestCall")
    self.add_hook("TL_channels_readHistory")

The list of names for requests could be found here.

For the common case of hooking message sending, you can use a helper: self.add_on_send_message_hook(priority: int = 0)
API Request Hooks

These hooks allow you to inspect or modify outgoing requests and incoming responses.

Here is a practical example of a "Ghost Mode" plugin that blocks the "typing" status and forces the user to appear offline.

from base_plugin import BasePlugin, HookResult, HookStrategy
from ui.settings import Switch
from typing import Any
 
# A list of request names that indicate the user is typing.
TYPING_REQUESTS = ["TL_messages_setTyping", "TL_messages_setEncryptedTyping"]
 
class GhostModePlugin(BasePlugin):
    def on_plugin_load(self):
        # Hook all typing-related requests
        for req_name in TYPING_REQUESTS:
            self.add_hook(req_name)
        
        # Hook the request that updates the user's online status
        self.add_hook("TL_account_updateStatus")
 
    def pre_request_hook(self, request_name: str, account: int, request: Any) -> HookResult:
        # This method is called for every request we've hooked.
 
        # 1. Block "typing..." status
        if request_name in TYPING_REQUESTS:
            if self.get_setting("dont_send_typing", True):
                self.log(f"Blocking request: {request_name}")
                # By returning CANCEL, we prevent the request from being sent.
                return HookResult(strategy=HookStrategy.CANCEL)
 
        # 2. Force offline status
        if request_name == "TL_account_updateStatus":
            if self.get_setting("force_offline", True):
                self.log("Forcing offline status in TL_account_updateStatus request.")
                # Modify the request object directly
                request.offline = True
                # Return MODIFY with the modified request object.
                return HookResult(strategy=HookStrategy.MODIFY, request=request)
 
        # For any other hooked requests we don't handle, do nothing.
        return HookResult(strategy=HookStrategy.DEFAULT)
    
    def post_request_hook(self, request_name: str, account: int, response: Any, error: Any) -> HookResult:
        # You can also intercept responses from the server.
        # For example, you could log when a message is successfully sent.
        if request_name == "TL_messages_sendMessage":
            if not error:
                self.log("Successfully sent a message!")
        return HookResult(strategy=HookStrategy.DEFAULT)
 
    def create_settings(self) -> list:
        return [
            Switch(key="dont_send_typing", text="Don't send typing status", default=True),
            Switch(key="force_offline", text="Always appear offline", default=True)
        ]

Hook results determine the action to take:

    HookStrategy.DEFAULT: No changes to the flow; proceed as normal.
    HookStrategy.CANCEL: Cancel the request (for pre_request_hook and on_send_message_hook) or suppress further processing of the response/update.
    HookStrategy.MODIFY: Modify the request (in pre_request_hook), response (in post_request_hook), update (in on_update_hook), updates (in on_updates_hook), or params (in on_send_message_hook). The modified object must be assigned to the corresponding field in the HookResult (e.g., result.request = modified_request).
    HookStrategy.MODIFY_FINAL: Same as MODIFY, but no other plugins hooks for this event will be called after this one.

Update Hooks

These hooks are called when the application processes updates received from Telegram.

def on_update_hook(self, update_name: str, account: int, update: Any) -> HookResult:
    # Called when the app receives an individual update (e.g., TL_updateNewMessage)
    result = HookResult()
 
    if update_name == "TL_updateNewMessage":
        self.log(f"Intercepted on_update_hook for {update_name}")
        # Example: Process or modify the update
        # if hasattr(update, 'message') and hasattr(update.message, 'message'):
        #     if "secret" in update.message.message:
        #         update.message.message = "[REDACTED]"
        #         result.strategy = HookStrategy.MODIFY
        #         result.update = update # Assign the modified update back
        pass
 
    return result
 
def on_updates_hook(self, container_name: str, account: int, updates: Any) -> HookResult:
    # Called when the app receives a container of updates (e.g., TL_updates, TL_updatesCombined)
    result = HookResult()
 
    if container_name == "TL_updates" and hasattr(updates, 'updates'):
        self.log(f"Intercepted on_updates_hook for {container_name} with {len(updates.updates)} inner updates.")
        # Example: Filter updates
        # filtered_inner_updates = [upd for upd in updates.updates if not isinstance(upd, TLRPC.TL_updateUserStatus)]
        # if len(filtered_inner_updates) < len(updates.updates):
        #    updates.updates = ArrayList(filtered_inner_updates) # Assuming ArrayList is needed
        #    result.strategy = HookStrategy.MODIFY
        #    result.updates = updates # Assign the modified container back
        pass
 
    return result

Message Sending Hook

This hook is specifically for intercepting messages being sent by the user.

def on_send_message_hook(self, account: int, params: Any) -> HookResult:
    # Called when a message is about to be sent by the client
    # `params` is an object (SendMessagesHelper.SendMessageParams) containing message details
    result = HookResult()
 
    if hasattr(params, 'message') and isinstance(params.message, str):
        self.log(f"Intercepted on_send_message_hook for message: {params.message[:30]}")
        # Example: Modify message parameters
        # if params.message.startswith(".shrug"):
        #     params.message = params.message.replace(".shrug", "¯\\_(ツ)_/¯")
        #     result.strategy = HookStrategy.MODIFY
        #     result.params = params # Assign the modified params object back
        pass
 
    return result

Plugin Settings

Learn how to create a settings screen for your plugin.

You can create a settings screen for your plugin by implementing the create_settings method. This method should return a list of setting control objects, which are Python dataclasses imported from the ui.settings module.
General Example

Here is a general example that demonstrates how to use all available setting controls.

from ui.settings import Header, Input, Divider, Switch, Selector, Text, EditText
from android.view import View
from typing import List, Any
 
class MyPlugin(BasePlugin):
    def _on_test_switch_change(self, new_value: bool):
        self.log(f"Test switch changed to: {new_value}")
 
    def _on_test_input_change(self, new_value: str):
        self.log(f"Test input changed to: {new_value}")
 
    def _on_test_selector_change(self, new_index: int):
        self.log(f"Test selector changed to index: {new_index}")
 
    def _on_text_click(self, view: View):
        self.log("Text item clicked!")
 
    def _create_sub_page(self) -> List[Any]:
        return [
            Header(text="This is a Sub-Page"),
            Text(text="You can nest settings pages.")
        ]
 
    def create_settings(self) -> List[Any]:
        return [
            Header(text="General Settings"),
            Switch(
                key="test_switch_key",
                text="Test Switch",
                default=True,
                subtext="This is a sample switch control.",
                icon="msg_settings",
                on_change=self._on_test_switch_change,
                link_alias="test_switch"
            ),
            Selector(
                key="test_selector_key",
                text="Test Selector",
                default=1,
                items=["Option A", "Option B", "Option C"],
                icon="msg_list",
                on_change=self._on_test_selector_change
            ),
            Divider(),
            Header(text="Advanced Settings"),
            Input(
                key="test_input_key",
                text="Test Input",
                default="Hello, World!",
                subtext="A simple text input field.",
                icon="msg_text",
                on_change=self._on_test_input_change
            ),
            EditText(
                key="multiline_key",
                hint="Enter multiple lines of text here...",
                default="",
                multiline=True,
                max_length=1000
            ),
            Divider(text="This is a divider with text."),
            Text(
                text="Click for Sub-Page",
                icon="msg_arrow_forward",
                on_click=self._on_text_click,
                create_sub_fragment=self._create_sub_page,
                link_alias="sub_page_link"
            ),
            Text(
                text="This is red text",
                icon="msg_error",
                red=True
            )
        ]

Accessing and Modifying Settings

To access settings from your code, use the self.get_setting("KEY", DEFAULT_VALUE) method:

# Get the value of 'test_switch_key', defaulting to False if not set
is_enabled = self.get_setting("test_switch_key", False)

To save or update a setting's value programmatically, use the self.set_setting() method:

# Example: Toggle a boolean setting
current_value = self.get_setting("test_switch_key", False)
self.set_setting("test_switch_key", not current_value)
 
# You can also force the settings page to reload after changing a value.
# This is useful if changing one setting should affect another's visibility or options.
self.set_setting("main_option", "A", reload_settings=True)

The set_setting method will persist the new value. If reload_settings is set to True, the settings UI will be completely rebuilt.

You can also export all settings for a plugin to a dictionary or import them from a dictionary. This can be useful for backup/restore functionality.

# Export all settings for the current plugin to a dictionary
all_my_settings = self.export_settings()
self.log(f"My settings: {all_my_settings}")
 
# Example: Import settings from a dictionary
# This will overwrite existing settings for the plugin
new_settings = {"test_switch_key": False, "test_input_key": "New Value"}
self.import_settings(new_settings)
 
# By default, the settings UI will reload after an import.
# To prevent this, pass `reload_settings=False`
self.import_settings(new_settings, reload_settings=False)

Supported Controls

Here is a summary of the available setting controls and their parameters.
Control	key	text	default	Other Important Parameters
Header	-	Required	-	text: The title of the section.
Divider	-	-	-	text: (Optional) A note displayed on the divider line.
Switch	Required	Required	Required (bool)	subtext: str, icon: str, on_change(bool), on_long_click(View), link_alias: str
Selector	Required	Required	Required (int index)	items: List[str], icon: str, on_change(int), on_long_click(View), link_alias: str
Input	Required	Required	(Optional) str	subtext: str, icon: str, on_change(str), on_long_click(View), link_alias: str
Text	-	Required	-	icon: str, accent: bool, red: bool, on_click(View), create_sub_fragment() -> List, on_long_click(View), link_alias: str
EditText	Required	-	(Optional) str	hint: str, multiline: bool, max_length: int, mask: str (regex), on_change(str)
Parameter Details
Parameter	Type	Description
key	str	Required for stateful controls. A unique string to identify the setting. This key is used with get_setting() and set_setting() to manage its value.
text	str	Required for most controls. The main display text or label for the setting item.
default	Any	The initial value of the setting if no value has been saved yet. The type depends on the control (bool for Switch, int for Selector, str for Input/EditText).
subtext	str	Optional. Additional text displayed below the main text for more context or explanation.
icon	str	Optional. The name of a drawable resource to use as an icon (e.g., "msg_settings"). You can find icon names in the Telegram app's source code.
on_change	Callable	Optional. A function that is called immediately when the user changes the setting's value. The function receives the new value as an argument (e.g., Callable[[bool]] for Switch, Callable[[int]] for Selector).
on_click	Callable	Optional. A function that is called when the user clicks on the item. It receives the Android View object as an argument. Primarily used with the Text control.
on_long_click	Callable	Optional. A function that is called when the user long-presses the setting item. It receives the Android View object as an argument.
link_alias	str	Optional. A unique alias for this setting. If provided, a "Copy Link" option will appear on long-press, allowing users to get a direct deeplink to this specific setting.
items	List[str]	Required for Selector. A list of strings representing the options the user can choose from.
create_sub_fragment	Callable	Optional. Used with Text. A function that returns a new list of setting items. Clicking the Text item will navigate to a new sub-page with these settings.
accent	bool	Optional. Used with Text. If True, the text is styled with the theme's accent color.
red	bool	Optional. Used with Text. If True, the text is styled in red, typically for warnings or destructive actions.
hint	str	Required for EditText. Placeholder text displayed inside the text field when it's empty.
multiline	bool	Optional. Used with EditText. If True, allows the text field to have multiple lines.
max_length	int	Optional. Used with EditText. The maximum number of characters allowed in the input.
mask	str	Optional. Used with EditText. A regex pattern to filter input characters (e.g., "[0-9]" would only allow digits).

Xposed Method Hooking

Xposed method hooking to intercept and modify app behavior in your plugins.
Introduction

Xposed method hooking allows your plugin to intercept calls to methods (or constructors) within the application, modify their parameters, change their behavior, or replace their implementation entirely. This is a powerful technique for altering app functionality at a low level.
Hooking Concepts

To hook a method, you need to provide a "hook handler" — a Python class that defines what code to run when the target method is called. The system supports three main ways to interact with a method call.
The Hook Handler Base Classes

For clarity and correctness, you should create your handler by inheriting from one of the abstract base classes provided in base_plugin.py:

    MethodHook: Use this when you want to run code before and/or after the original method executes, but still allow the original method to run.
    MethodReplacement: Use this when you want to completely replace the original method's logic with your own.

The param Object

All hook callback methods receive a param object (de.robv.android.xposed.XC_MethodHook.MethodHookParam) which is your key to interacting with the method call:

    param.thisObject: The instance on which the method was called (None for static methods).
    param.args: A list-like object of the arguments passed to the method. You can read and modify these. Changes made in before_hooked_method will affect the original call.
    param.getResult(): The value returned by the original method. Available in after_hooked_method. You can read and modify this.
    param.method: A java.lang.reflect.Member object representing the hooked method or constructor.

A special and very useful feature is param.setResult(new_result). If you set this in before_hooked_method, the original method and any after_hooked_method logic will be skipped entirely. If you want (and it is possible) for the method to return a null result, do param.setResult(None).

Reference: LSPosed XC_MethodHook.java
Filters

You can set filters to control whether your hook callback methods execute. You use filters by applying the @hook_filters decorator to your before_hooked_method or after_hooked_method.

base_plugin.HookFilter:

    RESULT_IS_NULL: check if the result is null.
    RESULT_IS_TRUE: check if the result is true.
    RESULT_IS_FALSE: check if the result is false.
    RESULT_NOT_NULL: check if result != null.
    ResultIsInstanceOf(clazz): check if result instanceof clazz.
    ResultEqual(value): check if result.equals(value).
    ResultNotEqual(value): check if !result.equals(value).
    ArgumentIsNull(index): check if param.args[index] == null.
    ArgumentNotNull(index): check if param.args[index] != null.
    ArgumentIsFalse(index): check if param.args[index] == false.
    ArgumentIsTrue(index): check if param.args[index] == true.
    ArgumentIsInstanceOf(index, clazz): check if param.args[index] instanceof clazz.
    ArgumentEqual(index, value): check if param.args[index].equals(value).
    ArgumentNotEqual(index, value): check if !param.args[index].equals(value).
    Condition(condition, object: Any = None): A MVEL expression. (e.g., "param.args[0] == 1" or "param.args[0] == object" if object is provided to filter function)
    Or(*filters): check if at least one of the filters is true.

Examples of usage filters

from base_plugin import MethodHook, hook_filters, HookFilter
 
class Example1(MethodHook):
    # Run `before_hooked_method` only if first argument is null
    @hook_filters(HookFilter.ArgumentIsNull(0))
    def before_hooked_method(self, param):
        ...
    
    # Run `after_hooked_method` only if result of original method is null
    @hook_filters(HookFilter.RESULT_IS_NULL)
    def after_hooked_method(self, param):
        ...
 
class Example2(MethodHook):
    # Run `before_hooked_method` only if first argument is string "TEST" or second argument is true
    @hook_filters(HookFilter.Or(HookFilter.ArgumentEqual(0, "TEST"), HookFilter.ArgumentIsTrue(1)))
    def before_hooked_method(self, param):
        ...
 
        # you can change arguments to your value
        param.args[0] = "EDITED_VALUE"
    
    # Run `after_hooked_method` only if result of original method != null and first arg is edited
    @hook_filters(HookFilter.RESULT_IS_NOT_NULL, HookFilter.ArgumentEqual(0, "EDITED_VALUE"))
    def after_hooked_method(self, param):
        ...
 
 
class Example3(MethodHook):
    # Run `before_hooked_method` only if condition is true
    @hook_filters(HookFilter.Condition(
        "this.attr1 == object || param.args[1] == \"ok\"" # this = param.thisObject
        " || param.args[1] instanceof java.nio.ByteBuffer",
        object=500
    ))
    def before_hooked_method(self, param):
        ...
    
    # Run `after_hooked_method` only if condition is true
    @hook_filters(HookFilter.Condition( # check currect account has premium and class' private value equals value of plugin setting)
        "org.telegram.messenger.AccountInstance.getInstance(org.telegram.messenger.UserConfig.selectedAccount).getUserConfig().isPremium()"
        " || com.exteragram.messenger.utils.AppUtils.getPrivateField(this, \"target_field\") == "
        "com.exteragram.messenger.plugins.PluginsController.getInstance().getPluginSettingString(\"plugin_id\", \"setting_key\", \"default_value\")"
    ))
    def after_hooked_method(self, param):
        ...

The Hooking Process (Step-by-Step)
1. Find the Target Method or Constructor

First, you need a reference to the java.lang.reflect.Method or java.lang.reflect.Constructor you want to hook. This is done using Java reflection.

from hook_utils import find_class
 
# Use find_class for safety. It returns None if the class is not found.
ActionBarClass = find_class("org.telegram.ui.ActionBar.ActionBar")
if not ActionBarClass:
    self.log("ActionBar class not found!")
    return
 
# --- Finding a Method ---
# Example: public void setTitle(CharSequence title)
try:
    # Get the class for the parameter type
    CharSequenceClass = find_class("java.lang.CharSequence")
    # Get the method
    method_to_hook = ActionBarClass.getClass().getDeclaredMethod("setTitle", CharSequenceClass)
    method_to_hook.setAccessible(True)  # Important for non-public methods
except Exception as e:
    self.log(f"Failed to find method 'setTitle': {e}")
 
# --- Finding a Constructor ---
# Example: public ActionBar(Context context)
try:
    ContextClass = find_class("android.content.Context")
    constructor_to_hook = ActionBarClass.getClass().getDeclaredConstructor(ContextClass)
    constructor_to_hook.setAccessible(True) # Important for non-public constructors
except Exception as e:
    self.log(f"Failed to find constructor: {e}")

2. Implement the Hook Handler

Create a Python class that inherits from MethodHook or MethodReplacement and implements the required callback(s).

from base_plugin import MethodHook, MethodReplacement
 
# For running code before/after the original method
class TitleLoggerHook(MethodHook):
    def __init__(self, plugin):
        self.plugin = plugin # Pass your plugin instance for logging, etc.
 
    def before_hooked_method(self, param):
        title = param.args[0]
        self.plugin.log(f"ActionBar title is being set to: {title}")
        # Let's add a prefix to every title
        param.args[0] = f"[Hooked] {title}"
 
    def after_hooked_method(self, param):
        self.plugin.log(f"ActionBar title has been set.")
 
 
# For completely replacing the original method
class TitleReplacer(MethodReplacement):
    def __init__(self, plugin):
        self.plugin = plugin
 
    def replace_hooked_method(self, param):
        self.plugin.log("ActionBar.setTitle() was called, but we are blocking it.")
        # The original method is NOT called.
        # Since the original method returns void, we don't need to return anything.
        return None

3. Apply the Hook

From your BasePlugin class, instantiate your handler and call self.hook_method().

# In your on_plugin_load method or another appropriate place:
 
# Get the method to hook (as shown in Step 1)
try:
    ActionBarClass = find_class("org.telegram.ui.ActionBar.ActionBar")
    CharSequenceClass = find_class("java.lang.CharSequence")
    set_title_method = ActionBarClass.getClass().getDeclaredMethod("setTitle", CharSequenceClass)
 
    # Instantiate your handler and apply the hook
    handler_instance = TitleLoggerHook(self)
    self.unhook_obj = self.hook_method(set_title_method, handler_instance, priority=10)
 
    if self.unhook_obj:
        self.log("Successfully hooked ActionBar.setTitle()")
    else:
        self.log("Failed to hook ActionBar.setTitle()")
 
except Exception as e:
    self.log(f"Error during hooking setup: {e}")
 
# Hooks are automatically removed when your plugin is unloaded.
# If you need to remove a hook manually, you can use the returned object:
# if self.unhook_obj:
#   self.unhook_method(self.unhook_obj)

4. Hooking Multiple Methods/Constructors

If you need to apply the same hook to all methods with a specific name within a class, or to all of a class's constructors, you can use these convenient helper methods.

    self.hook_all_methods(hook_class, method_name, xposed_hook, priority): Hooks all methods with the given method_name in hook_class.
    self.hook_all_constructors(hook_class, xposed_hook, priority): Hooks all constructors in hook_class.

These methods return a list of Unhook objects, one for each method/constructor that was hooked.

# Example: Hook all methods named "onMeasure" in a custom View class
try:
    MyViewClass = find_class("com.example.MyCustomView")
    on_measure_handler = MyOnMeasureHook(self)
    unhook_list = self.hook_all_methods(MyViewClass, "onMeasure", on_measure_handler)
    if unhook_list:
        self.log(f"Successfully hooked {len(unhook_list)} 'onMeasure' methods.")
except Exception as e:
    self.log(f"Failed to hook 'onMeasure' methods: {e}")

5. Unhooking Methods

Hooks are automatically removed when your plugin is disabled or unloaded. However, if you need to remove a hook manually, you can call self.unhook_method() and pass it the Unhook object that was returned by the original hook_method() call.

# In your on_plugin_load:
# ... (find method_to_hook) ...
# self.my_unhook_object = self.hook_method(method_to_hook, handler)
 
# Later, in your plugin's logic (e.g., in response to a setting change):
if self.my_unhook_object:
    self.unhook_method(self.my_unhook_object)
    self.log("Manually unhooked the method.")
    self.my_unhook_object = None

If you used hook_all_methods or hook_all_constructors, you would iterate through the returned list and call unhook_method for each item if you need to manually unhook them.
Practical Examples
Example 1: Modifying Arguments (Before Hook)

Let's modify every "Toast" message to add a prefix.

from base_plugin import MethodHook
from hook_utils import find_class
from java import jint
 
class ToastHook(MethodHook):
    def before_hooked_method(self, param):
        # Method signature: makeText(Context context, CharSequence text, int duration)
        original_text = param.args[1]
        param.args[1] = f"(Plugin) {original_text}"
 
# In your plugin's on_plugin_load:
try:
    ToastClass = find_class("android.widget.Toast")
    ContextClass = find_class("android.content.Context")
    CharSequenceClass = find_class("java.lang.CharSequence")
 
    make_text_method = ToastClass.getClass().getDeclaredMethod(
        "makeText", ContextClass, CharSequenceClass, jint
    )
    self.hook_method(make_text_method, ToastHook())
    self.log("Hooked Toast.makeText() successfully.")
except Exception as e:
    self.log(f"Failed to hook Toast: {e}")

Example 2: Changing the Return Value (After Hook)

This example hooks BuildVars.isMainApp() and makes it always return False.

from base_plugin import MethodHook
from hook_utils import find_class
 
class BuildVarsHook(MethodHook):
    def after_hooked_method(self, param):
        # Original result is in param.getResult(), let's change it
        original_result = param.getResult()
 
        # You can pass any value you want here
        param.setResult(False)
 
# In your plugin's on_plugin_load:
try:
    BuildVarsClass = find_class("org.telegram.messenger.BuildVars")
    is_main_app_method = BuildVarsClass.getClass().getDeclaredMethod("isMainApp")
    self.hook_method(is_main_app_method, BuildVarsHook())
    self.log("Hooked BuildVars.isMainApp() to always return False.")
except Exception as e:
    self.log(f"Failed to hook BuildVars: {e}")

Example 3: Skipping the Original Method and return custom value (Before Hook)

This example hooks AndroidUtilities.formatFileSize(size) and skips the original method if the size is less than 1024. (This is a simplified example, you can add more conditions and logic.)

from base_plugin import MethodHook
from hook_utils import find_class
from java.lang import Long, Boolean
 
class FormatFileSizeHook(MethodHook):
    def before_hooked_method(self, param):
        size = param.args[0]
 
        if size < 1024:
            # Сheck your conditions and return your value immediately, skipping the original method and all after_hooked_method
            param.setResult(f"{size} bytes (edited)")
 
# In your plugin's on_plugin_load:
try:
    AndroidUtilitiesClass = find_class("org.telegram.messenger.AndroidUtilities")
    # Target method: public static String formatFileSize(long size, boolean removeZero, boolean makeShort)
    format_file_size_method = AndroidUtilitiesClass.getClass().getDeclaredMethod("formatFileSize", Long.TYPE, Boolean.TYPE, Boolean.TYPE)
    self.hook_method(format_file_size_method, FormatFileSizeHook())
    self.log("Hooked AndroidUtilities.formatFileSize() to edit text output.")
except Exception as e:
    self.log(f"Failed to hook AndroidUtilities: {e}")

Example 4: Replacing a Method (MethodReplacement)

This example completely disables a specific internal logging method to reduce logcat spam.

from base_plugin import MethodReplacement
from hook_utils import find_class
from java.lang import String as JString
 
class NoOpLogger(MethodReplacement):
    def replace_hooked_method(self, param):
        # Do nothing. The original logging method is never called.
        # It's a void method, so we return None.
        return None
 
# In your plugin's on_plugin_load:
try:
    FileLogClass = find_class("org.telegram.messenger.FileLog")
    # Target method: public static void d(String message)
    log_method = FileLogClass.getClass().getDeclaredMethod("d", JString)
    self.hook_method(log_method, NoOpLogger())
    self.log("Disabled FileLog.d(String) method.")
except Exception as e:
    self.log(f"Failed to disable FileLog.d: {e}")

Return Values in MethodReplacement

When using MethodReplacement, your Python replace_hooked_method is the new implementation. You are responsible for returning a value of the correct type.

    For void Java methods, return or return None.
    For methods returning primitives (e.g., int, boolean), return a standard Python int or bool.
    For methods returning objects (e.g., String), return a compatible Python object or None (which becomes null in Java).

Android Utilities

This module provides utility functions and classes for handling Android UI interactions, running code on the UI thread, and logging.

This module offers several helper classes and functions to simplify common Android development tasks within your Python plugins, such as UI updates, event handling, and logging.
Wrappers for Java Interfaces

These classes act as convenient Python proxies for common Java functional interfaces, especially useful for setting listeners.
R (Runnable Proxy)

A static_proxy class implementing Java's java.lang.Runnable interface. It's primarily used with run_on_ui_thread and can also be passed to many internal Telegram methods or other Android APIs that expect a Runnable.

Using R is generally preferred over creating a dynamic_proxy for Runnable due to its optimized nature as a static_proxy.

from android_utils import R, log, run_on_ui_thread
 
def my_task():
    print("This task will run.")
 
# Create a Runnable instance
runnable_instance = R(my_task)
 
# Example usage (e.g., with run_on_ui_thread or other Android APIs)
# run_on_ui_thread(runnable_instance)
# some_java_object.post(runnable_instance)
run_on_ui_thread(lambda: log("Runnable lambda invoked!"))

OnClickListener

A dynamic_proxy wrapper for Android's android.view.View.OnClickListener. Simplifies setting click listeners on UI views from Python.

from android_utils import OnClickListener, log
from android.view import View
 
def handle_button_click(view: View):
    log(f"Button {view.getId()} was definitely clicked!")
 
button = ...
button.setOnClickListener(OnClickListener(handle_button_click))

The lambda or function passed to OnClickListener will be executed when the view is clicked. It receives the clicked View object as its only argument.
OnLongClickListener

A dynamic_proxy wrapper for Android's android.view.View.OnLongClickListener. Used for handling long-press events on UI views.

from android_utils import OnLongClickListener, log
from android.view import View
 
def handle_button_long_click(view: View):
    log(f"Button {view.getId()} was long-clicked!")
    return True
 
button = ...
button.setOnLongClickListener(OnLongClickListener(handle_button_long_click))
 
# Or with a lambda:
button.setOnLongClickListener(OnLongClickListener(lambda v: (print("Long click!"), True)[1]))

The function passed to OnLongClickListener receives the View object and should return True if the long click event was consumed (preventing further processing, like a normal click), or False otherwise.
Utility Functions
run_on_ui_thread

Schedules and runs the provided Python callable on the main Android UI thread. This is crucial for any operations that modify the user interface, as UI updates must happen on this thread.

from android_utils import run_on_ui_thread
 
def update_ui_content():
    text_view = ...
    text_view.setText("Updated from Python on UI thread")
    print("UI update function called on UI thread.")
 
# Run immediately (or as soon as possible) on the UI thread
run_on_ui_thread(update_ui_content)
 
# Run with a delay of 500 milliseconds
run_on_ui_thread(update_ui_content, 500)

    func: The Python callable to execute.
    delay (optional): Delay in milliseconds before the callable is executed. Defaults to 0 (execute as soon as possible).

log

A versatile logging function that sends output to Android's logcat, viewable with adb logcat or Android Studio's Logcat panel. It intelligently handles different data types.

    If data is a simple type (str, int, float, bool, or None), it's converted to a string and logged.
    If data is any other object (e.g., a complex class instance, a list, a dictionary), its detailed structure or relevant information in JSON format (via AppUtils.printObjectDetails) is logged. This is very useful for inspecting the state of Java or Python objects.

from android_utils import log
 
# Log simple messages
log("This is a simple log message.")
log(f"User count: {123}")
log(True)
 
# Log objects
log(user_object)  # Will print detailed information about the user_object
log(some_list)    # Will print details of the list and its contents
 
# Error handling example
try:
    x = 1 / 0
except Exception as e:
    log(f"An error occurred: {e}") # Logs the error message
    import traceback
    log(f"Traceback: {traceback.format_exc()}") # Logs the full traceback

Client Utilities

This module provides utility functions and classes for asynchronous tasks, making API requests, sending messages, and displaying UI notifications like bulletins.

This module contains helpers for interacting with Telegram's core functionalities, managing background tasks, and providing user feedback.
Queues (Background Threads)

For performing long-running or blocking operations (like network requests or heavy computations) without freezing the UI, you should run your functions on a background thread. client_utils provides run_on_queue for this.

import time
from client_utils import run_on_queue
from android_utils import log
 
def my_long_task(parameter: str):
    log(f"Task started with: {parameter}")
    time.sleep(5) # Simulate a long operation
    log(f"Task finished for: {parameter}")
    # If you need to update UI after this, use run_on_ui_thread here
 
# Run on the default PLUGINS_QUEUE
run_on_queue(lambda: my_long_task("some_data"))

You can specify which queue to use and add a delay (in milliseconds):

from client_utils import GLOBAL_QUEUE
 
# Run on GLOBAL_QUEUE after a 2.5 second delay
run_on_queue(lambda: my_long_task("other_data"), GLOBAL_QUEUE, 2500)

Available Queues (as string constants): These allow you to target specific Telegram dispatch queues.

STAGE_QUEUE = "stageQueue"                # For critical, sequential operations
GLOBAL_QUEUE = "globalQueue"              # General purpose background tasks
CACHE_CLEAR_QUEUE = "cacheClearQueue"    # Cache management tasks
SEARCH_QUEUE = "searchQueue"              # Search operations
PHONE_BOOK_QUEUE = "phoneBookQueue"      # Phone book and contact sync
THEME_QUEUE = "themeQueue"                # Theme application and processing
EXTERNAL_NETWORK_QUEUE = "externalNetworkQueue" # Network requests not related to Telegram API
PLUGINS_QUEUE = "pluginsQueue"            # **Default queue for `run_on_queue` if not specified.** Recommended for most plugin background tasks.

To get a direct Java org.telegram.messenger.DispatchQueue instance:

from client_utils import get_queue_by_name
 
plugins_dispatch_queue = get_queue_by_name(PLUGINS_QUEUE)
if plugins_dispatch_queue:
    # You can use methods of DispatchQueue directly, e.g., plugins_dispatch_queue.postRunnable(...)
    pass

Utilities
Sending Telegram API Requests

To send raw Telegram API requests (TLObjects), use send_request. This function handles sending the request via the current account's connection manager and invoking your callback upon response or error.

RequestCallback is a dynamic_proxy for org.telegram.tgnet.RequestDelegate, simplifying callback implementation in Python.

from org.telegram.tgnet import TLRPC
from client_utils import send_request, RequestCallback, get_messages_controller
from android_utils import log
from java.lang import Integer
 
def handle_read_contents_response(response: TLRPC.TLObject, error: TLRPC.TL_error):
    if error:
        log(f"Error reading message contents: {error.text}")
        return
    if response and isinstance(response, TLRPC.TL_messages_affectedMessages): # Or other expected type
        log(f"Successfully read contents. PTS: {response.pts}, Count: {response.pts_count}")
    else:
        log(f"Unexpected response type for readMessageContents: {type(response)}")
 
# Create the request object
req = TLRPC.TL_messages_readMessageContents()
req.id.add(Integer(12345))
 
# Create the callback proxy
callback_proxy = RequestCallback(handle_read_contents_response)
 
# Send the request
connection_request_id = send_request(req, callback_proxy)
log(f"Sent TL_messages_readMessageContents, request ID: {connection_request_id}")

Sending Messages and Media

This module provides several high-level functions to easily send text, photos, videos, and other files. These functions handle file processing and sending on the appropriate threads.
send_text

Sends a simple text message.

from client_utils import send_text
 
# Send a text message to a user or chat
peer_id = 123456789
send_text(peer_id, "Hello from my plugin!")
 
# Send a reply to a message
send_text(peer_id, "This is a reply.", replyToMsg=9876)

send_photo

Uploads and sends a photo from a local file path.

from client_utils import send_photo
 
peer_id = 123456789
photo_path = "/path/to/your/image.jpg"
 
# Send a photo with a caption
send_photo(peer_id, photo_path, caption="Here is a photo!")
 
# Send a high-quality photo
send_photo(peer_id, photo_path, caption="High quality.", high_quality=True)

send_document

Uploads and sends a generic file/document.

from client_utils import send_document
 
peer_id = 123456789
file_path = "/path/to/your/file.zip"
 
send_document(peer_id, file_path, caption="Here is the zip file.")

send_video

Uploads and sends a video file, automatically extracting metadata like duration and dimensions.

from client_utils import send_video
 
peer_id = 123456789
video_path = "/path/to/your/video.mp4"
 
send_video(peer_id, video_path, caption="Check out this video!")

send_audio

Uploads and sends an audio file as a music track, automatically extracting metadata.

from client_utils import send_audio
 
peer_id = 123456789
audio_path = "/path/to/your/song.mp3"
 
send_audio(peer_id, audio_path, caption="Listen to this!")

All send_* functions also accept any additional keyword arguments (**kwargs) that will be passed along to the underlying SendMessageParams object, such as replyToMsg, scheduleDate, etc.
Editing Messages

You can edit existing messages using the edit_message function.

from client_utils import edit_message
 
# Assume 'message_obj' is a valid MessageObject instance you have obtained
# For example, from a hook or by fetching it from storage.
 
# Edit the text of a message
edit_message(message_obj, text="This is the new, edited text.")
 
# Replace the media in a message (and optionally edit the caption)
new_photo_path = "/path/to/another/image.jpg"
edit_message(message_obj, file_path=new_photo_path, text="Here is a new photo instead.")

The edit_message function can also be used to add a media spoiler by passing with_spoiler=True.
Displaying Bulletins (Bottom Notifications)

Bulletins are small, non-intrusive notifications shown at the bottom of the screen. The BulletinHelper class provides an easy way to show them.

For detailed information and examples on how to use various types of bulletins, please refer to the Bulletin Helper documentation.

from ui.bulletin import BulletinHelper
 
# Example:
BulletinHelper.show_info("This is an informational message.")

Accessing Controllers and Managers

client_utils.py provides convenient getter functions for accessing various core Telegram controllers, managers, and configurations for the currently selected account.

from client_utils import (
    get_account_instance, get_messages_controller, get_contacts_controller,
    get_media_data_controller, get_connections_manager, get_location_controller,
    get_notifications_controller, get_messages_storage, get_send_messages_helper,
    get_file_loader, get_secret_chat_helper, get_download_controller,
    get_notifications_settings, get_notification_center, get_media_controller,
    get_user_config
)
 
# Examples:
account_instance = get_account_instance() # Current AccountInstance
messages_controller = get_messages_controller() # MessagesController
connections_manager = get_connections_manager() # ConnectionsManager
send_helper = get_send_messages_helper() # SendMessagesHelper
user_cfg = get_user_config() # UserConfig
 
# Use these instances to interact with Telegram's internal systems.
if user_cfg.getCurrentUser():
  user_name = user_cfg.getCurrentUser().first_name
 
messages_controller.loadDialogs(0, 50, True) # Example method call

These functions simplify access to key components of the Telegram client.

Markdown Parser

This module provides the ability to parse markdown-formatted text and convert formatting entities to TLRPC objects suitable for the Telegram API.

The markdown_utils.py module allows you to easily convert text with common Markdown V2-style formatting into a plain text string and a list of TLRPC.MessageEntity objects. These entities can then be used with client_utils.send_message or other API methods that accept formatted text.
Core Components

The parser returns a ParsedMessage object, which has two main attributes:

    text: str: The plain text content with all Markdown markers removed.
    entities: Tuple[RawEntity, ...]: A tuple of RawEntity objects, each representing a formatting instruction.

Each RawEntity object contains:

    type: TLEntityType: The type of the entity (e.g., bold, italic, code).
    offset: int: The starting position of the entity in the text (UTF-16 code units).
    length: int: The length of the formatted segment in the text (UTF-16 code units).
    language: Optional[str]: For pre (code block) entities, the specified language.
    url: Optional[str]: For text_link entities, the URL.
    document_id: Optional[int]: For custom_emoji entities, the ID of the custom emoji document.

To convert RawEntity objects into TLRPC.MessageEntity objects suitable for the Telegram API, call the to_tlrpc_object() method on each RawEntity.
Supported Entity Types (TLEntityType)

The parser supports the following entity types:

    BOLD (*bold*)
    ITALIC (_italic_)
    UNDERLINE (__underline__)
    STRIKETHROUGH (~strikethrough~)
    SPOILER (||spoiler||)
    CODE (inline code)
    PRE (code block) - can include an optional language specifier.
    TEXT_LINK ([link text](http://example.com))
    CUSTOM_EMOJI ([alt text](document_id)) - alt text becomes the content of the entity, document_id is the emoji's ID.

Usage Example

This example demonstrates how to parse a Markdown string and send it as a formatted message.

from client_utils import send_message
from markdown_utils import parse_markdown
from android_utils import log
 
params = {
    "peer": 12345678,
    "entities": []
}
 
markdown_input_string = (
    "Markdown entities parsing test:\n\n"
    "~strike~ *bold* __underlined__ _italic_ ||spoiler|| [textlink](https://google.com)\n"
    "This is an inline `code` example.\n"
    "Custom emoji: [😎](5373141891321699086)\n" # Example document_id for a custom emoji
    "\n"
    "Code block 1 (no language specified):\n"
    "```\n"
    "print('Hello, Python!')\n"
    "def greet(name):\n"
    "    return f'Hi, {name}'\n"
    "```\n"
    "\n"
    "Code block 2 (language specified as 'java'):\n"
    "```java\n"
    "public class HelloWorld {\n"
    "    public static void main(String[] args) {\n"
    "        System.out.println(\"Hello world!\");\n"
    "    }\n"
    "}\n"
    "```\n"
    "Nested *bold and _italic_ inside bold*."
)
 
try:
    parsed_message_object = parse_markdown(markdown_input_string)
 
    params["message"] = parsed_message_object.text
    params["entities"] = []
 
    for raw_entity in parsed_message_object.entities:
        tlrpc_entity = raw_entity.to_tlrpc_object()
        params["entities"].append(tlrpc_entity)
 
    log(f"Sending message: '{params['message']}' with {len(params['entities'])} entities.")
    send_message(params)
 
except SyntaxError as e:
    log(f"Markdown parsing error: {e}")
except Exception as e:
    log(f"An unexpected error occurred: {e}")

Important Notes

    UTF-16 Offsets & Lengths: The offset and length in RawEntity (and the resulting TLRPC.MessageEntity) are calculated based on UTF-16 code units, as required by the Telegram API. The parser handles this conversion automatically.
    Error Handling: If the Markdown syntax is incorrect (e.g., unclosed tags), parse_markdown will raise a SyntaxError. It's good practice to wrap the call in a try-except block.
    Nesting: Basic nesting of styles (e.g., bold inside italic) is generally supported, but complex or ambiguous nesting might lead to unexpected results.
    Escaping: Special Markdown characters (*, _, ~, |, `, [, ], \) can be escaped with a backslash (\) if you want them to appear as literal characters. For example, \*not bold\* will render as *not bold*.
    Code Blocks:
        Inline code is surrounded by single backticks (`).
        Fenced code blocks are surrounded by triple backticks ( ).
        An optional language identifier can be placed immediately after the opening triple backticks (e.g., ```python).
    Custom Emoji: The syntax [alt text](document_id) is used. The alt text (e.g., the emoji character itself) becomes the text segment covered by the TLRPC.TL_messageEntityCustomEmoji entity, and document_id is the ID of the custom emoji. You can obtain the emoji ID by sending the emoji to @AdsMarkdownBot on Telegram.

This parser provides a robust way to include rich text formatting in messages sent by your plugins.

Hook Utilities (Reflection)

A set of utility functions for performing Java reflection, allowing you to find classes and access or modify private fields and methods.

The hook_utils.py module provides essential tools for interacting with the underlying Java code of the application via reflection. This is particularly useful for advanced Xposed hooking when you need to access non-public members of a class.

Use with Caution

Reflection is a powerful but fragile technique. It can break if the underlying application code changes. Always include error handling (e.g., try-except blocks) when using these functions and check for None return values.
find_class(class_name: str)

Safely finds and returns a Java class object by its fully qualified name.

    class_name: The full name of the class, including the package (e.g., "org.telegram.ui.ActionBar.ActionBar").
    Returns: A Java Class object if found, otherwise None.

Example

from hook_utils import find_class
 
# Find the ActionBar class
ActionBarClass = find_class("org.telegram.ui.ActionBar.ActionBar")
 
if ActionBarClass:
    self.log(f"Successfully found class: {ActionBarClass.getName()}")
else:
    self.log("Could not find ActionBar class.")

get_private_field(obj: JavaObject, field_name: str)

Accesses and retrieves the value of a private (or public) instance field from a given object. It searches the entire class hierarchy.

    obj: The Java object instance from which to get the field.
    field_name: The name of the field to access.
    Returns: The value of the field if found, otherwise None.

Example

Assuming chatActivity is an instance of org.telegram.ui.ChatActivity.

from hook_utils import get_private_field
 
# Get the value of the private 'chatListView' field from a ChatActivity instance
chat_list_view = get_private_field(chatActivity, "chatListView")
 
if chat_list_view:
    self.log("Successfully accessed chatListView.")

set_private_field(obj: JavaObject, field_name: str, new_value: Any)

Modifies the value of a private (or public) instance field on a given object.

    obj: The Java object instance to modify.
    field_name: The name of the field to modify.
    new_value: The new value to assign to the field.
    Returns: True if the field was set successfully, False otherwise.

Example

from hook_utils import set_private_field
 
# Change the value of a 'verified' field on a user object
user_object = ...
success = set_private_field(user_object, "verified", True)
 
if success:
    self.log("User is now verified!")

get_static_private_field(clazz: JavaClass, field_name: str)

Accesses and retrieves the value of a static private (or public) field from a given class.

    clazz: The Java Class object.
    field_name: The name of the static field.
    Returns: The value of the field if found, otherwise None.

Example

from hook_utils import find_class, get_static_private_field
 
# Get the static 'configLoaded' field from ExteraConfig
ExteraConfigClass = find_class("com.exteragram.messenger.ExteraConfig")
if ExteraConfigClass:
    config_loaded = get_static_private_field(ExteraConfigClass, "configLoaded")
    self.log(f"Config loaded: {config_loaded}")

set_static_private_field(clazz: JavaClass, field_name: str, new_value: Any)

Modifies the value of a static private (or public) field on a given class.

    clazz: The Java Class object.
    field_name: The name of the static field to modify.
    new_value: The new value to assign.
    Returns: True if successful, False otherwise.

Example

from hook_utils import find_class, set_static_private_field
 
# Modify a static configuration flag
BuildVarsClass = find_class("org.telegram.messenger.BuildVars")
if BuildVarsClass:
    success = set_static_private_field(BuildVarsClass, "DEBUG_VERSION", True)
    if success:
        self.log("DEBUG_VERSION has been enabled.")

File Utilities

Learn how to work with files and directories using the file_utils module.

The file_utils module provides a set of helper functions to simplify common file and directory operations within your plugin, such as accessing standard Telegram directories, reading/writing files, and listing directory contents.
Standard Directories

These functions return the absolute paths to various standard directories used by Telegram, making it easy to store and retrieve files in the correct locations.

from file_utils import (
    get_plugins_dir, get_cache_dir, get_files_dir, get_images_dir,
    get_videos_dir, get_audios_dir, get_documents_dir
)
 
# Get the path to the directory where plugins are stored
plugins_path = get_plugins_dir()
 
# Get the path to Telegram's main cache directory
cache_path = get_cache_dir()
 
# Get paths to media-specific directories
files_path = get_files_dir()
images_path = get_images_dir()
videos_path = get_videos_dir()
audios_path = get_audios_dir()
documents_path = get_documents_dir()

Directory Operations
ensure_dir_exists

Ensures that a directory exists. If it doesn't, it will be created, including any necessary parent directories.

from file_utils import ensure_dir_exists, get_plugins_dir
import os
 
# Ensure a dedicated data directory for your plugin exists
my_plugin_data_dir = os.path.join(get_plugins_dir(), "my_plugin_data")
ensure_dir_exists(my_plugin_data_dir)

list_dir

Lists the contents of a directory with options for recursion, filtering by type (files/dirs), and file extension.

from file_utils import list_dir, get_images_dir, get_cache_dir
 
# List all JPG and PNG files in the Telegram Images directory (non-recursively)
image_files = list_dir(
    path=get_images_dir(),
    extensions=[".jpg", ".png"]
)
log(f"Found {len(image_files)} images.")
 
# Recursively list all subdirectories within the cache
cache_subdirs = list_dir(
    path=get_cache_dir(),
    recursive=True,
    include_files=False,
    include_dirs=True
)
log(f"Found {len(cache_subdirs)} subdirectories in the cache.")

File Operations

These functions provide simple wrappers for reading, writing, and deleting files.
write_file

Writes a string to a file, overwriting it if it already exists.

from file_utils import write_file, get_plugins_dir
import os
 
# Example: Save some data to a file
data_to_save = "Hello, World!"
my_data_path = os.path.join(get_plugins_dir(), "my_plugin_data", "data.log")
write_file(my_data_path, data_to_save)

read_file

Reads the entire content of a file into a string.

from file_utils import read_file, get_plugins_dir
import os
 
# Example: Read a config file from your plugin's data folder
my_config_path = os.path.join(get_plugins_dir(), "my_plugin_data", "config.txt")
config_content = read_file(my_config_path)
 
if config_content:
    log(f"Config loaded: {config_content}")

delete_file

Deletes a file from the filesystem.

from file_utils import delete_file
 
file_to_delete = "/path/to/your/temp_file.tmp"
was_deleted = delete_file(file_to_delete)
 
if was_deleted:
    log("Temporary file deleted successfully.")

Alert Dialog Builder

A Pythonic wrapper for creating and managing Telegram-style AlertDialogs.

The AlertDialogBuilder class, found in alert.py, provides a convenient way to construct and display various types of alert dialogs within your plugins. It wraps org.telegram.ui.ActionBar.AlertDialog.Builder and simplifies its usage from Python.
Basic Usage

from ui.alert import AlertDialogBuilder
from client_utils import get_last_fragment
from android_utils import log
 
# Get current activity (context)
current_fragment = get_last_fragment()
if not current_fragment:
    log("Cannot show dialog, no current fragment.")
    # return or handle error
 
activity = current_fragment.getParentActivity()
if not activity:
    log("Cannot show dialog, no parent activity.")
    # return or handle error
 
# Create a simple message dialog
builder = AlertDialogBuilder(activity) # Default is ALERT_TYPE_MESSAGE
builder.set_title("My Plugin Alert")
builder.set_message("This is an important message from the plugin.")
 
# Add buttons
def on_positive_click(bld: AlertDialogBuilder, which: int):
    log("Positive button clicked!")
    bld.dismiss()
 
def on_negative_click(bld: AlertDialogBuilder, which: int):
    log("Negative button clicked!")
    bld.dismiss()
 
builder.set_positive_button("OK", on_positive_click)
builder.set_negative_button("Cancel", on_negative_click)
 
builder.show()

Dialog Types

AlertDialogBuilder supports different styles of dialogs, controlled by the progress_style parameter in its constructor:

    AlertDialogBuilder.ALERT_TYPE_MESSAGE (default): Standard message dialog.
    AlertDialogBuilder.ALERT_TYPE_LOADING: Dialog with a determinate horizontal progress bar. Use builder.set_progress(value) to update.
    AlertDialogBuilder.ALERT_TYPE_SPINNER: Dialog with an indeterminate spinner, often used for loading states.

# Loading dialog example
loading_builder = AlertDialogBuilder(activity, AlertDialogBuilder.ALERT_TYPE_SPINNER)
loading_builder.set_title("Loading Data...")
loading_builder.set_message("Please wait while data is being fetched.")
loading_builder.set_cancelable(False) # Prevent dismissal by back press or touch outside
loading_builder.show()
 
# Later, when loading is done:
# loading_builder.dismiss()

Key Methods
Initialization

    AlertDialogBuilder(context: Context, progress_style: int = ALERT_TYPE_MESSAGE, resources_provider: Optional[Theme.ResourcesProvider] = None): Constructor.

Content

    set_title(title: str): Sets the dialog title.
    set_message(message: str): Sets the main message content.
    set_message_text_view_clickable(clickable: bool): Makes the message text clickable (e.g., for links).
    set_view(view: View, height: int = -2): Sets a custom Android View as the dialog's content.
    set_items(items: List[str], listener: Optional[Callable[['AlertDialogBuilder', int], None]] = None, icons: Optional[List[int]] = None): Displays a list of items. The listener is called with the dialog builder instance and the index of the clicked item.

Buttons

    set_positive_button(text: str, listener: Optional[Callable[['AlertDialogBuilder', int], None]] = None)
    set_negative_button(text: str, listener: Optional[Callable[['AlertDialogBuilder', int], None]] = None)
    set_neutral_button(text: str, listener: Optional[Callable[['AlertDialogBuilder', int], None]] = None)
        Listeners receive the AlertDialogBuilder instance and a button identifier (AlertDialogBuilder.BUTTON_POSITIVE, etc.).
    make_button_red(button_type: int): Styles a button's text (e.g., AlertDialogBuilder.BUTTON_NEGATIVE) with red color (using Theme.key_text_RedBold).

Listeners

    set_on_back_button_listener(listener: Optional[Callable[['AlertDialogBuilder', int], None]] = None): For back button presses while the dialog is shown.
    set_on_dismiss_listener(listener: Optional[Callable[['AlertDialogBuilder'], None]] = None): Called when the dialog is dismissed for any reason.
    set_on_cancel_listener(listener: Optional[Callable[['AlertDialogBuilder'], None]] = None): Called when the dialog is cancelled (e.g., by back press or touch outside, if cancelable).

Appearance & Behavior

    set_top_image(res_id: int, background_color: int)
    set_top_drawable(drawable: Drawable, background_color: int)
    set_top_animation(res_id: int, size: int, auto_repeat: bool, background_color: int, layer_colors: Optional[Dict[str, int]] = None)
    set_dim_enabled(enabled: bool): Enables/disables dimming of the background.
    set_dialog_button_color_key(theme_key: int): Sets a theme color key for buttons.
    set_blurred_background(blur: bool, blur_behind_if_possible: bool = True): Attempts to apply a blurred background.
    set_cancelable(cancelable: bool): Sets if the dialog can be dismissed by tapping outside or pressing back. Best called after create() or show().
    set_canceled_on_touch_outside(cancel: bool): Sets if tapping outside dismisses. Best called after create() or show().

Lifecycle

    create() -> 'AlertDialogBuilder': Creates the dialog but doesn't show it.
    show() -> 'AlertDialogBuilder': Creates (if not already) and shows the dialog.
    dismiss(): Dismisses the dialog if it's showing.
    get_dialog() -> Optional[AlertDialog]: Returns the underlying Java AlertDialog instance.
    get_button(button_type: int) -> Optional[View]: Gets a button view from the dialog (e.g., for custom styling). Call after create() or show().

Progress

    set_progress(progress: int): Sets the progress for ALERT_TYPE_LOADING dialogs (0-100).

Example: Dialog with Items

from ui.alert import AlertDialogBuilder
from client_utils import get_last_fragment
from android_utils import log
 
def on_item_click(bld: AlertDialogBuilder, which: int):
    items_list = ["Option A", "Option B", "Option C"]
    log(f"Item '{items_list[which]}' (index {which}) selected.")
    bld.dismiss()
 
item_builder = AlertDialogBuilder(activity)
item_builder.set_title("Choose an Option")
item_builder.set_items(
    ["Option A", "Option B", "Option C"],
    on_item_click
)
item_builder.set_negative_button("Cancel", lambda b, w: b.dismiss())
item_builder.show()

Important Notes

    Context: Always provide a valid Android Context (usually an Activity) to the constructor. get_last_fragment().getParentActivity() is a common way to get this.
    Listeners: The listener callables you provide will receive the Python AlertDialogBuilder instance as their first argument, allowing you to interact with the dialog (e.g., bld.dismiss()) from within the callback.
    Thread Safety: Dialog manipulation (creating, showing, dismissing, updating content) should generally happen on the Android UI thread. Use android_utils.run_on_ui_thread if you're performing these actions from a background thread.
    Error Handling: The proxy listeners in alert.py include basic try-except blocks to log errors occurring within your Python callbacks, preventing crashes.

Bulletin Helper

Easily display various types of bottom-screen notifications (Bulletins) in your plugins.

The BulletinHelper class, found in bulletin.py, provides a set of static methods to conveniently show Telegram's "Bulletin" notifications. Bulletins are small, non-intrusive messages that typically appear at the bottom of the screen and dismiss automatically.
Basic Usage

Most BulletinHelper methods are class methods and can be called directly. They often accept an optional fragment argument; if not provided, the helper tries to use the currently active fragment or a global context.

from ui.bulletin import BulletinHelper
from client_utils import get_last_fragment # Optional, for explicit fragment passing
from org.telegram.messenger import R as R_tg # For Telegram's R.raw Lottie animations
 
# Get current fragment (optional)
current_fragment = get_last_fragment()
 
# Show a simple informational bulletin
BulletinHelper.show_info("This is some information.", current_fragment)
 
# Show an error bulletin
BulletinHelper.show_error("An error occurred processing your request.", current_fragment)
 
# Show a success bulletin
BulletinHelper.show_success("Action completed successfully!", current_fragment)

UI Thread

All BulletinHelper.show_... methods automatically ensure that the bulletin is shown on the Android UI thread, so you don't need to wrap these calls in run_on_ui_thread yourself.
Bulletin Types and Methods

BulletinHelper wraps common functionalities of org.telegram.ui.Components.BulletinFactory.
Standard Bulletins

    BulletinHelper.show_info(message: str, fragment: Optional[BaseFragment] = None)
        Shows a bulletin with a default info icon (e.g., R.raw.info).
    BulletinHelper.show_error(message: str, fragment: Optional[BaseFragment] = None)
        Shows a bulletin with a default error/alert icon.
    BulletinHelper.show_success(message: str, fragment: Optional[BaseFragment] = None)
        Shows a bulletin with a default success/check icon.

Custom Simple Bulletins
BulletinHelper.show_simple(text: str, icon_res_id: int, fragment: Optional[BaseFragment] = None)

    Shows a single-line bulletin with a custom Lottie animation icon.
    icon_res_id: A Lottie animation resource ID (e.g., R_tg.raw.some_animation).

BulletinHelper.show_simple("Processing...", R_tg.raw.timer, current_fragment)

BulletinHelper.show_two_line(title: str, subtitle: str, icon_res_id: int, fragment: Optional[BaseFragment] = None)

    Shows a two-line bulletin with a custom icon, title, and subtitle.

    BulletinHelper.show_two_line("Download Complete", "File saved to gallery.", R_tg.raw.ic_download_done, current_fragment)

Bulletins with Actions

BulletinHelper.show_with_button(text: str, icon_res_id: int, button_text: str, on_click: Optional[Callable[[], None]], fragment: Optional[BaseFragment] = None, duration: int = BulletinHelper.DURATION_PROLONG)

    Shows a bulletin with an icon, text, and a clickable button.
    on_click: A callable to execute when the button is pressed.
    duration: How long the bulletin stays visible (e.g., BulletinHelper.DURATION_SHORT, DURATION_LONG, DURATION_PROLONG).

def open_settings_action():
    # Code to open some settings page
    print("Settings button clicked!")
 
BulletinHelper.show_with_button(
    "Plugin settings updated.",
    R_tg.raw.info,
    "Configure",
    open_settings_action,
    current_fragment
)

BulletinHelper.show_undo(text: str, on_undo: Callable[[], None], on_action: Optional[Callable[[], None]] = None, subtitle: Optional[str] = None, fragment: Optional[BaseFragment] = None)

    Shows an "Undo"-style bulletin.
    on_undo: Called if the "Undo" button is pressed.
    on_action: Called after a delay if "Undo" is not pressed (e.g., to commit an action).

    def perform_delete():
        print("Item permanently deleted.")
     
    def undo_delete():
        print("Delete operation undone.")
     
    BulletinHelper.show_undo(
        "Item moved to trash.",
        on_undo=undo_delete,
        on_action=perform_delete,
        fragment=current_fragment
    )

Contextual Bulletins (Predefined)
BulletinHelper.show_copied_to_clipboard(message: Optional[str] = None, fragment: Optional[BaseFragment] = None)

    Shows "Text copied to clipboard" or a custom message.

BulletinHelper.show_link_copied(is_private_link_info: bool = False, fragment: Optional[BaseFragment] = None)

    Shows "Link copied" bulletin, with a variant for private link info.

BulletinHelper.show_file_saved_to_gallery(is_video: bool = False, amount: int = 1, fragment: Optional[BaseFragment] = None)

    Shows "Photo/Video saved to gallery" (or plural versions).

BulletinHelper.show_file_saved_to_downloads(file_type_enum_name: str = "UNKNOWN", amount: int = 1, fragment: Optional[BaseFragment] = None)

    Shows "File saved to downloads" or similar, based on BulletinFactory.FileType.
    file_type_enum_name: String name of the enum from BulletinFactory.FileType (e.g., "PHOTO_TO_DOWNLOADS", "GIF").

    BulletinHelper.show_file_saved_to_downloads("MUSIC", amount=3, fragment=current_fragment)

Durations

The BulletinHelper class defines constants for common durations:

    BulletinHelper.DURATION_SHORT (1500 ms)
    BulletinHelper.DURATION_LONG (2750 ms)
    BulletinHelper.DURATION_PROLONG (5000 ms)

These can be used with methods like show_with_button.
Finding Lottie Animations (R.raw...)
Lottie animations used for bulletin icons are typically stored as raw resources in Telegram's codebase. You can explore Telegram's source (specifically TMessagesProj/src/main/res/raw/) to find available animations (e.g., info.json, success.json, delete.json). In Python, these are accessed via org.telegram.messenger.R.raw.animation_name (e.g., R_tg.raw.info).

Available Libraries

A list of pre-installed Python libraries available in the plugin environment.

The plugin environment comes with a specific version of Python and a set of pre-installed third-party libraries that you can use in your plugins without any extra setup.
Python Version

    Python: 3.11

Pre-installed Pip Packages

You can directly import and use the following libraries in your plugin code:

    beautifulsoup4: A library for pulling data out of HTML and XML files. Useful for web scraping.
    debugpy: The official debugger for Python from Microsoft, enabling remote debugging capabilities (used by the Dev Server).
    lxml: A powerful and Pythonic library for processing XML and HTML.
    packaging: Core utilities for Python packages.
    pillow: The friendly PIL fork (Python Imaging Library). Useful for image manipulation.
    requests: A simple, yet elegant, HTTP library. Essential for making web requests.
    PyYAML: A YAML parser and emitter for Python.

Using Other Libraries
If your plugin requires a library that is not on this list, you must either implement the needed functionality yourself or find an alternative available in Java. The plugin system does not support installing additional packages at runtime.
