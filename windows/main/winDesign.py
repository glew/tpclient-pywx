"""\
This module contains the System window. The System window displays all objects
at this current location and "quick" details about them.
"""

# Python imports
from types import TupleType
from copy import deepcopy

# wxPython imports
import wx
import wx.gizmos

# Local imports
from windows.winBase import winReportXRC, ShiftMixIn
from windows.xrc.winDesign import winDesignBase

from tp.client.parser import DesignCalculator
from tp.netlib.objects import Design, Component, Category

NAME = 0
DESC = 1

COL_SIZE=150

wx.ArtProvider()
Art = wx.ArtProvider_GetBitmap
wx.ArtSize = (16, 16)

def comparetoid(a, b):
	if not b is None and a[0] == type(b) and a[1] == b.id:
		return True
	return False

def comparebyid(a, b):
	if not b is None and type(a) == type(b) and a.id == b.id:
		return True
	return False


from windows.xrc.winCategoriesManager import CategoriesManagerBase
class CategoriesManager(CategoriesManagerBase, wx.Frame):
	"""\
	This class is a popup window with a checklist of categories.
	"""
	def __init__(self, parent, control):
		"""\
		Initialize the window, loading data from XRC, and add the resources.
		"""
		CategoriesManagerBase.__init__(self, parent)
		self.parent = parent
		self.control = control
		self.idlist = []
		self.Bind(wx.EVT_ACTIVATE, self.OnActivate)
		self.Hide()

	def SetOptions(self, categories):
		"""\
		Called to set the categories, takes a list of tuples of strings and their corresponding ID numbers.
		"""
		self.CategoriesList.Clear()
		stringlist = []
		
		for name, id in categories:
			stringlist.append(name)
			self.idlist.append(id)
		self.CategoriesList.InsertItems(stringlist, 0)
	
	def GetChecked(self):
		"""\
		Returns a list of the indices that are checked.
		"""
		returnlist = []
		for num in self.CategoriesList.GetChecked():
			returnlist.append(self.idlist[num])
		
		return returnlist
			
	
	def SetCheckedStrings(self, stringlist):
		"""\
		Called to set which categories are checked, takes a list of strings.
		"""
		self.CategoriesList.SetCheckedStrings(stringlist)
	
	def OnActivate(self, evt):
		"""\
		Called when the window becomes active or inactive.
		"""
		self.Move(self.control.GetScreenRect().GetTopLeft()+(0,self.control.GetSizeTuple()[1]))
		if evt.GetActive() == False:
			self.OnDone(evt)

	def Show(self, show=True):
		"""\
		Called when the window is shown.
		"""
		self.Panel.Layout()

		size = self.CategoriesList.GetBestSize()
		self.CategoriesList.SetMinSize(size)

		self.SetMinSize(self.Panel.GetBestSize())
		self.SetSize(self.Panel.GetBestSize())

		wx.Frame.Show(self)
	
	def OnDone(self, evt):
		self.parent.SetSelectedCategories(self.GetChecked())
		self.Hide()

