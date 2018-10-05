#!/usr/bin/env python3

from playback.internet_radio import internetRadio

import gi

gi.require_version('MatePanelApplet', '4.0')
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gio, GLib
from gi.repository import MatePanelApplet

from itertools import chain
from collections import deque


RADIO_SCHEMA = 'org.mate.panel.applet.InternetRadio'
RADIO_LIST_KEY = 'radio-stations'


class Preferences:

    def __init__(self):
        self.stations = deque(maxlen=3)
        self.settings = Gio.Settings(RADIO_SCHEMA)

        self.preference_builder = Gtk.Builder()
        # need to set full path here otherwise the resource file will not be found when autorunnng the applet
        self.preference_builder.add_from_file("/home/adrian/PythonProjects/internet_radio_applet/preferences.ui")

        dialog = self.preference_builder.get_object("player_preferences_dialog")
        # dialog.connect("delete-event", self.on_done_button_clicked)

        done_button = self.preference_builder.get_object("done_button")
        done_button.connect("clicked", self.on_done_button_clicked)

        set_stream_button = self.preference_builder.get_object("set_stream_button")
        set_stream_button.connect("clicked", self.on_set_stream_button_clicked)
        self.load_preferences()

    def load_preferences(self):
        settings_list = self.settings.get_value(RADIO_LIST_KEY).unpack()
        it = iter(settings_list)
        self.stations.extend(internetRadio.StationDef(name, url) for name, url in zip(it, it))

    def save_preferences(self):
        settings_list = list(chain.from_iterable(self.stations))
        self.settings.set_value(RADIO_LIST_KEY, GLib.Variant('as', settings_list))

    def on_done_button_clicked(self, button):
        self.hide()

    def on_set_stream_button_clicked(self, button):
        station_name = self.preference_builder.get_object("name_entry").get_text()
        stream_url = self.preference_builder.get_object("stream_url_entry").get_text()
        if not station_name or not stream_url:
            return

        station = internetRadio.StationDef(station_name, stream_url)
        internetRadio.play_station(station)
        self.stations.append(station)
        self.save_preferences()

    def show(self):
        recent_station = self.stations[-1]
        self.preference_builder.get_object("name_entry").set_text(recent_station.station_name)
        self.preference_builder.get_object("stream_url_entry").set_text(recent_station.stream_url)
        self.preference_builder.get_object("player_preferences_dialog").show_all()

    def hide(self):
        self.preference_builder.get_object("player_preferences_dialog").hide()


class PlayerApplet:
    def __init__(self, mate_applet: MatePanelApplet):
        self.applet = mate_applet
        self.menu = None
        self.button = None

    def set_song_title(self, title: str):
        self.button.set_tooltip_text(title)


class DialogWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="About")

        self.set_border_width(6)
        label = Gtk.Label('This is a radio streamer')
        button = Gtk.Button("Close")
        button.connect("clicked", lambda a: self.destroy())

        self.add(button)


class Menu:

    def __init__(self):
        self.preference = Preferences()
        self.player_menu_verbs = [
            ("PlayerPreferences", "document-properties", "_Preferences",
             None, None, self.display_preferences_dialog),
            ("PlayerHelp", "help-browser", "_Help",
             None, None, self.display_help_dialog),
            ("PlayerAbout", "help-about", "_About",
             None, None, self.display_about_dialog),
        ]
        self.action_group = Gtk.ActionGroup("Applet actions")
        self.action_group.add_actions(self.player_menu_verbs)

    def setup_menu(self, applet):
        # need to set full resource file path here
        applet.setup_menu_from_file("/home/adrian/PythonProjects/internet_radio_applet/menu.xml", self.action_group)


    def display_preferences_dialog(self, action):
        self.preference.show()

    def display_help_dialog(self, action):
        print("Help")

    def display_about_dialog(self, action):
        DialogWindow().show_all()


def on_play_button_clicked(button, player_applet):

    if internetRadio.is_playing():
        icon = Gio.ThemedIcon(name="media-playback-start")
        image = Gtk.Image.new_from_gicon(icon, 3)
        button.set_image(image)
        internetRadio.stop()
    else:
        icon = Gio.ThemedIcon(name="media-playback-stop")
        image = Gtk.Image.new_from_gicon(icon, 3)
        button.set_image(image)
        last_station = player_applet.menu.preference.stations[-1]
        internetRadio.play_station(last_station)


def applet_fill(player_applet):
    player_applet.menu = Menu()
    player_applet.menu.setup_menu(player_applet.applet)

    # you can use this path with gio/gsettings
    settings_path = player_applet.applet.get_preferences_path()

    button = Gtk.Button.new_from_icon_name("media-playback-start", 3)
    button.set_tooltip_text("Play")
    button.connect("clicked", on_play_button_clicked, player_applet)

    player_applet.button = button
    internetRadio.set_song_title_callback(player_applet.set_song_title)
    player_applet.applet.add(button)
    player_applet.applet.show_all()


def applet_factory(applet: MatePanelApplet, iid, data):
    if iid != "InternetRadio":
       return False
    print('---Starting InternetRadio applet---\n')
    player_applet = PlayerApplet(applet)
    applet_fill(player_applet)
    return True



MatePanelApplet.Applet.factory_main("InternetRadioAppletFactory", True,
                                    MatePanelApplet.Applet.__gtype__,
                                    applet_factory, None)
