#!/usr/bin/env python
# -*- coding: utf-8 -*-

# CD Tray: Play your Audio CDs from systray
# (c) 2012-2013 Alfonso Saavedra "Son Link"
# http://sonlinkblog.blogspot.com/p/cd-tray.html
# Under GPLv3 License

import gobject, gtk
import gettext, pynotify
import gst
import json

from urllib import urlopen
from os import getcwd
from os.path import isfile
from commands import getoutput
from ctypes import CDLL

t = gettext.translation('jrtp', 'lang')
_ = t.ugettext

class JAMTRAY():
	"""
	Init the program
	"""

	def __init__(self):
		self.actual_radioid = 0

		self.status = -1
		# -1 -> No hace nada, 0 Stop, 1 play, 2 pause
		self.shownotify = 1
		self.track_name = None

		self.statusicon = gtk.StatusIcon()

		self.statusicon.set_from_file('jrtp.svg')
		self.statusicon.connect("popup-menu", self.show_menu)
		self.statusicon.connect('activate', self.play)

		self.menu= gtk.Menu()

		# Radio selection
		self.tracks_menu = gtk.Menu()
		self.importm = gtk.MenuItem(label=_('Radios'))
		self.importm.set_submenu(self.tracks_menu)
		self.menu.append(self.importm)

		self.stop_button = gtk.ImageMenuItem(stock_id=gtk.STOCK_MEDIA_STOP)
		self.stop_button.connect('activate', self.stop)
		self.menu.append(self.stop_button)
		self.stop_button.set_sensitive(False)

		sep = gtk.SeparatorMenuItem()
		self.menu.append(sep)

		about = gtk.ImageMenuItem(stock_id=gtk.STOCK_ABOUT)
		about.connect('activate', self.about)
		self.menu.append(about)

		salir = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
		salir.connect('activate', self.quit)
		self.menu.append(salir)

		if not isfile('radioslist'):
			radios = self.getData('radios/?format=json&order=dispname&limit=all')
			if radios:
				f = open('radioslist', 'w')

				for radio in radios:
					f.write('%s|%s\n' % (radio['id'], radio['dispname']))
				f.close()
			else:
				exit(-1)

		self.update_jt_menu()
		self.player = gst.element_factory_make("playbin2", "player")
		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.connect("message::error", self.bus_message_error)
		bus.connect("message::tag", self.bus_message_tag)

	def show_menu(self, icon, button, time):
		"""
		Show the menu
		"""
		self.menu.show_all()
		self.menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.statusicon)

	def play(self, *args):
		"""
		Change the state to play or pause
		"""
		if self.status == 1:
			self.player.set_state(gst.STATE_PAUSED)
			self.status = 2

		elif self.status == 2 or self.status == 0:
			self.player.set_state(gst.STATE_PLAYING)
			self.status = 1

	def stop(self, *args):
		"""
		Stop
		"""
		try:
			self.player.set_state(gst.STATE_NULL)
		except:
			pass

		self.status = 0

	def bus_message_tag(self, bus, message):

		file_tags = {}

		taglist = message.parse_tag()

		for key in taglist.keys():
			try:
				if key == 'title':
					self.update_info(taglist['title'])
			except:
				return False

	def bus_message_error(self, bus, message):
		e, d = message.parse_error()
		self.statusicon.set_tooltip_text("ERROR: "+ str(e))

	def update_info(self, track_name):
		"""
		Show info on icon tooltip
		"""

		info_text = _('Playing %s' % track_name)

		self.statusicon.set_tooltip_text(info_text)

		# Send notify
		if self.shownotify == 1:
			pynotify.init('Jamendo Radio Tray Player')
			img = '%s/jrtp.svg' % getcwd()
			notify = pynotify.Notification('Jamendo Radio Tray Player', _('Playing %s') % track_name, img)
			notify.show()

	def update_jt_menu(self):

		self.tracks_menu = gtk.Menu()
		self.importm.set_submenu(self.tracks_menu)
		radios = open('radioslist')
		for radio in radios.readlines():
			radio = radio.split('|')
			menu_items = gtk.MenuItem(radio[1].rstrip())
			self.tracks_menu.append(menu_items)
			menu_items.connect("activate", self.changeRadio, radio[0])
			if radio[0] == self.actual_radioid:
				menu_items.set_sensitive(False)

	def changeRadio(self, widget, radioid):
		data = self.getData('radios/stream?format=json&id=%s' % radioid)[0]
		self.actual_radioid = radioid
		self.update_jt_menu()
		self.player.set_state(gst.STATE_NULL)
		self.player.set_property("uri", data['stream'])
		self.player.set_state(gst.STATE_PLAYING)
		self.status = 1
		self.stop_button.set_sensitive(True)

	def getData(self, params):
		try:
			response = urlopen("http://api.jamendo.com/v3.0/%s&client_id=455c95a8" % params)
			if response.getcode() == 200:
				data = json.loads(response.read())
				if data['headers']['code'] == 0:
					return data['results']
				else:
					return False
			else:
				return False

		except IOError:
			return False

	def about(self, w):
		# The about dialog

		info = gtk.AboutDialog()
		info.set_name('Jamendo Radio Tray Player')
		logo = gtk.gdk.pixbuf_new_from_file('jrtp.svg')
		info.set_logo(logo)
		info.set_version('Beta 1 (r3)')
		f = open('COPYING', 'r')
		info.set_license(f.read())
		f.close()
		info.set_comments(_('Play Jamendo radios on yor systray'))
		info.set_website('https://github.com/son-link/JamendoRadioTrayPlayer')
		info.set_website_label(_("Proyect page"))
		info.set_translator_credits('English: Alfonso Saavedra "Son Link"')
		def close(w, res):
			w.hide()
		info.connect("response", close)
		info.run()

	def quit(self, w):
		"""
		Exit from program
		"""
		self.stop()
		exit()

if __name__ == '__main__':
	process = getoutput('ps -A')

	libc6 = 'libc.so.6'

	if not 'jamendoradio' in process:
		libc = CDLL(libc6)
		libc.prctl (15, 'jamendoradio', 0, 0, 0)
		JAMTRAY()
		gtk.main()

	else:
		warning = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_OK, message_format=_("Error!"))
		warning.set_title('Jamendo Radio Tray Player')
		warning.format_secondary_text(_("There is another Jamendo Radio Tray Player instance running. If the program didn't close correctly, kill jamendoradio process"))
		def close(w, res):
			w.destroy()
			exit(1)
		warning.connect("response", close)
		warning.run()