class winDesign(winReportXRC, winDesignBase, ShiftMixIn):
	title = _("Design")
	
	def __init__(self, application, parent):
		winDesignBase.__init__(self, parent)
		winReportXRC.__init__(self, application, parent)
		ShiftMixIn.__init__(self)
		
		self.CategoriesWindow = CategoriesManager(self, self.Categories)
		
		self.selected = None	# Currently selected design
		self.updating = []		# Designs which are been saved to the server
		self.creating = []		# Designs which are being created on the server

		#Panel = wx.Panel(self, -1)
		
		self.icons = wx.ImageList(*wx.ArtSize)
		self.icons.Add(Art(wx.ART_FOLDER, wx.ART_OTHER, wx.ArtSize))
		self.icons.Add(Art(wx.ART_FILE_OPEN, wx.ART_OTHER, wx.ArtSize))
		self.icons.Add(Art(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.ArtSize))

		self.grid = self.Panel.GetSizer()

		self.DesignsTree.SetImageList(self.icons)

		# The labels
		################################################################
		self.top			= self.TitlePanel.GetSizer()
		self.middle			= self.DesignPanel.GetSizer()
		self.designsizer	= self.DesignInfoPanel.GetSizer()
		self.compssizer		= self.ComponentsPanel.GetSizer()
		self.addsizer		= self.ComponentsButtonPanel.GetSizer()

		self.design_ps		= wx.BoxSizer(wx.HORIZONTAL)

		self.PartsList.InsertColumn(0, "#", format=wx.LIST_FORMAT_RIGHT, width=20)
		self.PartsList.InsertColumn(1, _("Component"))

		self.ComponentsTree.SetImageList(self.icons)

		self.Panel.SetAutoLayout( True )

		self.Bind(wx.EVT_BUTTON, self.OnEdit,   self.Edit)
		self.Bind(wx.EVT_BUTTON, self.OnRemove, self.Delete)
		self.Bind(wx.EVT_BUTTON, self.OnSelect, self.Revert)
		self.Bind(wx.EVT_BUTTON, self.OnDuplicate, self.Duplicate)
		self.Bind(wx.EVT_BUTTON, self.OnSave,   self.Save)

		self.Bind(wx.EVT_BUTTON, self.OnAdd,     self.ComponentsAdd)
		self.Bind(wx.EVT_BUTTON, self.OnAddMany, self.ComponentsAddMany)

		self.Bind(wx.EVT_BUTTON, self.OnCategories, self.Categories)

		self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelectObject, self.DesignsTree)
		
		self.DesignsSearch.Bind(wx.EVT_TEXT, self.BuildDesignList)
		self.DesignsSearch.Bind(wx.EVT_TEXT_ENTER, self.BuildDesignList)
		self.DesignsSearch.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.BuildDesignList)
		self.DesignsSearch.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnDesignsSearchCancel)
		
		self.TitleEditable.Bind(wx.EVT_TEXT, self.TitleChanged)
		self.TitleEditable.Bind(wx.EVT_TEXT_ENTER, self.TitleChanged)
		
		self.ComponentsSearch.Bind(wx.EVT_TEXT, self.BuildCompList)
		self.ComponentsSearch.Bind(wx.EVT_TEXT_ENTER, self.BuildCompList)
		self.ComponentsSearch.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.BuildCompList)
		self.ComponentsSearch.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnComponentsSearchCancel)

		self.application.gui.Binder(self.application.CacheClass.CacheUpdateEvent, self.OnCacheUpdate)
		self.application.gui.Binder(self.application.gui.SelectObjectEvent, self.OnSelectObject)

		#self.Panel = Panel
		self.OnSelect()

	# Functions to manipulate the Tree controls....
	# FIXME: These should be part of the tree controls themselves...
	#################################################################################
	def TreeAddCategory(self, tree, category):
		child = tree.AppendItem(tree.GetRootItem(), category.name)
		tree.SetPyData(child, category)
		tree.SetItemImage(child, 0, wx.TreeItemIcon_Normal)
		tree.SetItemImage(child, 1, wx.TreeItemIcon_Expanded)
		return child

	def TreeAddItem(self, tree, category, object):
		child = tree.AppendItem(category, object.name)
		tree.SetPyData(child, object)
		tree.SetItemImage(child, 2, wx.TreeItemIcon_Normal)

	def TreeColourItem(self, tree, item, mode):
		if mode == "normal":
			tree.SetItemTextColour(item, wx.Color(0, 0, 0))
		elif mode == "updating":
			tree.SetItemTextColour(item, wx.Color(0, 0, 255))
		elif mode == "removing":
			tree.SetItemTextColour(item, wx.Color(255, 0, 0))

	def TreeSelectedData(self, tree, criteria):
		selected = []
		for tid in tree.GetSelections():
			object = self.ComponentsTree.GetPyData(tid)
			if isinstance(object, criteria):
				selected.append(object)
		return selected

	# Functions to build PartsList of the interface
	#################################################################################
	def DesignsFilter(self):
		filter = self.DesignsSearch.GetValue()
		if len(filter) == 0:
			return "*"
		if filter[-1] != '*':
			return '*'+filter.lower()+'*'
	DesignsFilter = property(DesignsFilter)
	
	def BuildDesignList(self, evt=None):
		self.DesignsTree.DeleteAllItems()

		root = self.DesignsTree.AddRoot(_("Designs"))
		self.DesignsTree.SetPyData(root, None)
		self.DesignsTree.SetItemImage(root, 0, wx.TreeItemIcon_Normal)
		self.DesignsTree.SetItemImage(root, 1, wx.TreeItemIcon_Expanded)

		tmpcache = self.application.cache
		for category in tmpcache.categories.values():
			categoryitem = self.TreeAddCategory(self.DesignsTree, category)

			for design in tmpcache.designs.values():
				if category.id in design.categories:
					# Filter the list..
					from fnmatch import fnmatch as match
					if match(design.name.lower(), self.DesignsFilter.lower()):
						self.TreeAddItem(self.DesignsTree, categoryitem, design)

			if not self.DesignsTree.ItemHasChildren(categoryitem):
				self.DesignsTree.Delete(categoryitem)
		
		for design in tmpcache.designs.values():
			# If the design has any categories, don't add it.
			if len(design.categories) >= 0:
				continue
				
			# Filter the list..
			from fnmatch import fnmatch as match
			if match(design.name.lower(), self.DesignsFilter.lower()):
				self.TreeAddItem(self.DesignsTree, root, design)

		blank = Design(-1, -1, 0, [1], _("NewDesign"), "", -1, -1, [], "", [])
		self.TreeAddItem(self.DesignsTree, root, blank)

		self.DesignsTree.SortChildren(self.DesignsTree.GetRootItem())
		self.DesignsTree.ExpandAll()

	def ComponentsFilter(self):
		filter = self.ComponentsSearch.GetValue()
		if len(filter) == 0:
			return "*"
		if filter[-1] != '*':
			return '*'+filter.lower()+'*'
	ComponentsFilter = property(ComponentsFilter)

	def BuildCompList(self, evt=None):
		#FIXME: This is broken as it does not take into account the change of position of items
		#selected = self.ComponentsTree.GetSelection()

		self.ComponentsTree.DeleteAllItems()

		root = self.ComponentsTree.AddRoot(_("Components"))
		self.ComponentsTree.SetPyData(root, None)
		self.ComponentsTree.SetItemImage(root, 0, wx.TreeItemIcon_Normal)
		self.ComponentsTree.SetItemImage(root, 1, wx.TreeItemIcon_Expanded)

		tmpcache = self.application.cache
		for category in tmpcache.categories.values():
			categoryitem = self.TreeAddCategory(self.ComponentsTree, category)

			for component in tmpcache.components.values():
				if category.id in component.categories:
					# Filter the list..
					from fnmatch import fnmatch as match
					if match(component.name.lower(), self.ComponentsFilter.lower()):
						self.TreeAddItem(self.ComponentsTree, categoryitem, component)

			if not self.ComponentsTree.ItemHasChildren(categoryitem):
				self.ComponentsTree.Delete(categoryitem)

		self.ComponentsTree.SortChildren(self.ComponentsTree.GetRootItem())
		self.ComponentsTree.ExpandAll()
	
		# FIXME: This is broken as it does not take into account the change of position of items
