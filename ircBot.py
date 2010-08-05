#!/usr/bin/python
import Queue, re, SocketHandler, sys, threading, time, uuid, random

class ircBot(threading.Thread):
	_pingInterval = 60
	_lastPing = time.time()
	_recvPong = True

	_onChan = False
	_joinDelay = 20
	_sentJoin = 0
	_id = uuid.uuid4().hex
	_isMute = False
	_defaultConfigs = {'alias' : {}, 'restrictedCommand' : {}, 'port' : 6667, 'botName' : 'B_Dobbs', 'nickServPass' : '', 'logFile' : './ircBotLog.txt'}
	_essentialConfigs = ['botName', 'channel', 'network', 'port']

	#queues for communicating with SocketHandler
	_getQueue = Queue.Queue()
	_sendQueue = Queue.Queue()
	
	# the dictionary that holds the bot's configuration
	config = {}
	#contains any external modules that are loaded
	_external = []

	def sendLns(self, target, lines):
		if self._isMute:
			return

		if not lines:
			return
		# if we're given a list of lines to send, put them in the proper format
		if type(lines) is list:
			print lines[0]
			for i in range(0, len(lines)):
				self._write2log(self.config['botName']+'==>'+target+': '+lines[i])
				lines[i]='PRIVMSG '+target+' :'+lines[i]+'\r\n'
			lines = ''.join(lines)
		# otherwise, assume we're given a single line: format it
		else:
			self._write2log(self.config['botName']+'==>'+target+': '+lines)
			lines = 'PRIVMSG '+target+' :'+lines+'\r\n'
		self._sendQueue.put(( 'SEND', self._id, lines ))
		return

	def sendRaw(self, lines):
		if self._isMute:
			return

		if not lines:
			return
		# if we're given a list of lines to send, put them in the proper format
		if type(lines) is list:
			for i in range(0, len(lines)-1):
				lines[i]=unicode(lines[i])+u'\r\n'
			lines = ''.join(lines)
		# otherwise, assume we're given a single line: format it
		else:
			lines = unicode(str(lines))+u'\r\n'
		self._sendQueue.put(( 'SEND', self._id, lines ))
		return


	def run(self):
		while True:
			data = ''
			try:
				if not self._getQueue.empty():
					data = self._getQueue.get_nowait()
			except:
				print 'x'
			if not data:
				self._pingServer('')
				continue
			print data
			if data == 'THREAD_STOPPED':
				break

			(junk, (name, data)) = data
			self._pingServer(data)
			if not self._onChan:
				lusers = re.findall(self.config['botName']+'\w* . '+self.config['channel']+' (\:[^\r\n]*\r\n\:)', data)
				print lusers
				if lusers:
					if re.findall(self.config['botName'], lusers[0]):
						self._onChan = True
					else:
						if self._joinDelay+self._sentJoin < time.time():
							self.sendRaw('JOIN '+self.config['channel']+'\r\n')
				else:
					self.sendRaw('NAMES '+self.config['channel']+'\r\n')
			# if it's addressed to us, read it
			if name == self._id:
				# store to chat logs
				# add later
			
				# link closed?
				if re.findall('ERROR :Closing Link', data):
					self._reconnect()
					continue
				#ping?
				ping = re.findall('PING :([^\r]+)\r\n',data)
				if ping:
					self.sendRaw('PONG :'+ping[0]+'\r\n')
					continue

				self._runCommand(data)

			#if it's not addressed to us, log it
			else:
				print "================",data,"================"

	
		return
	def _authorized(self, user, command):
		if not self.config['admins'].has_key(user):
			userLevel = 999
		else:
			userLevel = self.config['admins'][user]
		if userLevel > 1000 or self.config['restrictedCommand'].has_key(command) and userLevel > self.config['restrictedCommand'][command]:
			return False
		else:
			return True

	def _connect(self):
		self._sendQueue.put(( 'ADDCLIENT', self._id, ('irc.synirc.net', 6667, 4096) ))
		self._nick(self.config['botName'])
		time.sleep(5)
		self.sendRaw('JOIN '+self.config['channel']+'\r\n')
		return
	def _list2dict(self, inList):
		outDict = {}
		if type(inList) is list:
			for line in inList:
				keyval = line.split()
				outDict.update({keyval[0] : keyval[1]})
		else:
			data = inList.split()
			outDict = {data[0] : data[1]}
		return outDict

	def _loadConfig(self, configFile):
		self.config = {}
		#open the configFile
		configFileHandle = open(configFile)
		#read it
		configFile = configFileHandle.readlines()
		configFileHandle.close()
		#loop through the lines we just read, finding key, value pairs
		for line in configFile:
			line = re.findall('\W*([\w]+)\W+(.*)', line)
			if not line:
				continue
			(key, val) = line[0]
			# if the key already exists, we want that key to return a list of all the entries 
			if self.config.has_key(key):
				oldVal = self.config[key]
				# make it a list if it's not already one
				if not (type(oldVal) is list):
					self.config[key] = [oldVal]
				self.config[key].append(val)
			# if there's no key, make one
			else:
				self.config.update({key : val})

		#make config['admins'] a dict, with the admins' names as keys, and their access level as the entry
		# e.g. {'adminName' : 0, ...}
		if self.config.has_key('admins'):
			data=self.config['admins'].split(':')
			self.config['admins'] = {}
			for line in data:
				(key, val) = line.split(' ')
				self.config['admins'].update({key : int(val)})
		else:
			self.config['admins'] = {}

		#load our list of external modules into _external
		if self.config.has_key('modules'):
			self.config['modules']=self.config['modules'].split(':')

		#set configs to defaults if no value exists
		for conf in self._defaultConfigs:
			if not self.config.has_key(conf):
				self.config[conf] = _defaultConfigs[conf]

		#check for _essentialConfigs, raise error if one's missing
		for conf in self._essentialConfigs:
			if not self.config.has_key(conf):
				raise ConfigError('No entry in config file for '+conf)

		#change some formats
		self.config['port'] = int(self.config['port'])
		self.config['channel'] = '#'+self.config['channel']

		# turn our list of aliases into a dictionary
		if self.config.has_key('alias') and len(self.config['alias']):
			self.config['alias'] = self._list2dict(self.config['alias'])

		# turn our list of restricted commands into a dictionary
		if self.config.has_key('restrictedCommand'):
			self.config['restrictedCommand'] = self._list2dict(self.config['restrictedCommand'])
		for key in self.config['restrictedCommand']:
			self.config['restrictedCommand'][key] = int(self.config['restrictedCommand'][key])
				
		#load external module, if exists
		self._reloadModules()
		return #end load config
	def _nick(self, nick):
		self.sendRaw(['NICK '+nick+'\r\n', 'USER '+nick+' '+nick+' '+nick+' :Python IRC\r\n',])

	def _pingServer(self, data):
	
		if re.findall('PONG', data):
			self._recvPong = True
		if self._pingInterval+self._lastPing < time.time():
			if self._recvPong == False:
				#no pong from last ping, reconnect
				self._reconnect()
				self._lastPing = time.time()
				return
			else:
				self._recvPong = False
				self.sendRaw('PING : '+self.config['botName']+'\r\n')	
				self._lastPing = time.time()
		return

	def _reloadModules(self):

		if self.config.has_key('modules'):
			modules = self.config['modules']
			for mod in modules:
				print mod
				try:
					#if it's already loaded, reload it
					if sys.modules.has_key(mod):
						reload(sys.modules[mod])
					self._external.append( __import__(mod))
				except BaseException, error:
					print "Error loading module \''+mod+'\' from config file:\n", error
		return

	def _reconnect(self):
		self._onChan = False
		self._sendQueue.put(( 'CLOSE',  self._id, '' ))
		time.sleep(5)
		self._connect()
		return
	def _runCommand(self, data):
		if re.findall('KICK', data):
			self.sendRaw('JOIN '+self.config['channel']+'\r\n')
			self._onChan = False
		if re.findall('please choose a different nick.', data):
			self.sendLns( 'nickserv', 'identify '+self.config['nickServPass'])
		if re.findall('Nickname is already in use.', data):
			self._nick(self.config['botName']+str(random.randint(100,999)))
			print '!!!'
			self.sendLns('nickserv', 'GHOST '+self.config['botName']+' '+self.config['nickServPass'])
		if re.findall('Ghost with your nick has been killed', data):
			self._nick(self.config['botName'])
		utca = re.findall('\:([^\!]+)[^ ]+ PRIVMSG ([^ ]+) \:[\t ]*\!([^\r\n\t ]+)[\t ]*([^\r\n]*)', data)
		if not utca:
			print "============idle=========="
			for mod in self._external:
				if hasattr(mod, 'idle'):
					mod.idle(self, data)
					break
			return
		print utca


		(user, target, command, argument ) = utca[0]
		if command:
			self._write2log(user+'==>'+target+': !'+command+' \''+argument+'\'')

		if user in self.config['ignore']:
			print '---Ignored---'
			return

		if target == self.config['botName']:
			target = user
		if self.config['alias'].has_key(command):
			command = self.config['alias'][command]

		if not self._authorized(user, command):
			self.sendLns(user, 'Permission Denied.')
			return

		if command == 'die':
			self._sendQueue.put(( 'STOP_THREAD', '', ''))
			return
		elif command == 'reload':
			self._loadConfig(self._configFile)
			self._reloadModules()
			return
		elif command == 'mute':
			self._isMute = False if self._isMute else True
			return
				


		for mod in self._external:
			if hasattr(mod, command):

				getattr(mod, command)(self, user, target, argument)
				break
	def _write2log(self, data):
		logTime = time.strftime('%d %B %Y %H:%M:%S')
		ircLog=open(self.config['logFile'], 'a')
		line = logTime+'\t'+data+'\n'
		ircLog.write(line.encode('utf-8'))


	def __init__(self, configFile):
		self._configFile = configFile
		#start our socket thread
		SocketHandler.SocketHandler(self._sendQueue, self._getQueue).start()
		self._loadConfig(configFile)
		self._connect()
		threading.Thread.__init__(self)
		return

bot = ircBot('ircbot.cfg').start()
