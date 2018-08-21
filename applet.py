#!/usr/bin/env python

from playback.internet_radio import internetRadio

import gi

gi.require_version('MatePanelApplet', '4.0')
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from gi.repository import MatePanelApplet

class DialogWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="About")

        self.set_border_width(6)
        label = Gtk.Label('This is a radio streamer')
        button = Gtk.Button("Close")
        button.connect("clicked", lambda a: self.destroy())

        self.add(button)



def display_preferences_dialog(action, applet):
    print("Preferences")


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


def applet_fill(applet):
    action_group = Gtk.ActionGroup("Applet actions")
    action_group.add_actions(player_menu_verbs, applet)
    applet.setup_menu_from_file("menu.xml", action_group)

    settings_path = applet.get_preferences_path()

    button = Gtk.Button("Play")
    button.connect("clicked", on_play_button_clicked)
    applet.add(button)


    applet.show_all()


def applet_factory(applet, iid, data):
    if iid != "TestApplet":
       return False
    applet_fill(applet)
    return True



MatePanelApplet.Applet.factory_main("TestAppletFactory", True,
                                    MatePanelApplet.Applet.__gtype__,
                                    applet_factory, None)
