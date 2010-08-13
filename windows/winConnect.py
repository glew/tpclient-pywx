"""\
This module contains the "connect" window which lets a
person enter the server/username/password.
"""

# Python imports
import string

# wxPython Imports
import wx
import wx.gizmos
import wx.wizard as wiz
import wx.lib.filebrowsebutton as filebrowse
import types

from extra.decorators import freeze_wrapper
from extra.Opener import open

# Local Imports
from winBase import winBaseXRC
from xrc.winConnect import winConnectBase
from xrc.configConnect import configConnectBase
from xrc.SinglePlayerWizard import *
from utils import *

from requirements import graphicsdir

from tp.netlib.client import url2bits
from tp.client.SinglePlayer import DownloadList, SinglePlayerGame

# FIXME: The game really isn't part of the username, it's part of the server information
# You could be playing multiple different games on the same server!

class usernameMixIn:
	def __init__(self):
		self.Username.Bind(wx.EVT_CHAR, self.OnUsernameChar)
		self.Game.Bind(wx.EVT_CHAR, self.OnGameChar)

	@freeze_wrapper
	def OnGameShow(self, evt):
		if self.GameShow.GetValue():
			self.SetUsername(self.Username.GetValue())
			# Show the game boxes
			self.GameTitle.Show()
			self.Game.Show()
	
		else:
			self.SetUsername("%s@%s" % (self.Username.GetValue(), self.Game.GetValue()))
			# Hide the game boxes
			self.GameTitle.Hide()
			self.Game.Hide()

		self.Panel.Layout()
		size = self.Panel.GetBestSize()
		self.SetClientSize(size)

	def OnUsernameChar(self, evt):
		if isinstance(evt.KeyCode, (int,long)):
			key = evt.KeyCode
		else: 
			key = evt.KeyCode()
		if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
			evt.Skip()
			return
		if chr(key) in string.letters+string.digits:
			evt.Skip()
			return

		if not self.GameShow.GetValue():
			if chr(key) == '@':
				evt.Skip()
				return
		return

	def OnGameChar(self, evt):
		if isinstance(evt.KeyCode, (int,long)):
			key = evt.KeyCode
		else: 
			key = evt.KeyCode()
		if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
			evt.Skip()
			return
		if chr(key) in string.letters+string.digits:
			evt.Skip()
			return
		return

	def GetUsername(self):
		username = self.Username.GetValue()
		game     = self.Game.GetValue().strip()
		if self.GameShow.GetValue() and len(game) > 0:
			return "%s@%s" % (username, game)
		else:
			return username

	def GetUsernameGame(self):
		username = self.Username.GetValue()
		game     = self.Game.GetValue().strip()
	
		return (username, game)

	def SetUsername(self, value):
		# Split the part after the @ into the game box
		username = value.split('@')
		if len(username) == 2:
			username, game = username
		else:
			username = username[0]
			game = ""

		if self.GameShow.GetValue() or len(game) == 0:
			self.Username.SetValue(username)
		else:
			self.Username.SetValue("%s@%s" % (username, game))
		self.Game.SetValue(game)

class configConnect(configConnectBase, usernameMixIn):
	def __init__(self, *args, **kw):
		configConnectBase.__init__(self, *args, **kw)

		usernameMixIn.__init__(self)
		self.Panel = self

		self.GameShow.MoveAfterInTabOrder(self.Password)
		self.Servers.SetMinSize(wx.Size(300, -1))
		self.Layout()

		# Use better Art Graphics for the EditableList
		custom = {
			"Del":	wx.ART_DELETE,
			"New":	wx.ART_NEW,
			"Up":	wx.ART_GO_UP,
			"Down":	wx.ART_GO_DOWN,
			"Edit":	wx.ART_REPORT_VIEW,}

		for name, id in custom.items():
			bmp = wx.ArtProvider_GetBitmap(id, wx.ART_TOOLBAR, (16,16))

			if not bmp.Ok():
				continue

			button = getattr(self.Servers, "Get%sButton" % name)()
			button.SetBitmapLabel(bmp)
			button.SetBitmapDisabled(bmp)

	def EnableDetails(self, label):
		self.ServerDetails.SetLabel(_("Login for %s") % (label,))
		self.Username.Enable()
		self.Game.Enable()
		self.GameShow.Enable()
		self.Password.Enable()
		self.AutoConnect.Enable()

	def DisableDetails(self):
		#self.ServerDetails.SetLabel(" ")
		self.Username.Disable()
		self.Username.SetValue("")
		self.Game.Disable()
		self.Game.SetValue("")
		self.GameShow.Disable()
		self.Password.Disable()
		self.Password.SetValue("")
		self.AutoConnect.Disable()


# single player wizard

