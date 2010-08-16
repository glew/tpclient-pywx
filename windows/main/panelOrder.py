"""\
The order window.
"""

# Python Imports
import time
import copy
import sys
import os

from extra.decorators import *

# wxPython Imports
import wx

# Protocol Imports
from tp.netlib import objects
from tp.netlib.objects import constants
from tp.netlib.objects import parameters

from tp.client import objectutils
from tp.client.ChangeList import ChangeNode, ChangeHead

from requirements import graphicsdir

TURNS_COL = 0
ORDERS_COL = 1

buttonSize = (wx.local.buttonSize[0], wx.local.buttonSize[1]+2)

CREATING = wx.Color(0, 0, 150)
UPDATING = wx.Color(150, 150, 0)
REMOVING = wx.Color(150, 0, 0)

from extra.StateTracker import TrackerObjectOrder, TrackerObject, TrackerOrder
from windows.xrc.panelOrder import panelOrderBase
class panelOrder(panelOrderBase, TrackerObject, TrackerOrder):
	title = _("Orders")

	def __init__(self, application, parent):
		panelOrderBase.__init__(self, parent)

		self.application = application
		self.parent = parent

		TrackerObject.__init__(self)
		TrackerOrder.__init__(self)

		self.Master.Hide()

		self.clipboard = None
		self.ignore = False

		self.Orders.InsertColumn(TURNS_COL, _("Turns"))
		self.Orders.SetColumnWidth(TURNS_COL, 40)
		self.Orders.InsertColumn(ORDERS_COL, _("Order Information"))
		self.Orders.SetColumnWidth(ORDERS_COL, 140)
		self.Orders.SetFont(wx.local.normalFont)

		self.Queues.Bind(wx.EVT_CHOICE, self.OnQueueSelect)

		self.DetailsSizer = self.DetailsPanel.GetSizer()

		self.Orders.Bind(wx.EVT_LIST_ITEM_SELECTED,   self.OnOrderSelect)
		self.Orders.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnOrderDeselect)
		self.Orders.Bind(wx.EVT_RIGHT_UP, self.OnRightClick)
		self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

	def OnKeySkip(self, evt):
		pass

	##########################################################################
	# AUI interface bits
	##########################################################################

	def GetPaneInfo(self):
		info = wx.aui.AuiPaneInfo()
		info.MinSize(self.GetBestSize())
		info.BestSize((self.GetBestSize()[0]*2,self.GetBestSize()[1]))
		info.Left()
		info.Layer(2)
		info.CaptionVisible(True)
		info.Caption(self.title)
		info.MinimizeButton(True)
		info.Icon(wx.Bitmap(os.path.join(graphicsdir, "order-icon.png")))
		return info

	def DockBestSize(self):
		return wx.Size(*self.GetBestSize())
	min_size = property(DockBestSize)

	##########################################################################
	# Update the various bits in the order list
	##########################################################################

	def ColourListItem(self, listpos, color):
		"""\
		Makes a listpos show that the item is pending changes.
		"""
		item = self.Orders.GetItem(listpos)
		item.SetTextColour(color)
		self.Orders.SetItem(item)

	def ColourOrderPanel(self):
		if len(self.nodes) != 1:
			self.DetailsBorderPanel.SetBackgroundColour(wx.NullColour)
		else:
			node = self.nodes[0]

			# Colour the background of the argument panel depending on the current state of the node
			if node.LastState == "idle":
				self.DetailsBorderPanel.SetBackgroundColour(wx.NullColour)
			if node.LastState == "creating":
				self.DetailsBorderPanel.SetBackgroundColour(CREATING)
			if node.LastState == "removing":
				self.DetailsBorderPanel.SetBackgroundColour(REMOVING)
			if node.LastState == "updating":
				self.DetailsBorderPanel.SetBackgroundColour(UPDATING)

	def InsertListItem(self, listpos, node):
		"""\
		Inserts an order a certain position in the list.
		"""
		assert listpos <= self.Orders.GetItemCount()
		assert not isinstance(node, ChangeHead)
		assert isinstance(node, ChangeNode)

		newlistpos = self.Orders.InsertStringItem(listpos, "")
		assert newlistpos == listpos, "%s == %s" % (newlistpos, listpos)
		self.Orders.SetItemPyData(listpos, node)

		self.UpdateListItem(listpos)

	def UpdateListItem(self, listpos):
		"""\
		Updates an node at a certain position in the list.
		"""
		node = self.Orders.GetItemPyData(listpos)

		if node.CurrentState is "idle":
			self.Orders.SetStringItem(listpos, TURNS_COL, unicode(node.CurrentOrder.turns))
		else:
			self.Orders.SetStringItem(listpos, TURNS_COL, 'U')

		self.Orders.SetStringItem(listpos, ORDERS_COL, node.CurrentOrder._name)

		# FIXME: Hack
		self.ColourOrderPanel()

		if node.LastState == "idle":
			self.ColourListItem(listpos, wx.BLACK)
		if node.LastState == "creating":
			self.ColourListItem(listpos, CREATING)
		if node.LastState == "removing":
			self.ColourListItem(listpos, REMOVING)
		if node.LastState == "updating":
			self.ColourListItem(listpos, UPDATING)

	def RemoveListItem(self, listpos):
		"""\
		Removes an order from a position in the list.
		"""
		# FIXME: Hack
		self.ColourOrderPanel()

		self.Orders.DeleteItem(listpos)

	##########################################################################
	# Methods called when state changes with an object
	##########################################################################

	@freeze_wrapper
	def ObjectSelect(self, id):
		"""\
		Called when an object is selected.
		"""
		# Hide the order panel when no object is selected
		if id is None:
			self.Master.Hide()
			return

		# Do the clean up first
		self.Orders.DeleteAllItems()
		self.Possible.Clear()
		self.Queues.Clear()

		# Get objects, its queues and possible order types
		object = self.application.cache.objects[self.oid]
		orderqueuelist = objectutils.getOrderQueueList(self.application.cache, object.id)
		ordertypes = objectutils.getOrderTypes(self.application.cache, object.id)

		# Display queues with possible order types or with existing orders
		for itemname, itemid in orderqueuelist:
			if len(ordertypes[itemid]) > 0 or len(self.application.cache.orders[itemid]) > 0:
				self.Queues.Append(itemname, itemid)

		if self.Queues.GetCount() > 0:
			self.Master.Show()
			self.Master.Layout()
			self.Master.Refresh()
		else:
			# No possible orders on this object
			self.Master.Hide()
			return

		self.Queues.Select(0)
		
		self.OrderQueueSelect(self.Queues.GetClientData(self.Queues.GetSelection()))

		orders = self.application.cache.orders[self.qid]
		
		if objectutils.getOrderQueueLimit(self.application.cache, id, self.qid) == 1:
			self.Orders.Hide()
		
		# Add all the orders to the list
		for listpos, node in enumerate(orders):
			self.InsertListItem(listpos, node)
			if not self.Orders.IsShown():
				self.Orders.SetSelected([listpos])
				self.OnOrderSelect(listpos)
	
		# Set which order types can be added to this object
		self.Possible.SetToolTipDefault(_("Order type to create"))
		
		ordertypes = objectutils.getOrderTypes(self.application.cache, object.id)
		for type in ordertypes[self.qid]:
			if not objects.OrderDescs().has_key(type):
				print "WARNING: Unknown order type with id %s" % type
				continue

			od = objects.OrderDescs()[type]
			self.Possible.Append(od._name, type)
			if hasattr(od, "doc"):
				desc = od.doc
			else:
				desc = od.__doc__
			desc = desc.strip()

			self.Possible.SetToolTipItem(self.Possible.GetCount()-1, desc)
		
		# Set the order types to the first selection
		if len(objectutils.getOrderTypes(self.application.cache, object.id)) > 0:
			self.Possible.Enable()
			self.Possible.SetSelection(0)
		else:
			self.Possible.Disable()

	##########################################################################
	# Methods called when state changes with the order
	##########################################################################
	@freeze_wrapper
	def OrdersSelect(self, nodes):
		# Orders Select is only valid when an object is selected
		assert self.oid != None
		assert self.qid != None
		
		d = self.application.cache.orders[self.qid]

		listpos = []
		for node in nodes:
			assert node in d
			listpos.append(d.index(node))

			assert listpos[-1] < self.Orders.GetItemCount()

		self.Orders.SetSelected(listpos)

		self.BuildPanel()

		# Enable the delete button if we have orders to delete	
		if len(nodes) > 0:
			self.Delete.Enable()
		else:
			self.Delete.Disable()

		# Ensure we can see the items
		if len(listpos) > 0:
			self.Orders.EnsureVisible(listpos[-1])

	@freeze_wrapper
	def OrderInsertAfter(self, afterme, toinsert):
		"""\
		Inserts the order into a slot.
		"""
		assert self.oid != None
		assert self.qid != None
		
		d = self.application.cache.orders[self.qid]

		assert afterme in d
		assert toinsert in d

		# Inserting into an empty list
		listpos = d.index(afterme) + 1

		# Update the list box
		self.InsertListItem(listpos, toinsert)

	@freeze_wrapper
	def OrderInsertBefore(self, beforeme, toinsert):
		"""\
		Inserts the order into a slot.
		"""
		assert self.oid != None
		assert self.qid != None
		
		d = self.application.cache.orders[self.qid]

		assert beforeme in d
		assert toinsert in d

		# Inserting into an empty list
		listpos = d.index(beforeme)-1

		# Update the list box
		self.InsertListItem(listpos, toinsert)

	@freeze_wrapper
	def OrderRefresh(self, node):
		"""\
		"""
		assert self.oid != None
		assert self.qid != None
		
		d = self.application.cache.orders[self.qid]
		
		assert node in d

		assert self.Orders.GetItemPyData(d.index(node)) is node

		self.UpdateListItem(d.index(node))

		if node in self.nodes:
			self.BuildPanel()

	@freeze_wrapper
	def OrdersRemove(self, nodes, override=False):
		"""\
		Deletes the order from a slot.
		"""
		assert self.oid != None
		assert self.qid != None
		
		d = self.application.cache.orders[self.qid]

		listposes = []
		for i in range(0, self.Orders.GetItemCount()):
			node = self.Orders.GetItemPyData(i)
			if node in nodes:
				listposes.append((i, node))
		listposes.sort(reverse=True)

		if override:
			for listpos, node in listposes:
				self.UpdateListItem(listpos)

				if node in self.nodes:
					self.BuildPanel()
		else:
			for listpos, node in listposes:
				self.RemoveListItem(listpos)

	####################################################
	# Local Event Handlers
	####################################################
	@freeze_wrapper
	def OnQueueSelect(self, evt):
		self.OrderQueueSelect(self.Queues.GetClientData(self.Queues.GetSelection()))
		# Do the clean up first
		self.Orders.DeleteAllItems()
		self.Possible.Clear()
		
		object = self.application.cache.objects[self.oid]
		orders = self.application.cache.orders[self.qid]
		
		# Add all the orders to the list
		for listpos, node in enumerate(orders):
			self.InsertListItem(listpos, node)
	
		# Set which order types can be added to this object
		self.Possible.SetToolTipDefault(_("Order type to create"))
		
		ordertypes = objectutils.getOrderTypes(self.application.cache, object.id)
		for type in ordertypes[self.qid]:
			if not objects.OrderDescs().has_key(type):
				print "WARNING: Unknown order type with id %s" % type
				continue

			od = objects.OrderDescs()[type]
			self.Possible.Append(od._name, type)
			if hasattr(od, "doc"):
				desc = od.doc
			else:
				desc = od.__doc__
			desc = desc.strip()

			self.Possible.SetToolTipItem(self.Possible.GetCount()-1, desc)
		
		# Set the order types to the first selection
		if len(objectutils.getOrderTypes(self.application.cache, object.id)) > 0:
			self.Possible.Enable()
			self.Possible.SetSelection(0)
		else:
			self.Possible.Disable()
		
		self.BuildPanel()
		
	def OnOrderDeselect(self, evt):
		wx.CallAfter(self.OnOrderSelect, evt)

	@freeze_wrapper
	def OnOrderSelect(self, evt):
		"""\
		Called when somebody selects an order.
		"""
		if self.Orders.ignore > 0:
			self.Orders.ignore -= 1
			return

		nodes = []
		for listpos in self.Orders.GetSelected():
			nodes.append(self.Orders.GetItemPyData(listpos))

		self.SelectOrders(nodes)
		
	@freeze_wrapper
	def OnOrderNew(self, evt, after=True):
		"""\
		Called to add a new order.
		"""
		assert self.oid != None

		# Figure out what type of new order we are creating
		type = self.Possible.GetSelection()
		if type == wx.NOT_FOUND:
			return
		type = self.Possible.GetClientData(type)
		
		# Build the argument list
		orderdesc = objects.OrderDescs()[type]

		# sequence, id, slot, type, turns, resources
		args = [-1, self.qid, -1, type, 0, []]
		for property in orderdesc.properties:
			# FIXME: These could probably be made into better functions that create 
			# more reasonable initial values.
			if isinstance(property, parameters.OrderParamAbsSpaceCoords):
				args += [[[0, 0, 0]]]
			elif isinstance(property, parameters.OrderParamRelSpaceCoords):
				args += [[0, [0, 0, 0]]]
			elif isinstance(property, parameters.OrderParamList):
				args += [[[], []]]
			elif isinstance(property, parameters.OrderParamString):
				args += [[0, ""]]
			elif isinstance(property, parameters.OrderParamTime):
				args += [[0, 0]]
			elif isinstance(property, parameters.OrderParamObject):
				args += [[0, []]]
			elif isinstance(property, parameters.OrderParamPlayer):
				args += [[0, 0]]
			elif isinstance(property, parameters.OrderParamRange):
				args += [[-1, -1, -1, -1]]
			elif isinstance(property, parameters.OrderParamReference):
				args += [[0, [0]]]
			elif isinstance(property, parameters.OrderParamReferenceList):
				args += [[[0], [0]]]
			elif isinstance(property, parameters.OrderParamResourceList):
				args += [[[0,0], 0, 0, [0,0]]]
			elif isinstance(property, parameters.OrderParamGenericReferenceQuantityList):
				args += [[[0, []], [0, "", 0, [], []], []]]
			else:
				print "Unknown: ", type(property)
				return

		# Create the new order
		new = objects.Order(*args)
		new._dirty = True

		# Insert the new order (after the currently selected)
		if after:
			node = self.InsertAfterOrder(new)
		else:
			node = self.InsertBeforeOrder(new)

		self.SelectOrders([node])

	@freeze_wrapper
	def OnOrderDelete(self, evt):
		"""\
		Called to delete the selected orders.
		"""
		self.RemoveOrders()

	@freeze_wrapper
	def OnOrderSave(self, evt):
		"""\
		Called to save the current selected orders.
		"""
		if len(self.nodes) != 1:
			return
			
		# Update the order
		order = self.FromPanel(self.nodes[0].CurrentOrder)
		self.ChangeOrder(order)

	OnNew    = OnOrderNew
	OnSave   = OnOrderSave
	OnDelete = OnOrderDelete

	@freeze_wrapper
	def OnRevert(self, evt):
		self.BuildPanel()

	@freeze_wrapper
	def OnOrderDirty(self, evt):
		"""\
		Called when an order is updated but not yet saved.
		"""
		# Ignore programatic changes
		if self.ignore:
			return 

		assert len(self.nodes) == 1
		
		# Update the order
		order = self.FromPanel(self.nodes[0].CurrentOrder)

		# Tell the gui about the change
		self.DirtyOrder(order)
	
	####################################################
	# Panel Functions
	####################################################
	@freeze_wrapper
	def BuildPanel(self):
		"""\
		Builds a panel for the entering of orders arguments.
		"""
		try:
			object = self.application.cache.objects[self.oid]
			nodes = self.nodes

			if len(objectutils.getOrderTypes(self.application.cache, object.id)) <= 0:
				node = _("No orders available")
			elif len(nodes) > 1:
				node = _("Multiple orders selected.")
			elif len(nodes) < 1:
				node = None
			else:
				node = nodes[0]

				if node.LastState in ("removing", "removed"):
					node = _("Order queued for removal.")
		except KeyError:
			node = _("No object selected.")

		self.ColourOrderPanel()

		# Remove the previous panel and stuff
		if hasattr(self, "ArgumentsPanel"):
			self.ArgumentsPanel.Hide()
			self.DetailsSizer.Remove(self.ArgumentsPanel)
			self.ArgumentsPanel.Destroy()
			del self.ArgumentsPanel

		# Show the details panel
		DetailsPanelShow = True
		self.DetailsPanel.Hide()
		self.ArgumentLine.Hide()
		self.Message.SetLabel("")
		self.Message.Hide()

		if isinstance(node, ChangeNode):
			order = node.CurrentOrder
			assert not order is None

			# Create a new panel
			self.ArgumentsPanel = wx.Panel(self.DetailsPanel, -1)
			self.ArgumentsPanel.Bind(wx.EVT_KEY_UP, self.OnKeySkip)

			self.ArgumentsPanel.SetAutoLayout( True )
			self.ArgumentsSizer = wx.FlexGridSizer( 0, 1, 0, 0)
			self.ArgumentsPanel.SetSizer(self.ArgumentsSizer)
			self.ArgumentsSizer.AddGrowableCol( 0 )

			orderdesc = objects.OrderDescs()[order.subtype]
			
			# List for the argument subpanels
			self.ArgumentsChildren = []
				
			for property in orderdesc.properties:
				name = property.name
				# Add there name..
				name_text = wx.StaticText( self.ArgumentsPanel, -1, name.title().replace("_","") )
				name_text.SetFont(wx.local.tinyFont)

				# Add the arguments bit
				namepos = wx.LEFT
				if isinstance(property, parameters.OrderParamAbsSpaceCoords):
					subpanel = PositionArgumentPanel(self.ArgumentsPanel)
					subpanel.application = self.application
					subpanel.set_value(list(getattr(order, name)))
				elif isinstance(property, parameters.OrderParamRelSpaceCoords):
					subpanel = RelativePositionArgumentPanel(self.ArgumentsPanel)
					subpanel.application = self.application
					subpanel.set_value(list(getattr(order, name)))
				elif isinstance(property, parameters.OrderParamList):
					subpanel = ListArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value(list(getattr(order, name)))
				elif isinstance(property, parameters.OrderParamString):
					subpanel = TextArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value([getattr(order, name)])
				elif isinstance(property, parameters.OrderParamTime):
					subpanel = TimeArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value([getattr(order,name)])
				elif isinstance(property, parameters.OrderParamObject):
					subpanel = ObjectArgumentPanel(self.ArgumentsPanel)
					subpanel.application(self.application)
					subpanel.set_value([getattr(order,name)])
				elif isinstance(property, parameters.OrderParamPlayer):
					subpanel = PlayerArgumentPanel(self.ArgumentsPanel)
					subpanel.application(self.application)
					subpanel.set_value([getattr(order,name)])
				elif isinstance(property, parameters.OrderParamRange):
					subpanel = RangeArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value([getattr(order,name)])
				elif isinstance(property, parameters.OrderParamReference):
					subpanel = UnimplementedArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value(["Unimplemented: OrderParamReference"])
				elif isinstance(property, parameters.OrderParamReferenceList):
					subpanel = UnimplementedArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value(["Unimplemented: OrderParamReferenceList"])
				elif isinstance(property, parameters.OrderParamResourceList):
					subpanel = UnimplementedArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value(["Unimplemented: OrderParamResourceList"])
				elif isinstance(property, parameters.OrderParamGenericReferenceQuantityList):
					subpanel = UnimplementedArgumentPanel(self.ArgumentsPanel)
					subpanel.set_value(["Unimplemented: OrderParamGenericReferenceList"])
				else:
					return

				#subpanel.SetToolTip(wx.ToolTip(getattr(order, name+'__doc__')))
				subpanel.SetFont(wx.local.normalFont)
				self.ArgumentsChildren.append( subpanel )
				
				if subpanel.namepos == wx.TOP:
					self.ArgumentsSizer.Add( name_text, 0, wx.ALIGN_CENTER|wx.RIGHT|wx.LEFT,  border=4)
					self.ArgumentsSizer.Add( subpanel, 1,  wx.GROW|wx.EXPAND|wx.ALIGN_CENTER)
		
				elif subpanel.namepos == wx.LEFT:
					ArgumentSubSizer = wx.BoxSizer(wx.HORIZONTAL)
					ArgumentSubSizer.Add( name_text, 0, wx.ALIGN_CENTER|wx.RIGHT, 4 )
					ArgumentSubSizer.Add( subpanel,  1, wx.GROW|wx.EXPAND|wx.ALIGN_CENTER)

					self.ArgumentsSizer.Add(ArgumentSubSizer, 1, wx.GROW|wx.EXPAND|wx.ALIGN_CENTER)

				else:
					raise TypeError('WTF?')

				self.ArgumentsPanel.Layout()

			if len(orderdesc.properties) == 0:
				name_text = wx.StaticText( self.ArgumentsPanel, -1, "No arguments" )
				name_text.SetFont(wx.local.normalFont)
				self.ArgumentsSizer.Add( name_text, 0, wx.ALIGN_CENTER|wx.CENTER, 4 )