#		if selected:
#			self.ComponentsTree.SelectItem(selected)
#			self.ComponentsTree.EnsureVisible(selected)

	def BuildHeaderPanel(self, design):
		# Set the title
		self.TitleStatic.SetLabel(design.name)
		self.TitleEditable.SetValue(design.name)
		
		# Set the Used
		self.Used.SetLabel(unicode(design.used))
		if design.used == -1:
			self.Used.SetForegroundColour(wx.Color(255, 0, 0))
		elif design.used == 0:
			self.Used.SetForegroundColour(wx.Color(0, 255, 0))
		else:
			self.Used.SetForegroundColour(wx.Color(0, 0, 0))

		# Set the Categories
		c = "Categories: "
		for cid in design.categories:
			c += self.application.cache.categories[cid].name + ", "
		c = c[:-2]
		self.CategoriesLabel.SetLabel(c)

		
	def BuildPropertiesPanel(self, design):
		SIZER_FLAGS = wx.EXPAND|wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL
		tmpcache = self.application.cache
		
		# Remove the previous Panel and stuff
		if hasattr(self, 'properties'):
			self.properties.Hide()
			self.design_ps.Remove(self.properties)
			self.properties.Destroy()
			del self.properties
		if hasattr(self, 'DesignPropertyGroup1'):
			self.DesignProperties.Hide()
			self.designsizer.Remove(self.DesignPropertyGroup1)
			self.DesignPropertyGroup1.Destroy()
			del self.DesignPropertyGroup1

		# Create a new Panel
		Panel = wx.Panel(self.DesignProperties, -1)
		sizer = wx.BoxSizer(wx.VERTICAL) 
		Panel.SetSizer(sizer)
		Panel.SetSize((350, 390))

		# Sort the properties into category groups
		properties = {}
		for pid, pstring in design.properties:
			property = tmpcache.properties[pid]
			
			for cid in property.categories:
				if not properties.has_key(cid):
					properties[cid] = []
				properties[cid].append((property, pstring))
		
		if len(properties) <= 0:
			self.DesignProperties.Hide()
			return
		
		for cid in properties.keys():
			category = tmpcache.categories[cid]

			# The box around the properties in the category
			box = wx.StaticBox(Panel, -1, category.name)
			box.SetFont(wx.local.normalFont)
			box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
			sizer.Add(box_sizer, 1, SIZER_FLAGS, 5)

			# The properties
			prop_sizer = wx.FlexGridSizer( 0, 2, 0, 0 )
			box_sizer.Add(prop_sizer, 1, SIZER_FLAGS, 5)

			for property, pstring in properties[cid]:
				# Property name
				name = wx.StaticText(Panel, -1, property.display_name)
				name.SetFont(wx.local.tinyFont)
				prop_sizer.Add(name, 0, SIZER_FLAGS|wx.ALIGN_RIGHT, 5)

				# Property value
				value = wx.StaticText(Panel, -1, pstring)
				value.SetFont(wx.local.tinyFont)
				prop_sizer.Add(value, 1, SIZER_FLAGS|wx.ALIGN_RIGHT, 5)
				
				self.design_ps.Layout()
				Panel.Layout()
		self.DesignProperties.Show()
		self.design_ps.Show(Panel)
		self.DesignProperties.SetMinSize(Panel.GetSize()-(0, 40))
		Panel.SetSize((Panel.GetBestSize()[0], self.DesignProperties.GetSize()[1]-10))
		self.SetSize(self.GetBestSize())

		self.properties = Panel

	def BuildPartsPanel(self, design):
		# Populate the PartsList list
		self.PartsList.DeleteAllItems()
		for cid, number in design.components:
			component = self.application.cache.components[cid]
		
			self.PartsList.InsertStringItem(0, unicode(number))
			self.PartsList.SetStringItem(0, 1, component.name)

	def TitleChanged(self, evt):
		design = self.selected
		design.name = evt.GetString()

	# Functions to update the component lists
	#################################################################################
	def OnAddMany(self, evt):
		"""\
		Pops up a selection box to ask for how many to ComponentsAdd.
		"""
		self.OnAdd(evt, amount)
	
	def OnAdd(self, evt, amount=1):
		"""\
		Adds components to the current design.
		"""
		# Figure out if a component is selected
		components = self.TreeSelectedData(self.ComponentsTree, Component)
		
		dc = DesignCalculator(self.application.cache, self.selected)
		for component in components:
			dc.change(component, amount)
		dc.update()
	
		if self.selected.used == -1:
			if amount > 1 or len(components) > 1:
				reason = self.selected.feedback + _("\nWould you like to continue adding these components?")
			else:
				reason = self.selected.feedback + _("\nWould you like to continue adding this component?")
			dlg = wx.MessageDialog(self, reason, _('Design Warning'), wx.YES_NO|wx.NO_DEFAULT|wx.ICON_ERROR)
			
			if dlg.ShowModal() == wx.ID_NO:
				for component in components:
					dc.change(component, -amount)
				dc.update()

			dlg.Destroy()

		# Redisplay the panels
		self.BuildPartsPanel(self.selected)
		self.BuildPropertiesPanel(self.selected)

	# Functions to change the mode of the dialog
	#################################################################################
	def OnCategories(self, evt=None):
		if self.CategoriesWindow.IsShown():
			pass
		else:
			design = self.selected
			catlist = []
			for category in self.application.cache.categories.values():
				catlist.append((category.name, category.id))
				
			self.CategoriesWindow.SetOptions(catlist)
			
			checkedlist = []
			for category in self.application.cache.categories.values():
				if category.id in design.categories:
					checkedlist.append(category.name)
					
			self.CategoriesWindow.SetCheckedStrings(checkedlist)
			
			self.CategoriesWindow.Show()
	
	def SetSelectedCategories(self, categories):
		design = self.selected
		design.categories = categories
		print design.categories
		# Add the design to ones which are being updated
		self.updating.append(design.id)
		#self.application.Post(self.application.cache.CacheDirtyEvent("designs", "change", design.id, design), source=self)
	
	def OnEdit(self, evt=None):
		if self.selected.used > 0:
			return
	
		# Disable the select side
		self.DesignsTree.Disable()

		# Show the component bar
		self.grid.Show(self.ComponentsPanel)
		self.grid.Show(self.ComponentsSearch)
		self.ComponentsPanel.SetSize((0, 0))
		self.ComponentsSearch.SetSize((0, 0))
		self.ComponentsPanel.Layout()
		
		# Make the title and description editable
		self.top.Show(self.TitleEditable)
		self.top.Hide(self.StaticTitlePanel)
		self.top.Layout()

		# Disable Edit, Duplicate, Delete
		self.Edit.Disable()
		self.Duplicate.Disable()
		self.Delete.Disable()
		
		self.Categories.Show()

		# Enable the Save, Revert
		self.Revert.Enable()
		self.Revert.SetDefault()
		self.Save.Enable()

		# Re-layout everything
		self.grid.Layout()

		# Start the timer so that Add -> Add Many
		self.ShiftStart()

	def OnSave(self, evt):
		design = self.selected

		# Is this a new design?
		if design.id == -1:
			self.creating.append(design.name)
			self.application.Post(self.application.cache.CacheDirtyEvent("designs", "create", -1, design), source=self)
			self.selected = None
		else:
			# Add the design to ones which are being updated
			self.updating.append(design.id)

			# Change the colour on the side
			for item in self.DesignsTree.FindAllByData(design, comparebyid):
				self.TreeColourItem(self.DesignsTree, item, "updating")
	
			# Tell the world about the change
			self.application.Post(self.application.cache.CacheDirtyEvent("designs", "change", design.id, design), source=self)

		self.OnSelect(None)

	def OnDuplicate(self, evt):
		design = self.selected
		self.creating.append(design.name)
		self.application.Post(self.application.cache.CacheDirtyEvent("designs", "create", -1, design), source=self)
		self.selected = None

	def OnRemove(self, evt):
		design = self.selected

		# Add the design to ones which are being updated
		self.updating.append(design.id)
		
		# Change the colour on the side
		for item in self.DesignsTree.FindAllByData(design, comparebyid):
			self.TreeColourItem(self.DesignsTree, item, "removing")
			
		self.application.Post(self.application.cache.CacheDirtyEvent("designs", "remove", design.id, design.id), source=self)

	def OnSelect(self, evt=None):
		# Stop any running Shift timers
		self.ShiftStop()
	
		# Enable the selection side
		self.DesignsTree.Enable()

		# Hide the component bar
		self.grid.Hide(self.ComponentsPanel)
		self.grid.Hide(self.ComponentsSearch)
		self.ComponentsPanel.SetSize((0,0))
		self.ComponentsSearch.SetSize((0,0))
		self.ComponentsPanel.Layout()
		self.TitleEditable.SetMinSize(self.TitlePanel.GetSize() - (self.Used.GetSize()[0], 0))

		# Make the title and description uneditable
		self.top.Hide(self.TitleEditable)
		self.top.Show(self.StaticTitlePanel)
		self.top.Layout()

		# Disable Save, Revert
		self.Revert.Disable()
		self.Save.Disable()

		# Re-layout everything
		self.grid.Layout()

		self.OnSelectObject()

	def OnSelectObject(self, evt=None):
		selected = self.TreeSelectedData(self.DesignsTree, Design)
		if len(selected) != 1:
			self.selected = None
		else:
			if selected[0].id in self.updating:
				self.selected = None
			else:
				self.selected = deepcopy(selected[0])

		if self.selected == None:
			# Clear the title
			self.TitleStatic.SetLabel("")

			# Hide the design
			self.grid.Hide(self.DesignPanel)
			self.grid.Layout()
			
			# Disable the buttons
			self.Edit.Disable()
			self.Categories.Disable()
			self.Duplicate.Disable()
			self.Delete.Disable()
			return