class OptValidator(wx.PyValidator):
	def __init__(self, type = None, pyVar = None):
		wx.PyValidator.__init__(self)
		self.type = type
		self.Bind(wx.EVT_CHAR, self.OnChar)

		self.allowed = { 'I' : string.digits,
						 'S' : string.digits + string.letters + '-_',
			}
	
	def Clone(self):
		return OptValidator(self.type)
	
	def Validate(self, win):
		tc = self.GetWindow()
		val = tc.GetValue()
		for x in val:
			if x not in self.allowed[self.type]:
				return False
		return True
	
	def OnChar(self, event):
		key = event.GetKeyCode()
		if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
			event.Skip()
			return
		if chr(key) in self.allowed[self.type]:
			event.Skip()
			return
		return
	
	def TransferToWindow(self):
		return True

	def TransferFromWindow(self):
		return True

class OptFileBrowseButton(filebrowse.FileBrowseButton):
	def __init__ (self, parent, id = -1,
				  pos = wx.DefaultPosition,
				  size = wx.DefaultSize,
				  style = wx.TAB_TRAVERSAL,
				  name = 'fileBrowseButton',
		):
		filebrowse.FileBrowseButton.__init__(self, parent, id, pos, size, style,
			"", _("Browse"), _("Type filename or click browse to choose."),
			_("Choose a File"), ".", "", "*.*", wx.OPEN, lambda x:x, 0)
	
	def createDialog(self, parent, id, pos, size, style, name=""):
		wx.Panel.__init__(self, parent, id, pos, size, style, name)
		self.SetMinSize(size)
		box = wx.BoxSizer(wx.HORIZONTAL)
		self.textControl = self.createTextControl()
		box.Add( self.textControl, 1, wx.CENTER, 0)
		self.browseButton = self.createBrowseButton()
		box.Add(self.browseButton, 0, wx.LEFT|wx.CENTER, 5)
		outsidebox = wx.BoxSizer(wx.VERTICAL)
		outsidebox.Add(box, 1, wx.EXPAND|wx.ALL, 0)
		outsidebox.Fit(self)
		self.SetAutoLayout(True)
		self.SetSizer(outsidebox)
		self.Layout()
		if type(size) == types.TupleType:
			size = apply(wx.Size, size)
		self.SetDimensions(-1, -1, size.width, size.height, wx.SIZE_USE_EXISTING)