#			self.DetailsPanel.SetClientSize(wx.Size(self.GetBestSize()[0], -1))
			self.DetailsSizer.Add( self.ArgumentsPanel, flag=wx.GROW|wx.EXPAND|wx.ALIGN_CENTER|wx.ALL)
		
			# Show the Save/Revert/Delete buttons
			self.Message.Show()
			self.Save.Show()
			self.Revert.Show()
			self.Delete.Show()
	
		elif isinstance(node, (unicode, str)):
			self.Message.SetLabel(node)
			self.Message.Show()

			# Hide the Save/Revert buttons
			self.Save.Hide()
			self.Revert.Hide()

			# Delete button should still be valid
			self.Delete.Show()
		else:
			DetailsPanelShow = False
			self.ArgumentLine.Hide()

			# Hide the Save/Revert/Delete buttons
			self.Save.Hide()
			self.Revert.Hide()
			self.Delete.Hide()

		if DetailsPanelShow:
			self.DetailsPanel.Show()
			self.ArgumentLine.Show()

		self.Orders.SetSize((-1,0))
		self.Master.Layout()
		self.DetailsPanel.Layout()
		self.Layout()

	def FromPanel(self, order):
		orderdesc = objects.OrderDescs()[order.subtype]
		
		args = [order.sequence, order.id, -1, order.subtype, 0, []]
		subpanels = copy.copy(self.ArgumentsChildren)
		for property in orderdesc.properties:
			panel = subpanels.pop(0)
			args += [panel.get_value()]
		
		return apply(objects.Order, args)

	##########################################################################
	# Clipboard functionality
	##########################################################################

	def BuildMenu(self, menu):
		"""\
		Build a menu containing the order types which could be inserted.
		"""
		object = self.application.cache.objects[self.oid]
		
		ordertypes = objectutils.getOrderTypes(self.application.cache, object.id)
		
		# FIXME: Separate the queues here?
		for orderqueue, types in ordertypes.items():
			for type in types:
				if not objects.OrderDescs().has_key(type):
					continue

				od = objects.OrderDescs()[type]
			
				if hasattr(od, "doc"):
					desc = od.doc
				else:
					desc = od.__doc__
				desc = desc.strip()
				menu.Append(-1, od._name, desc)

	def CheckClipBoard(self):
		"""\
		Check if the items in the clipboard could be pasted on the currently selected object.
		"""
		if self.clipboard != None:
			for subtype, orderstring in self.clipboard:
				if not objects.OrderDescs().has_key(subtype):
					return False

				slot = self.Possible.FindString(objects.OrderDescs()[subtype]._name)
				if slot == wx.NOT_FOUND:
					return False
			return True
		return False

	def OnOrderCopy(self, evt):
		if len(self.nodes) < 1:
				return

		self.clipboard = []

		for node in self.nodes:
			self.clipboard.append((node.CurrentOrder.subtype, node.CurrentOrder.__str__()))

	def OnOrderCut(self, evt):
		self.OnOrderCopy(evt)
		self.OnOrderDelete(evt)

	####################################################
	# Window Event Handlers
	####################################################
	def OnRightClick(self, evt):
		"""\
		Pop-up a menu when a person right clicks on the order list.
		"""
		slot = self.Orders.HitTest(evt.GetPosition())[0]
		if slot != wx.NOT_FOUND:
			if not evt.ControlDown() and not evt.ShiftDown():
				# Check if shift or ctrl is being held down...
				self.Orders.SetSelected([slot])
			else:
				self.Orders.AddSelected(slot)

		id = wx.NewId()
		menu = wx.Menu()
		menu.SetTitle(_("Top"))

		# Check to see if we can paste the stuff here...
		nopaste = self.CheckClipBoard()

		slots = self.Orders.GetSelected()
		if len(slots) > 0:
			before = wx.Menu()
			before.SetTitle(_("Before"))
			menu.AppendMenu(-1, _("New Before"), before)
			self.BuildMenu(before)

			after = wx.Menu()
			after.SetTitle(_("After"))
			menu.AppendMenu(-1, _("New After"), after)
			self.BuildMenu(after)
	
			menu.Append(-1, _("Delete"))

			menu.AppendSeparator()
			
			menu.Append(-1, _("Cut"))
			menu.Append(-1, _("Copy"))

			if self.clipboard != None:
				menu.Append(-1, _("Paste Before"))
				menu.Enable(menu.FindItem(_("Paste Before")), nopaste)
				menu.Append(-1, _("Paste After"))
				menu.Enable(menu.FindItem(_("Paste After")), nopaste)
		else:
			new = wx.Menu()
			new.SetTitle(_("New"))
			menu.AppendMenu(-1, _("New"), new)
			self.BuildMenu(new)
			
			if self.clipboard != None:
				menu.Append(-1, _("Paste"))
				menu.Enable(menu.FindItem(_("Paste")), nopaste)
			
		self.Bind(wx.EVT_MENU, self.OnOrderMenu)
		self.PopupMenu(menu)

	def OnOrderMenu(self, evt):
		"""\
		An action from the right click menu.
		"""
		menu = evt.GetEventObject()
		item = menu.FindItemById(evt.GetId())
		
		t = item.GetText()
		if t == _("Delete"):
			self.OnOrderDelete(None)
			
		elif t == _("Copy"):
			self.OnOrderCopy(None)
			
		elif t == _("Cut"):
			self.OnOrderCut(None)
				
		elif t.startswith(_("Paste")):
			if self.CheckClipBoard() == False:
				print _("Cant paste because the orders arn't valid on this object.")
				return
				
			# Figure out whats our new position
			
			subtype, orderstring = self.clipboard[0]
			order = objects.Header.fromstr(orderstring[:objects.Header.size])
			order.__process__(orderstring[objects.Header.size:])
			if t.endswith(_("Before")):
				node = self.InsertBeforeOrder(order)
			else:
				node = self.InsertAfterOrder(order)

			for order in self.clipboard[1:]:
				node = self.InsertAfterOrder(order, node)

		else:
			slot = self.Possible.FindString(t)
			if slot == wx.NOT_FOUND:
				return

			self.Possible.SetSelection(slot)
			
			if menu.GetTitle() == _("Before"):
				self.OnOrderNew(None, after=False)
			else:
				self.OnOrderNew(None)

