#!/usr/bin/python3

import os
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
import redis
import numpy as np


class MouseClient():

	def __init__(self):
		super().__init__()
		self.state = [0, 0, 0, 0]
		self.bus = dbus.SystemBus()
		self.btkservice = self.bus.get_object(
			'org.thanhle.btkbservice', '/org/thanhle/btkbservice')
		self.iface = dbus.Interface(self.btkservice, 'org.thanhle.btkbservice')
	def send_current(self):
		try:
			self.iface.send_mouse(0, bytes(self.state))
		except OSError as err:
			error(err)
	
	def run(self):
		self.input_stream = "cursor_2d_commands"
		self.discrete_input_stream = "decoded_gestures"
		self.last_input_entry_seen = "$"
		self.screen_height = 1080
		self.r = redis.Redis('192.168.150.2')

		last_input_entries = self.r.xrevrange(self.input_stream, count=1)
		self.last_input_entry_seen = (
			last_input_entries[0][0] if len(last_input_entries) > 0 else "0-0"
		)

		last_discrete_input_entries = self.r.xrevrange(
			self.discrete_input_stream, count=1
		)
		last_discrete_input_entry_seen = (
			last_discrete_input_entries[0][0]
			if len(last_discrete_input_entries) > 0
			else "0-0"
		)
	
		while True:
			
			read_result = self.r.xread(
                    {
                        self.input_stream: self.last_input_entry_seen,
                        self.discrete_input_stream: last_discrete_input_entry_seen,
                    }
                )

			read_result_dict = {
				stream.decode(): entries for stream, entries in read_result
			}

			for input_entry_id, input_entry_dict in read_result_dict.get(
				self.input_stream, []
			):
				# Save that we've now seen this entry.
				self.last_input_entry_seen = input_entry_id

				# Input command received.
				distance_bgcoordinates = np.frombuffer(
					input_entry_dict[b"data"], dtype=np.float32
				)
				x_bgcoordinates = distance_bgcoordinates[0]
				y_bgcoordinates = distance_bgcoordinates[1]

				self.state[1] = x_bgcoordinates / self.screen_height
				self.state[2] = y_bgcoordinates / self.screen_height

				self.send_current()
				


if __name__ == "__main__":
	node = MouseClient()
	node.run()