def PopulateOpts(paramlist, page, sizer, label=None):
	sizer.Clear(deleteWindows = True)
	page.Params = {}
	if len(paramlist) > 0:
		if label is not None:
			label.Show()
		for opt in paramlist.keys():
			sizer.Add(wx.StaticText(page, -1, paramlist[opt]['longname']), 1, flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
			if paramlist[opt]['default'] is None:
				default = ''
			else:
				default = str(paramlist[opt]['default'])
			if paramlist[opt]['type'] == 'I' or paramlist[opt]['type'] == 'S':
				page.Params[opt] = wx.TextCtrl(page, -1, default,
											   validator = OptValidator(paramlist[opt]['type']))
			elif paramlist[opt]['type'] == 'F':
				page.Params[opt] = OptFileBrowseButton(page, -1)
			elif paramlist[opt]['type'] == 'B':
				page.Params[opt] = wx.CheckBox(page, -1, default)
			sizer.Add(page.Params[opt], 1, flag=wx.EXPAND)
	else:
		if label is not None:
			label.Hide()
	sizer.Layout()

class StartPage(StartPageBase):
	def __init__(self, parent, *args, **kw):
		StartPageBase.__init__(self, parent, *args, **kw)
		self.PageDesc.SetLabel(_("""\
This wizard sets up a single player Thousand Parsec game using the servers, \
rulesets, and AI clients installed locally on your system."""))
		self.PageDesc.Wrap(self.PageDesc.GetSize()[0])

		# ensure there are some servers/rulesets installed
		if len(parent.game.rulesets) > 0:
			self.ProceedDesc.SetLabel(_("""\
You have at least one server installed on your system. Click the link below \
to install more."""))
			self.ProceedDesc.Wrap(self.ProceedDesc.GetSize()[0])
			self.proceed = True
		else:
			self.ProceedDesc.SetLabel(_("""\
No servers were found on your system. You need a server to play a single \
player game. Click the link below for a list and installation instructions."""))
			self.ProceedDesc.Wrap(self.ProceedDesc.GetSize()[0])
			self.proceed = False

		self.DownloadLink.SetURL(parent.dllist.linkurl('server'))

	def GetNext(self):
		if self.proceed:
			return self.next
		return None

class LoadPage(LoadPageBase):
        def __init__(self, parent, *args, **kw):
                LoadPageBase.__init__(self, parent, *args, **kw)

                self.PageDesc.SetLabel(_("""\
Choose a savefile to load a previous game. Leave blank to continue creating a new game."""))
                self.PageDesc.Wrap(self.PageDesc.GetSize()[0])

        def GetNext(self):
                next = self.next
                while next.skip:
                        next = next.next
                return next

        def RefreshOpts(self):
                loadparam = {'savefile': {'default': None, 'commandstring': '', 'type': 'F', 'description': 'Savefile to load.', 'longname': 'Savefile'}}
                PopulateOpts(loadparam, self, self.LoadOptSizer)

        def OnLoad(self, event):
                # load savefile
                if self.Savefile.GetValue():
                        self.parent.game.load(self.Savefile.GetValue())

                        # show savefile components
                        self.SavefileDesc.SetLabel("""\
Loaded file.""")

                        # if no errors, should skip subsequent pages
                        self.next.skip = True
                        self.next.next.skip = True
                        self.next.next.next.skip = True
                        self.next.next.next.next.skip = True
                        self.next.next.next.next.next.skip = True
                        self.next.next.next.next.next.next.skip = True
                        # else skip false
                else:
                        # reset game fields


                        self.SavefileDesc.Hide()
                

class RulesetPage(RulesetPageBase):
	def __init__(self, parent, *args, **kw):
		RulesetPageBase.__init__(self, parent, *args, **kw)
		for ruleset in parent.game.rulesets:
			rs = parent.game.ruleset_info(ruleset)['longname']
			self.Ruleset.Insert(rs, self.Ruleset.GetCount())

	def GetNext(self):
		next = self.next
		while next.skip:
			next = next.next
		return next

	def OnRuleset(self, event):
		# set ruleset
		self.parent.game.rname = self.parent.game.rulesets[self.Ruleset.GetSelection()]

		# set current game server to first supported.
		self.parent.game.sname = self.parent.game.list_servers_with_ruleset()[0]

		# show ruleset description
		self.RulesetDesc.SetLabel(self.parent.game.ruleset_info()['description'])
		self.RulesetDesc.Wrap(self.RulesetDesc.GetSize()[0])

		# show additional downloads
		if len(self.parent.dllist.rulesets) > len(self.parent.game.rulesets):
			self.DownloadDesc.SetLabel(_("""\
Additional rulesets are available by installing other servers. Click the link \
below for a list and installation instructions.""")) 
			self.DownloadDesc.Wrap(self.DownloadDesc.GetSize()[0])
			self.DownloadLink.SetURL(self.parent.dllist.linkurl('server'))
		else:
			self.DownloadDesc.Hide()
			self.DownloadLink.Hide()

		# If multiple servers provide a ruleset, let the player select which
		# server to use.
		self.next.servers = self.parent.game.list_servers_with_ruleset()
		if len(self.next.servers) == 1:
			self.next.skip = True
		else:
			self.next.skip = False

		self.next.Server.SetItems([])
		for server in self.next.servers:
			ss = self.parent.game.server_info(server)['longname']
			self.next.Server.Insert(ss, self.next.Server.GetCount())
		self.next.Server.SetSelection(0)
		self.next.OnServer(None)

		# populate ruleset parameter page
		if len(self.parent.game.list_rparams()) == 0:
			self.next.next.skip = True
		else:
			self.next.next.skip = False
			self.next.next.PageDesc.SetLabel(_("""\
Configure options for the %(longname)s ruleset (leave blank to use default):""") % self.parent.game.ruleset_info())
			self.next.next.PageDesc.Wrap(self.next.next.PageDesc.GetSize()[0])
			self.next.next.RefreshOpts()

		# populate opponent page
		op = self.next.next.next.next
		op.aiclients = self.parent.game.list_aiclients_with_ruleset()
		if len(op.aiclients) == 0:
			op.skip = True
			op.next.skip = False
			op.next.PageDesc.SetLabel(_("""\
You do not appear to have any AI clients installed which support the \
%(longname)s ruleset. If you proceed, you will have no opponents in the game. \
Click the link below for a list and installation instructions.""") % self.parent.game.ruleset_info(self.parent.game.rname))
		else:
			op.skip = False
			op.next.skip = True

		op.AIClient.SetItems([])

		for aiclient in op.aiclients:
			os = self.parent.game.aiclient_info(aiclient)['longname']
			op.AIClient.Insert(os, op.AIClient.GetCount())

class ServerPage(ServerPageBase):
	def __init__(self, parent, *args, **kw):
		ServerPageBase.__init__(self, parent, *args, **kw)
		self.PageDesc.SetLabel(_("Multiple servers implement the ruleset you selected. Please select a server to use:"))

	def GetNext(self):
		next = self.next
		while next.skip:
			next = next.next
		return next

	def OnServer(self, event):
		# show server description
		self.parent.game.sname = self.servers[self.Server.GetSelection()]
		self.ServerDesc.SetLabel(self.parent.game.server_info()['description'])
		self.ServerDesc.Wrap(self.ServerDesc.GetSize()[0])

		# show info about ruleset implementation
		rinfo = self.parent.game.ruleset_info()
		self.ServerRulesetDesc.SetLabel(_("Implements %(longname)s version %(version)s.") % rinfo)
		self.ServerDesc.Wrap(self.ServerDesc.GetSize()[0])

		# populate server parameter page
		if len(self.parent.game.list_sparams()) == 0:
			self.next.next.skip = True
		else:
			self.next.next.skip = False

		self.next.next.RefreshOpts()

class RulesetOptsPage(RulesetOptsPageBase):
	def __init__(self, parent, *args, **kw):
		RulesetOptsPageBase.__init__(self, parent, *args, **kw)
		self.RulesetOptSizer = self.SizerRef.GetContainingSizer()

	def GetNext(self):
		next = self.next
		while next.skip:
			next = next.next
		return next

	def GetPrev(self):
		prev = self.prev
		while prev.skip:
			prev = prev.prev
		return prev

	def RefreshOpts(self):
		"""\
		Clear and repopulate the parameter fields.
		"""
		PopulateOpts(self.parent.game.list_rparams(), self, self.RulesetOptSizer)

class ServerOptsPage(ServerOptsPageBase):
	def __init__(self, parent, *args, **kw):
		ServerOptsPageBase.__init__(self, parent, *args, **kw)
		self.PageDesc.SetLabel(_("Configure options for this server (leave blank to use default):"))
		self.PageDesc.Wrap(self.PageDesc.GetSize()[0])
		self.ServerOptSizer = self.SizerRef.GetContainingSizer()

	def GetNext(self):
		next = self.next
		while next.skip:
			next = next.next
		return next

	def GetPrev(self):
		prev = self.prev
		while prev.skip:
			prev = prev.prev
		return prev

	def RefreshOpts(self):
		"""\
		Clear and repopulate the parameter fields.
		"""
		PopulateOpts(self.parent.game.list_sparams(), self, self.ServerOptSizer)

class OpponentPage(OpponentPageBase):
	Columns = [_("Name"), _("Type")]
	Columns_Sizes = [100, wx.LIST_AUTOSIZE]

	def __init__(self, parent, *args, **kw):
		OpponentPageBase.__init__(self, parent, *args, **kw)

		self.AIOptSizer = self.SizerRef.GetContainingSizer()
		self.Box = self.BoxRef.GetContainingSizer().GetStaticBox()

		self.Opponents.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnOpponentsSelect)


	def GetNext(self):
		next = self.next
		while next.skip:
			next = next.next
		return next

	def GetPrev(self):
		prev = self.prev
		while prev.skip:
			prev = prev.prev
		return prev
	
	def OnAIClient(self, event):
		"""\
		Show AI client description.
		"""
		self.AIClientDesc.SetLabel(self.parent.game.aiclient_info(self.parent.game.aiclients[self.AIClient.GetSelection()])['description'])
		self.AIClientDesc.Wrap(self.AIClientDesc.GetSize()[0])
		self.RefreshOpts(self.parent.game.aiclients[self.AIClient.GetSelection()])

	def OnOpponentsSelect(self, event):
		opponent = self.Opponents.GetItemPyData(event.GetIndex())
		self.Populate(opponent)

		self.New.Hide()

		self.Save.Show()
		self.Delete.Show()

		self.Box.SetLabel(_("Edit Opponent"))

		self.Layout()

	def OnDelete(self, event):
		self.Opponents.DeleteItem(self.Opponents.GetSelected()[0])

		self.ResetAdd()

	def OnSave(self, event):
		self.AddOpponent(self.Opponents.GetSelected()[0])
		self.ResetAdd()

	def OnNew(self, event):
		"""\
		Called when the AI is added...
		"""
		self.AddOpponent(-1)
		self.ResetAdd()

	def AddOpponent(self, i):
		name = self.parent.game.aiclients[self.AIClient.GetSelection()]
		user = self.AIUser.GetValue()
		if len(user) == 0:
			# FIXME: Add a pop-up telling them to add a username.
			return

		# FIXME: Check that the username is not already used

		# Check the input values
		opponent = {
			'name': name,
			'user': user,
			'parameters': {}}

		# Get the optional parameters
		parameters = {}
		for opt in self.parent.game.list_aiparams(name).keys():
			opponent['parameters'][opt] = str(self.Params[opt].GetValue())

		if i == -1:
			i = self.Opponents.GetItemCount()
			self.Opponents.InsertStringItem(i, "")
		self.Opponents.SetStringItem(i, self.Columns.index(_("Name")), user)
		self.Opponents.SetStringItem(i, self.Columns.index(_("Type")), 
			self.parent.game.aiclient_info(name)['longname'])
		self.Opponents.SetItemPyData(i, opponent)
	
	def RefreshOpts(self, ainame):
		"""\
		Dynamically clear and repopulate parameter fields.

		@param ainame The name of the selected AI client.
		"""
		PopulateOpts(self.parent.game.list_aiparams(ainame), self, self.AIOptSizer, self.AIOptionsLabel)

	def Populate(self, opponent):
		"""\
		Populates the page with details about an opponent.

		@param opponent The opponent dict object (can be popped off the opponent list).
		"""
		# populate username
		self.AIUser.SetValue(opponent['user'])

		# determine which AI client selection this is
		for i, ainame in enumerate(self.parent.game.aiclients):
			if opponent['name'] == ainame:
				break
		self.AIClient.SetSelection(i)

		# show and populate options
		self.RefreshOpts(opponent['name'])
		for opt in opponent['parameters'].keys():
			self.Params[opt].SetValue(opponent['parameters'][opt])

	def ResetAdd(self):
		self.Opponents.SetSelected([])

		# clear name and client selection
		self.AIUser.SetValue('')
		self.AIClient.SetSelection(0)
		self.OnAIClient(None)

		# clear AI client parameters
		self.AIOptSizer.Clear(deleteWindows = True)
		self.Params = {}

		self.New.Show()
		self.Save.Hide()
		self.Delete.Hide()
		self.Box.SetLabel(_("New Opponent"))

		self.Layout()

	def Reset(self):
		"""\
		Resets the page.
		"""
		self.ResetAdd()

		# write opponent list
		self.WriteOpponentList()

	def WriteOpponentList(self):
		"""\
		Writes a list of current opponents into the page description text.
		"""
		self.Opponents.ClearAll()
		# Add the columns
		for i, name in enumerate(self.Columns):
			self.Opponents.InsertColumn(i, name)
		# Set the column widths
		for i, name in enumerate(self.Columns):
			self.Opponents.SetColumnWidth(i, self.Columns_Sizes[i])

		for i, opponent in enumerate(self.parent.game.opponents):
			self.Opponents.InsertStringItem(i, "")
			self.Opponents.SetStringItem(i, self.Columns.index(_("Name")), opponent['user'])
			self.Opponents.SetStringItem(i, self.Columns.index(_("Type")),
				self.parent.game.aiclient_info(opponent['name'])['longname'])
			self.Opponents.SetItemPyData(i, opponent)

	