class ArgumentPanel(object):
	"""\
	Base class for all other Argument panels.
	"""

	# The position to place the name argument
	namepos = wx.LEFT

	pass

from windows.xrc.orderUnimplemented import orderUnimplementedBase
class UnimplementedArgumentPanel(ArgumentPanel, orderUnimplementedBase):

	def set_value(self, list):
		print "UnimplementedArgumentPanel", list
		self.__text = list.pop(0)
		self.Unimplemented.SetLabel(self.__text)

	def get_value(self):
		return []

from windows.xrc.orderText import orderTextBase
class TextArgumentPanel(ArgumentPanel, orderTextBase):

	def set_value(self, list):
		print "TextArgumentPanel", list
		self.__max, self.__text = list.pop(0)
		self.Value.SetValue(self.__text)

	def get_value(self):
		return [self.__max, unicode(self.Value.GetValue())]

from windows.xrc.orderObject import orderObjectBase
class ObjectArgumentPanel(ArgumentPanel, orderObjectBase):

	def __init__(self, parent, *args, **kw):
		ArgumentPanel.__init__(self)
		orderObjectBase.__init__(self, parent, *args, **kw)

		self.Value.SetFont(wx.local.tinyFont)

	# FIXME: This is broken	
	def application(self, value):
		combobox = self.Value

		combobox.Freeze()
		combobox.Append(_("No object"), -1)

		# Sort the objects by name
		objects = value.cache.objects.values()
		def objcmp(obja, objb):
			return cmp(obja.name, objb.name)
		objects.sort(objcmp)

		for object in objects:
			combobox.Append(object.name + " (%s)" % object.id, object.id)

		combobox.Thaw()

	def set_value(self, list):
		self.__oid = list.pop(0)[0]

		combobox = self.Value
		combobox.SetSelection(0)
		for slot in xrange(0, combobox.GetCount()):
			if combobox.GetClientData(slot) == self.__oid:
				combobox.SetSelection(slot)
				break

	def get_value(self):
		self.__oid = long(self.Value.GetClientData(self.Value.GetSelection()))
		return [self.__oid, []]

	