#		# Recalculate all the properties if they are empty
#		if len(self.selected.properties) == 0:
#			self.Recalculate()

		# Build the Header Panel
		self.BuildHeaderPanel(self.selected)

		# Show the PartsList list
		self.grid.Show(self.DesignPanel)
		self.grid.Layout()

		# Populate the PartsList list
		self.BuildPartsPanel(self.selected)
		
		# Populate the properties
		self.BuildPropertiesPanel(self.selected)

		self.Categories.Hide()

		# Set if Edit can work
		if self.selected.used <= 0:
			self.Edit.Enable()
			self.Edit.SetDefault()
			self.Categories.Enable()

			self.Duplicate.Enable()
			self.Delete.Enable()
		else:
			self.Edit.Disable()
			self.Delete.Disable()
			self.Categories.Disable()

			self.Duplicate.Enable()
			self.Duplicate.SetDefault()
		
		# Re-layout everything
		self.grid.Layout()

	def OnCacheUpdate(self, evt=None):
		# Full cache update, rebuild everything
		if evt.what is None:
			self.BuildDesignList()
			self.BuildCompList()

		if evt.what is "designs":
			design = evt.change
		
			if evt.action in ("change", "remove"):
				for item in self.DesignsTree.FindAllByData(design, comparebyid):
					categoryitem = self.DesignsTree.GetItemParent(item)
					self.DesignsTree.Delete(item)
					
					# Remove the category if it will be empty
					if self.DesignsTree.ItemHasChildren(categoryitem):
						self.DesignsTree.Delete(categoryitem)
				
			if evt.action in ("change", "create"):
				if not design.name in self.creating and not design.id in self.updating:
					return
				
				for categoryid in design.categories:
					# Check the category exists
					parent = self.DesignsTree.FindItemByData((Category, categoryid), comparetoid)
					if parent is None:
						parent = self.TreeAddCategory(self.DesignsTree, self.application.cache.categories[categoryid])
					
					# Add the new design under this category
					self.TreeAddItem(self.DesignsTree, parent, design)

			if design.name in self.creating:
				self.creating.remove(design.name)

			if design.id in self.updating:
				self.updating.remove(design.id)

			self.BuildDesignList()
			self.DesignsTree.SortChildren(self.DesignsTree.GetRootItem())
	
	def OnDesignsSearchCancel(self, evt):
		self.DesignsSearch.SetValue("")
		self.BuildDesignList()
		
	def OnComponentsSearchCancel(self, evt):
		self.ComponentsSearch.SetValue("")
		self.BuildCompList()