class NoOpponentPage(NoOpponentPageBase):
	def __init__(self, parent, *args, **kw):
		NoOpponentPageBase.__init__(self, parent, *args, **kw)
		self.DownloadLink.SetURL(parent.dllist.linkurl('ai'))

	def GetPrev(self):
		prev = self.prev
		while prev.skip:
			prev = prev.prev
		return prev

class EndPage(EndPageBase):
	def __init__(self, parent, *args, **kw):
		EndPageBase.__init__(self, parent, *args, **kw)
		self.PageDesc.SetLabel(_("The Thousand Parsec client will now connect to your local single player game."))
		self.PageDesc.Wrap(self.PageDesc.GetSize()[0])

	def GetPrev(self):
		prev = self.prev
		while prev.skip:
			prev = prev.prev
		return prev

class SinglePlayerWizard(SinglePlayerWizardBase):
	def __init__(self, parent, *args, **kw):
		kw['bitmap'] = wx.Image(os.path.join(graphicsdir, "sidebar.bmp")).ConvertToBitmap()
		SinglePlayerWizardBase.__init__(self, parent, *args, **kw)

		self.parent = parent

		self.parent.application.game = SinglePlayerGame()
		self.dllist = DownloadList()
		self.game = self.parent.application.game

		self.pages = []

		self.AddPage(StartPage(self))
                self.AddPage(LoadPage(self))
		self.AddPage(RulesetPage(self))
		self.AddPage(ServerPage(self))
		self.AddPage(RulesetOptsPage(self))
		self.AddPage(ServerOptsPage(self))
		self.AddPage(OpponentPage(self))
		self.AddPage(NoOpponentPage(self))
		self.AddPage(EndPage(self))

		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)
		self.Bind(wx.wizard.EVT_WIZARD_CANCEL, self.OnCancelWizard)
		self.Bind(wx.EVT_HYPERLINK, self.OnLink)

	def AddPage(self, page):
		"""\
		Adds a page to the wizard and chains it.

		@param page The wxWizardPage object to add.
		"""
		i = len(self.pages)
		self.pages.append(page)
		if i > 0:
			self.pages[i].SetPrev(self.pages[i - 1])
			self.pages[i - 1].SetNext(self.pages[i])
		self.GetPageAreaSizer().Add(self.pages[i])


	def Run(self):
		"""\
		Runs the wizard.
		"""
		if self.RunWizard(self.pages[0]):
			return self.game.sname != '' and self.game.rname != ''

	def OnPageChanged(self, event):
		pass

	def OnPageChanging(self, event):
		if not(event.GetPage().validate()):
			event.Veto()
			return

		if isinstance(event.GetPage(), LoadPage) and self.game.sname == '':
			# initialize ruleset selection
			if len(self.game.rulesets) > 0:
				event.GetPage().next.Ruleset.SetSelection(0)
				event.GetPage().next.OnRuleset(None)
			return

		if isinstance(event.GetPage(), RulesetOptsPage):
			# store ruleset parameters
			self.game.rparams = {}
			for opt in self.game.list_rparams().keys():
				self.game.rparams[opt] = str(event.GetPage().Params[opt].GetValue())
			return
	
		if isinstance(event.GetPage(), ServerOptsPage):
			# store server parameters
			self.game.sparams = {}
			for opt in self.game.list_sparams().keys():
				self.game.sparams[opt] = str(event.GetPage().Params[opt].GetValue())
			# clear AI client page
			if not event.GetPage().next.skip:
				event.GetPage().next.Reset()
			return

		if isinstance(event.GetPage(), OpponentPage):
			self.game.opponents = []
			for i in range(0, event.GetPage().Opponents.GetItemCount()):
				opponent = event.GetPage().Opponents.GetItemPyData(i)
				self.game.add_opponent(**opponent)
			return

		if isinstance(event.GetPage(), EndPage):
			# similar to opponent page backward, but no page change veto required
			if not event.GetDirection() and not event.GetPage().prev.skip and len(self.game.opponents) > 0:
				i = len(self.game.opponents) - 1
				# populate page with last added opponent info
				event.GetPage().prev.Populate(self.game.opponents[i])
				# remove the last added opponent
				del self.game.opponents[i]
			return

	
	def OnCancelWizard(self, event):
		pass

	def OnLink(self, event):
		open(event.GetURL())