from windows.xrc.orderPlayer import orderPlayerBase
class PlayerArgumentPanel(ArgumentPanel, orderPlayerBase):

	def __init__(self, parent, *args, **kw):
		ArgumentPanel.__init__(self)
		orderPlayerBase.__init__(self, parent, *args, **kw)

		self.Value.SetFont(wx.local.tinyFont)

	# FIXME: This is broken	
	# FIXME: Should filter players by masking bits in parameters.py
	def application(self, value):
		combobox = self.Value

		combobox.Freeze()
		combobox.Append(_("No player"), -1)

		# Sort the objects by name
		players = value.cache.players.values()

		for players in players:
			combobox.Append(player.name + " (%s)" % player.id, player.id)

		combobox.Thaw()

	def set_value(self, list):
		print "PlayerArgumentPanel", list
		self.__oid = list.pop(0)

		combobox = self.Value
		combobox.SetSelection(0)
		for slot in xrange(0, combobox.GetCount()):
			if combobox.GetClientData(slot) == self.__oid:
				combobox.SetSelection(slot)
				break

	def get_value(self):
		self.__oid = long(self.Value.GetClientData(self.Value.GetSelection()))
		return [self.__oid]


from windows.xrc.orderRange import orderRangeBase
class TimeArgumentPanel(ArgumentPanel, orderRangeBase):

	def set_value(self, list):
		print "TimeArgumentPanel", list
		self.__text, self.__max = list.pop(0)
		self.Value.SetValue(self.__text)

	def get_value(self):
		return [long(self.Value.GetValue()), self.__max]
		
