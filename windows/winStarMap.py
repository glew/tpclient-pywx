"""\
This module contains the StarMap window. This window displays a view of the
universe.
"""
# Python imports
import os
from math import *

# wxPython imports
from wxPython.wx import *
from extra.wxFloatCanvas.NavCanvas import NavCanvas
from extra.wxFloatCanvas.FloatCanvas import EVT_FC_ENTER_OBJECT, EVT_FC_LEAVE_OBJECT
from extra.wxFloatCanvas.FloatCanvas import Text
from extra.wxFloatCanvas.CircleNoSmall import CircleNoSmall

from netlib.objects.ObjectExtra.StarSystem import StarSystem
from netlib.objects.ObjectExtra.Fleet import Fleet

from winBase import *
from utils import *

#wxRED = wxColor()
wxYELLOW = wxColor(0xD6, 0xDC, 0x2A)

POINT = 4

sysPLAIN = 1
sysOWNER = 2
sysHAB = 3
sysMIN = 4

# Shows the main map of the universe.
class winStarMap(winBase):
	title = "StarMAP, The Known Universe"

	def __init__(self, application, parent, pos=wxDefaultPosition, size=wxDefaultSize, style=wxDEFAULT_FRAME_STYLE):
		winBase.__init__(self, application, parent, pos, size, style)

		self.application = application

		self.CreateStatusBar()
		self.SetStatusText("")

		self.Canvas = NavCanvas(self, size=wxSize(500,500), Debug = 1, BackgroundColor = "BLACK")
		self.Canvas.ZoomToBB()

		EVT_CACHE_UPDATE(self, self.Update)

	def Update(self, evt):
		try:
			application = self.application
			C = self.Create
			
			for object in application.cache.values():
				if isinstance(object, StarSystem):
					s = round(object.size/(1000*100))
					x = round(object.pos[0]/(1000*1000))
					y = round(object.pos[1]/(1000*1000))

					# Draw an orbit
					so = round(s * 1.25)

					if len(object.contains) > 0:
						C(object, CircleNoSmall(x,y,so,10,LineWidth=1,LineColor="White",FillColor="Black"))
					else:	
						C(object, CircleNoSmall(x,y,so,10,LineWidth=1,LineColor="Black",FillColor="Black"))

					C(object, CircleNoSmall(x,y,s,4,LineWidth=1,LineColor="Yellow",FillColor="Yellow"))
					C(object, Text(object.name,x,y-100,Position="tc",Color="White",Size=8))

				if isinstance(object, Fleet):
					if object.vel != (0, 0, 0):
						# We need to draw in a vector
						pass
					pass

		except Exception, e:
			do_traceback()

	def Create(self, object, drawable):
		drawable.oid = object.id

		self.Canvas.AddObject(drawable)

		drawable.Bind(EVT_FC_ENTER_OBJECT, self.OnEnter)
		drawable.Bind(EVT_FC_LEAVE_OBJECT, self.OnLeave)

	def OnEnter(self, evt):
		object = self.application.cache[evt.oid]
		print "Enter:", object

	def OnLeave(self, evt):
		object = self.application.cache[evt.oid]
		print "Leave:", object
		