USERNAME=0
PASSWORD=1
AUTOCONNECT=2

# FIXME: The config should use proper URLs, currently you can't have more then one login to a server (and a server could have multiple games).

class winConnect(winConnectBase, winBaseXRC, usernameMixIn):
	title = _("Connect")

	def Post(*args):
		pass

	def __init__(self, application):
		winConnectBase.__init__(self, None)
		winBaseXRC.__init__(self, application)	
		usernameMixIn.__init__(self)

		self.attemps = 0

		self.GameShow.MoveAfterInTabOrder(self.Okay)

		self.Bind(wx.EVT_CLOSE, self.OnExit)
		self.Bind(wx.EVT_COMBOBOX, self.OnChangeServer, self.Server)

		self.singleplayer = False

	def OnChangeServer(self, evt):
		server = self.Server.GetValue()
		if server in self.config['servers']:
			self.SetUsername(self.config['details'][server][0])
			self.Password.SetValue(self.config['details'][server][1])

	def OnExit(self, evt):
		self.application.Exit()

	def SetFromConfig(self, server):
		if not server in self.config['servers'] or not self.config['details'].has_key(server):
			raise RuntimeError("Server is not in the config settings!")

		self.Server.SetValue(server)
		self.SetUsername(self.config['details'][server][USERNAME])
		self.Password.SetValue(self.config['details'][server][PASSWORD])
		return self.config['details'][server][AUTOCONNECT]

	def Show(self, show=True):
		if not show:
			return self.Hide()

		self.Panel.Layout()
		size = self.Panel.GetBestSize()
		self.SetClientSize(size)
		self.SetMinSize(size)

		self.CenterOnScreen(wx.BOTH)

		autoconnect = False

		# If the server value is empty we should populate with a server item
		if len(self.Server.GetValue()) == 0:
			# Check that no other server is also set to autoconnect
			for key in self.config['details'].keys():
				if not self.config['details'][key][AUTOCONNECT]: 
					continue
				self.SetFromConfig(key)
				autoconnect = True
			
			# Set the last tried server if there's a valid one
			if len(self.config['last_server']) > 0 and self.config['last_server'] in self.config['servers']:
				autoconnect = self.SetFromConfig(self.config['last_server'])

			# Is it still empty?
			if len(self.Server.GetValue()) == 0 and len(self.config['servers']) > 0:
				autoconnect = self.SetFromConfig(self.config['servers'][0])

		# FIXME: Gross hack
		if self.attemps == 0 and autoconnect:
			wx.CallAfter(self.OnOkay, None)
		self.attemps += 1

		return winBaseXRC.Show(self)

	def OnOkay(self, evt):
		self.application.StartNetwork()

		server = self.Server.GetValue()
		username = self.GetUsername()

		password = self.Password.GetValue()
		if server == "" or username == "":
			return

		# Save info about a connection attempt
		self.config['last_server'] = server
		self.application.ConfigSave()

		# Check if this server exists in the config
		if server in self.config['servers']:
			# Check the values are the same
			(oldusername, oldpassword, oldautoconnect) = self.config['details'][server]
		else:
			(oldusername, oldpassword, oldautoconnect) = (username, password, False)

		if (server not in self.config['servers'] or username != username) and not self.singleplayer:
			# Popup a dialog asking if we want to add the account
			msg = _("""\
It appears you haven't accessed this account before.

Would you like to save this account's details?
""")
			dlg = wx.MessageDialog(self, msg, _("Add Account?"), wx.YES_NO|wx.YES_DEFAULT|wx.ICON_INFORMATION)

			if dlg.ShowModal() == wx.ID_YES:
				# Add the account.
				if not server in self.ConfigPanel.Servers.GetStrings():
					self.ConfigPanel.Servers.SetStrings([server,] + self.ConfigPanel.Servers.GetStrings())
				self.config['details'][server] = [username, password, False]

				# Save the config now
				self.application.ConfigSave()

		elif password != oldpassword:
			msg = _("""\
It appears that you are using a different password for
this account, would you like to update the saved 
information with the new password?
""")

			dlg = wx.MessageDialog(self, msg, _("Update Password?"), wx.YES_NO|wx.YES_DEFAULT|wx.ICON_INFORMATION)
			if dlg.ShowModal() == wx.ID_YES:
				# Update the password
				self.config['details'][server][PASSWORD] = password
				# Save the config now
				self.application.ConfigSave()

		self.application.network.Call(self.application.network.ConnectTo, server, username, password, debug=self.config['debug'])

	def OnCancel(self, evt):
		self.OnExit(evt)

	def OnConfig(self, evt):
		self.application.ConfigDisplay()

	def OnSinglePlayer(self, evt):
		wizard = SinglePlayerWizard(self)
		if wizard.Run():
			# FIXME: This is a blocking call and will cause the UI to freeze!
			port = wizard.game.start()
			if port:
				self.singleplayer = True
				self.ShowURL("tp://player:player@localhost:" + str(port))
				self.OnOkay(None)
			else:
				msg = _("""\
Could not start single player game. Please check the console log for more information. \
""")
				dlg = wx.MessageDialog(self, msg, _("Single Player Error"), wx.OK|wx.ICON_ERROR)
				dlg.ShowModal()
		wizard.Destroy()

	def OnFind(self, evt):
		self.application.gui.Show(self.application.gui.servers)

	def ShowURL(self, url):
		# Split the URL out into username, password, etc
		# <proto>://<username>:<password>@<server>/<game>
		# server = <proto>://<server>/
		# username = <username>@<game>
		# password = <server>
		server, username, game, password = url2bits(url)

		if server is None or len(server) == 0:
			return
		self.Server.SetValue(server)

		if username is None:
			username = ""
		if not game is None:
			username = "%s@%s" % (username, game)
		self.SetUsername(username)
		if password is None:
			password = ""
		self.Password.SetValue(password)

	# Config Functions -----------------------------------------------------------------------------
	def ConfigDefault(self, config=None):
		"""\
		Fill out the config with defaults (if the options are not valid or nonexistant).
		"""
		if config is None:
			config = {}

		try:
			if not isinstance(config['servers'], list):
				raise ValueError('Config-%s: a servers value of %s is not valid' % (self, config['servers']))

			for server in config['servers']:
				if not isinstance(server, (str, unicode)):
					config['servers'].remove(server)

			if len(config['servers']) <= 0:
				raise ValueError('Config-%s: the servers list was empty' % (self,))

		except (ValueError, KeyError), e:
			config['servers'] = ["demo1.thousandparsec.net", "demo2.thousandparsec.net", "127.0.0.1"]

		#check the last selected server
		try:
			if not isinstance(config['last_server'], (str, unicode)):
				raise ValueError('Config-%s: the last server is not set' % self)
			
		except (ValueError, KeyError), e:
			config['last_server'] = ""

		try:
			if not isinstance(config['details'], dict):
				raise ValueError('Config-%s: a details value of %s is not valid' % (self, config['details']))

			for server, details in config['details'].items():
				if not isinstance(details, list) or len(details) != 3 or \
						not isinstance(details[0], (str, unicode)) or \
						not isinstance(details[1], (str, unicode)) or \
						not isinstance(details[2], bool):
					del config[server]

		except (ValueError, KeyError), e:
			config['details'] = {}
		for server in config['servers']:
			if server not in config['details']:
				config['details'][server] = ["guest@tp", "guest", False]

		try:
			if not isinstance(config['debug'], bool):
				raise ValueError('Config-%s: a debug value of %s is not valid' % (self, config['debug']))
		except (ValueError, KeyError), e:
			config['debug'] = False

		return config

	def ConfigSave(self):
		"""\
		Returns the configuration of the Window (and it's children).
		"""
		self.ConfigUpdate()

		self.ConfigLoad(self.config)
		return self.config

	def ConfigLoad(self, config):
		"""\
		Loads the configuration of the Window (and it's children).
		"""
		self.config = config
		self.ConfigDefault(config)

		#self.Server.Clear()
		self.Server.AppendItems(self.config['servers'])
		#self.Server.SetValue(self.config['servers'][0])

		self.ConfigDisplayUpdate(None)

	def ConfigUpdate(self):
		"""\
		Updates the config details using external sources.
		"""
		self.config['debug'] = self.ConfigPanel.Debug.GetValue()

		self.config['servers'] = self.ConfigPanel.Servers.GetStrings()
		for removed in self.config['details'].keys():
			if not removed in self.config['servers']:
				del self.config['details'][removed]

	def ConfigDisplay(self, panel, sizer):
		"""\
		Display a config panel with all the config options.
		"""
		self.ConfigPanel = configConnect(panel)

		self.ConfigPanel.Servers.Bind(wx.EVT_LIST_ITEM_FOCUSED,   self.OnConfigSelectServer)
		self.ConfigPanel.Servers.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnConfigSelectServer)
		self.ConfigPanel.Username.Bind(wx.EVT_KILL_FOCUS, self.OnConfigUsername)
		self.ConfigPanel.Game.Bind(wx.EVT_KILL_FOCUS, self.OnConfigUsername)
		self.ConfigPanel.Password.Bind(wx.EVT_KILL_FOCUS, self.OnConfigPassword)
		self.ConfigPanel.AutoConnect.Bind(wx.EVT_CHECKBOX, self.OnConfigAutoConnect)
		self.ConfigPanel.Debug.Bind(wx.EVT_CHECKBOX, self.OnConfigDebug)

		sizer.Add( self.ConfigPanel, 1, wx.EXPAND, 5 )

	def ConfigDisplayUpdate(self, evt):
		"""\
		Updates the config details using external sources.
		"""
		if evt != None:
			evt.Skip()

		self.ConfigPanel.Debug.SetValue(self.config['debug'])
		self.ConfigPanel.Servers.SetStrings(self.config['servers'])

	def OnConfigSelectServer(self, evt):
		server = evt.GetText()

		if len(server) > 0:
			self.ConfigPanel.EnableDetails(server)

			if not self.config['details'].has_key(server):
				self.config['details'][server] = [self.ConfigPanel.GetUsername(), self.ConfigPanel.Password.GetValue(), False]

			self.ConfigPanel.SetUsername(self.config['details'][server][0])
			self.ConfigPanel.Password.SetValue(self.config['details'][server][1])
			self.ConfigPanel.AutoConnect.SetValue(self.config['details'][server][2])
		else:
			self.ConfigPanel.DisableDetails()
		evt.Skip()

	def OnConfigUsername(self, evt):
		server = self.ConfigPanel.ServerDetails.GetLabel()[len(_("Login for ")):]
		self.config['details'][server][0] = self.ConfigPanel.GetUsername()

	def OnConfigPassword(self, evt):
		server = self.ConfigPanel.ServerDetails.GetLabel()[len(_("Login for ")):]
		self.config['details'][server][1] = self.ConfigPanel.Password.GetValue()

	def OnConfigAutoConnect(self, evt):
		server = self.ConfigPanel.ServerDetails.GetLabel()[len(_("Login for ")):]

		if evt.Checked():
			# Check that no other server is also set to autoconnect
			for key, details in self.config['details'].items():
				if not details[2]: 
					continue
				msg = _("""
The client is already set to autoconnect to %(key)s.

Would you instead like to autoconnect to %(server)s.
""") % {'key': key, 'server': server}
				dlg = wx.MessageDialog(self.ConfigPanel, msg, _("Autoconnect to?"), wx.OK|wx.CANCEL|wx.ICON_INFORMATION)
				if dlg.ShowModal() == wx.ID_OK:
					details[2] = False
					break

		self.config['details'][server][2] = evt.Checked()

	def OnConfigDebug(self, evt):
		self.config['debug'] = evt.Checked()