from windows.xrc.orderRange import orderRangeBase
class RangeArgumentPanel(ArgumentPanel, orderRangeBase):

	def set_value(self, list):
		print "RangeArgumentPanel", list
		self.__text, self.self.__min, self.__max, self.__increment = list.pop(0)
		self.Value.SetMin(self.__min)
		self.Value.SetMax(self.__max)
		self.Value.SetValue(self.__text)

	def get_value(self):
		return [long(self.Value.GetValue()), self.__min, self.__max, self.__increment]

from windows.xrc.orderPosition import orderPositionBase
class PositionArgumentPanel(ArgumentPanel, orderPositionBase):
	def OnSelectPosition(self, evt):
		self.X.SetValue(unicode(evt[0]))
		self.Y.SetValue(unicode(evt[1]))
		self.Z.SetValue(unicode(evt[2]))

		# Go back to selection mode
		from windows.main.panelStarMap import panelStarMap
		starmap = self.application.gui.main.panels[panelStarMap.title]
		starmap.SetMode(starmap.GUISelect)

		# Remove selection handler
		delattr(self.application.gui.main.panels[panelOrder.title], "OnSelectPosition")

	def OnLocate(self, evt):
		self.application.gui.main.panels[panelOrder.title].OnSelectPosition = self.OnSelectPosition
		from windows.main.panelStarMap import panelStarMap
		starmap = self.application.gui.main.panels[panelStarMap.title]
		starmap.SetMode(starmap.GUIWaypointEdit)

	def set_value(self, list):
		print "PositionArgumentPanel", list
		self.X.SetValue(unicode(list[0][0]))
		self.Y.SetValue(unicode(list[0][1]))
		self.Z.SetValue(unicode(list[0][2]))

	def get_value(self):
		return [[long(self.X.GetValue()), long(self.Y.GetValue()), long(self.Z.GetValue())]]

