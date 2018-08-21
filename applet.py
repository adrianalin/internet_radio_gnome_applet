#!/usr/bin/env python

from playback.internet_radio import internetRadio

import gi

gi.require_version('MatePanelApplet', '4.0')
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from gi.repository import MatePanelApplet


class PlayerApplet:
    def __init__(self, mate_applet):
        self.applet = mate_applet
        self.preference_window = None


class DialogWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="About")

        self.set_border_width(6)
        label = Gtk.Label('This is a radio streamer')
        button = Gtk.Button("Close")
        button.connect("clicked", lambda a: self.destroy())

        self.add(button)


def on_done_button_clicked(button, player_applet: PlayerApplet):
    player_applet.preference_window.destroy()
    player_applet.preference_window = None
    print('on button clicked')


def display_preferences_dialog(action, player_applet: PlayerApplet):
    print("Preferences")
    if player_applet.preference_window is not None:
        player_applet.preference_window.show_all()
        return

    builder = Gtk.Builder()
    builder.add_from_file("preferences.ui")
    button = builder.get_object("done_button")
    button.connect("clicked", on_done_button_clicked, player_applet)
    window = builder.get_object("player_preferences_dialog")
    window.show_all()
    player_applet.preference_window = window

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


def on_play_button_clicked(widget):

    if internetRadio.is_playing():
        internetRadio.stop()
    else:
        internetRadio.play_station(0)


def applet_fill(player_applet):
    action_group = Gtk.ActionGroup("Applet actions")
    action_group.add_actions(player_menu_verbs, player_applet)
    player_applet.applet.setup_menu_from_file("menu.xml", action_group)

    settings_path = player_applet.applet.get_preferences_path()

    button = Gtk.Button("Play")
    button.connect("clicked", on_play_button_clicked)
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
