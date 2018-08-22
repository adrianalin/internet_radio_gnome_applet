#!/usr/bin/env python

from playback.internet_radio import internetRadio

import gi

gi.require_version('MatePanelApplet', '4.0')
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gio
from gi.repository import MatePanelApplet


class PlayerApplet:
    def __init__(self, mate_applet):
        self.applet = mate_applet
        self.preference_builder = None


class DialogWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="About")

        self.set_border_width(6)
        label = Gtk.Label('This is a radio streamer')
        button = Gtk.Button("Close")
        button.connect("clicked", lambda a: self.destroy())

        self.add(button)


def on_done_button_clicked(button, player_applet: PlayerApplet):
    player_applet.preference_builder.get_object("player_preferences_dialog").close()


def on_set_stream_button_clicked(button, player_applet: PlayerApplet):
    station_name = player_applet.preference_builder.get_object("name_entry").get_text()
    stream_url = player_applet.preference_builder.get_object("stream_url_entry").get_text()
    station = internetRadio.StationDef(station_name, stream_url)
    internetRadio.play_station(station)


def display_preferences_dialog(action, player_applet: PlayerApplet):
    if player_applet.preference_builder is not None:
        player_applet.preference_builder.get_object("player_preferences_dialog").show_all()
        return

    builder = Gtk.Builder()
    builder.add_from_file("preferences.ui")

    done_button = builder.get_object("done_button")
    done_button.connect("clicked", on_done_button_clicked, player_applet)

    set_stream_button = builder.get_object("set_stream_button")
    set_stream_button.connect("clicked", on_set_stream_button_clicked, player_applet)

    window = builder.get_object("player_preferences_dialog")
    window.show_all()
    player_applet.preference_builder = builder


def display_help_dialog(action, applet):
    print("Help")


def display_about_dialog(action, applet):
    DialogWindow().show_all()


player_menu_verbs = [
    ("PlayerPreferences", "document-properties", "_Preferences",
     None, None, display_preferences_dialog),
    ("PlayerHelp", "help-browser", "_Help",
    None, None, display_help_dialog),
    ("PlayerAbout", "help-about", "_About",
     None, None, display_about_dialog),
]


def on_play_button_clicked(button):

    if internetRadio.is_playing():
        icon = Gio.ThemedIcon(name="media-playback-start")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        button.set_image(image)
        internetRadio.stop()
    else:
        icon = Gio.ThemedIcon(name="media-playback-stop")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        button.set_image(image)
        internetRadio.play_station(0)


def applet_fill(player_applet):
    action_group = Gtk.ActionGroup("Applet actions")
    action_group.add_actions(player_menu_verbs, player_applet)
    player_applet.applet.setup_menu_from_file("menu.xml", action_group)

    settings_path = player_applet.applet.get_preferences_path()

    button = Gtk.Button()
    button.connect("clicked", on_play_button_clicked)
    icon = Gio.ThemedIcon(name="media-playback-start")
    image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON + 0.9)
    button.set_image(image)

    player_applet.applet.add(button)
    player_applet.applet.show_all()


def applet_factory(applet, iid, data):
    if iid != "InternetRadio":
       return False
    player_applet = PlayerApplet(applet)
    applet_fill(player_applet)
    return True



MatePanelApplet.Applet.factory_main("InternetRadioAppletFactory", True,
                                    MatePanelApplet.Applet.__gtype__,
                                    applet_factory, None)