from windows.xrc.orderRelPosition import orderRelPositionBase
class RelativePositionArgumentPanel(ArgumentPanel, orderRelPositionBase):
	def OnSelectPosition(self, evt):
		self.X.SetValue(unicode(evt[0]))
		self.Y.SetValue(unicode(evt[1]))
		self.Z.SetValue(unicode(evt[2]))

		# Go back to selection mode
		from windows.main.panelStarMap import panelStarMap
		starmap = self.application.gui.main.panels[panelStarMap.title]
		starmap.SetMode(starmap.GUISelect)

		# Remove selection handler
		delattr(self.application.gui.main.panels[panelOrder.title], "OnSelectPosition")

	def OnLocate(self, evt):
		self.application.gui.main.panels[panelOrder.title].OnSelectPosition = self.OnSelectPosition
		from windows.main.panelStarMap import panelStarMap
		starmap = self.application.gui.main.panels[panelStarMap.title]
		starmap.SetMode(starmap.GUIWaypointEdit)

	def set_value(self, list):
		print "PositionArgumentPanel", list
		self.ObjectID.SetValue(unicode(list[0]))
		self.X.SetValue(unicode(list[1][0]))
		self.Y.SetValue(unicode(list[1][1]))
		self.Z.SetValue(unicode(list[1][2]))

	def get_value(self):
		return [self.ObjectID.GetValue(), [long(self.X.GetValue()), long(self.Y.GetValue()), long(self.Z.GetValue())]]

from windows.xrc.orderList import orderListBase
class ListArgumentPanel(ArgumentPanel, orderListBase):
	namepos = wx.TOP

	NAME = 0
	MAX  = 1

	def __init__(self, parent, *args, **kw):
		ArgumentPanel.__init__(self)
		orderListBase.__init__(self, parent, *args, **kw)

		self.__options = {}
		self.__selections = {}
		self.__choices = [None]

		self.Choices.InsertColumn(0, "#")
		self.Choices.SetColumnWidth(0, 25)
		self.Choices.InsertColumn(1, _("Type"))
		self.Choices.SetColumnWidth(1, 100)
		self.Choices.Layout()

		self.Type.SetMaxSize((-1, self.Number.GetSize()[1]))

		self.Bind(wx.EVT_LIST_ITEM_SELECTED,   self.OnChoicesSelect)
		self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnChoicesDeselect)

		self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnChoicesEditStart)
		self.Bind(wx.EVT_LIST_END_LABEL_EDIT,   self.OnChoicesEditEnd)

		self.OnChoicesDeselect(None)
		self.OnType(None)

	def set_value(self, list):
		print "ListArgumentPanel", list

		options_list   = list.pop(0)
		selection_list = list.pop(0)

		# Convert the options into a dictionary
		options = {}
		for type, name, max in options_list:
			options[type] = (name, max)

		# Convert the selection into a dictionary
		selections = {}
		for type, number in selection_list:
			selections[type] = number
		
		if self.__options != options:
			self.__options = options

			# FIXME: Should sort by the name

			self.Type.Clear()
			for type, (name, max) in options.items():
				self.Type.Append(name, type)

		if self.__selections != selections:
			self.__selections = selections

			self.Choices.DeleteAllItems()
			for slot, (type, number) in enumerate(selections.items()):
				self.Choices.InsertStringItem(slot, "")
				self.Choices.SetStringItem(slot, 0, unicode(number))
				self.Choices.SetStringItem(slot, 1, options[type][self.NAME])
				self.Choices.SetItemPyData(slot, type)

			self.Choices.Layout()

	def get_value(self):
		options = []
		for type, (name, max) in self.__options.items():
			options.append((type, name, max))

		selections = []
		for type, number in self.__selections.items():
			selections.append((type, number))

		return [options, selections]

	def OnChoicesEditStart(self, evt):
		pass

	def OnChoicesEditEnd(self, evt):
		try:
			value = long(evt.GetLabel())

			# Make sure the value is positive
			if value < 0:
				evt.Veto()		
				return	

			type = self.Choices.GetItemPyData(evt.GetIndex())

			# Make sure that the value is not bigger then the maximum
			value = min(value, self.__options[type][self.MAX])

			slot = self.Choices.FindItemByPyData(type)
			if value > 0:
				# Set the value
				self.__selections[type] = value

				self.Choices.SetStringItem(slot, 0, unicode(value))
				self.UpdateNumber(type)
			else:
				del self.__selections[type]
				self.Choices.DeleteItem(slot)

				self.UpdateNumber(type)

		except ValueError:
			pass
		evt.Veto()

	def OnAdd(self, evt):
		amount = self.Number.GetValue()
		if amount == 0:
			return	

		type = self.Type.GetSelection()
		if type == wx.NOT_FOUND:
			return
		type = self.Type.GetClientData(type)

		s = self.__selections

		if not s.has_key(type):
			s[type] = 0

			slot = self.Choices.GetItemCount()
			self.Choices.InsertStringItem(slot, "")
			self.Choices.SetStringItem(slot, 0, unicode(amount))
			self.Choices.SetStringItem(slot, 1, self.__options[type][self.NAME])
			self.Choices.SetItemPyData(slot, type)

		s[type] += amount
		s[type]  = max(min(s[type], self.__options[type][self.MAX]), 0)
		
		slot = self.Choices.FindItemByPyData(type)
		if s[type] == 0:
			del s[type]
			self.Choices.DeleteItem(slot)
		else:
			self.Choices.SetStringItem(slot, 0, unicode(s[type]))

		self.UpdateNumber(type)
	
	def OnDelete(self, evt):
		selected = self.Choices.GetSelected()
		
		for selection in selected:
			type = self.Choices.GetItemPyData(selection)
			del self.__selections[type]

			self.Choices.DeleteItem(selection)

	def UpdateNumber(self, type):
		s = self.__selections
		if s.has_key(type):
			self.Number.SetRange(-1*self.__selections[type], self.__options[type][self.MAX]-self.__selections[type])
		else:
			self.Number.SetRange(1, self.__options[type][self.MAX])

		if self.Number.GetValue() == 0:
			self.Number.SetValue(1)

	def OnType(self, evt):
		type = self.Type.GetSelection()
		if type == wx.NOT_FOUND:
			self.Add.Disable()
			self.Number.Disable()
			return
		type = self.Type.GetClientData(type)

		self.Add.Enable()
		self.Number.Enable()
		self.UpdateNumber(type)

		# Select the linst related to this type
		slot = self.Choices.FindItemByPyData(type)
		if slot == wx.NOT_FOUND:
			self.Choices.SetSelected([])
		else:
			self.Choices.SetSelected([slot])
			self.Choices.EnsureVisible(slot)

	def OnChoicesDeselect(self, evt):
		wx.CallAfter(self.OnChoicesSelect, evt)

	def OnChoicesSelect(self, evt):
		try:
			choices = self.Choices.GetSelected()
		except:
			return

		if self.__choices == choices:
			return
		else:
			self.__choices = choices

		if len(choices) > 1:
			self.Type.SetSelection(wx.NOT_FOUND)
			self.Add.Disable()
			self.Number.Disable()
			self.Type.Disable()
		else:
			self.Type.Enable()

			if len(choices) > 0:
				self.Delete.Enable()

				type = self.Choices.GetItemPyData(choices[0])
				for slot in range(0, self.Type.GetCount()):
					if self.Type.GetClientData(slot) == type:
						self.Type.SetSelection(slot)
						self.OnType(None)
						break
			else:
				self.Delete.Disable()

