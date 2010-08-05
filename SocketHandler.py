#!/usr/bin/python
import Queue, socket, select, threading, time, uuid

class SocketHandler(threading.Thread):
	_sendBuffer = {}
	_masterDict = {}

	def _addClient(self, name, data):
		(host, port, recvSize) = data
		#create and connect our socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# set keep-alive
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		# connect
		sock.connect((host, port))
		# non-blocking
		sock.setblocking(0)
		# add it to _socketDict
		self._masterDict.update({name : ('CLIENT', (sock, recvSize)) })
		return

	def _addServer(self, name, data):
		(host, port, recvSize, timeOut, backlog) = data
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server.bind( (host, port) )
		server.listen(backlog)
		self._masterDict.update({ name : ('SERVER', ( server, recvSize, timeOut, [] )) })
		return

	# data = '' if client, uuid if for server client
	def _close(self, name):
		(itemType, data) = self._masterDict[name]
		if itemType == 'SERVCLIENT':
			parent = data[2]
			self._masterDict[parent][1][3].remove(name)
		sock = data[0]
		sock.shutdown(1)
		sock.close()
		del self._masterDict[name]
		if self._sendBuffer.has_key(name):
			del self._sendBuffer[name]
		
		return

	def _rwConnections(self):
		names = self._masterDict.keys()
		for name in names:
			if not self._masterDict.has_key(name): continue
			(itemType, data) = self._masterDict[name]
			if itemType == 'SERVER':
				(server, recvSize, timeOut, connectionNames) = data
				(r2r, r2w, error) = select.select([server], [], [server], 0)
				# new connection?
				if r2r:
					# get our client's socket
					client, address = server.accept()
					cName = uuid.uuid4().hex
					self._masterDict.update({cName : ( 'SERVCLIENT',  (client, recvSize, name, time.time()) ) })
					self._masterDict[name][1][3].append(cName)
					self. _outQueue.put( ('SERV_NEW_CLIENT', (name, cName, address )) )
			elif itemType == 'SERVCLIENT':
				(sock, recvSize, parent, timeOut) = data
				toTimeOut = self._masterDict[parent][1][2]

				if timeOut <= time.time()-toTimeOut:
					self._close(name)
					continue
				(r2r, r2w, error) = select.select([sock], [sock], [sock], 0)
				if r2w:
					if self._sendBuffer.has_key(name):
						line = self._sendBuffer[name]
#						line = line.encode('utf-8')
						sock.send(line)
						del self._sendBuffer[name]
				else:
					#it died, so remove it
					self._close(name)
					self. _outQueue.put( ('SERVCLIENT_DISCON', name) )

				if r2r:
					data = sock.recv(recvSize)
					if data:
						(junk,  (client, recvSize, parent, junk) ) = self._masterDict[name]
						self._masterDict[name] = ( 'SERVCLIENT',  (client, recvSize, parent, time.time()) )
						self._outQueue.put( ('SERVCLIENT_RECV', (parent, name, data)) )

			elif itemType == 'CLIENT':
				(sock, recvSize) = data
				(r2r, r2w, error) = select.select([sock], [sock], [sock], 0)
				if r2w:
					if self._sendBuffer.has_key(name):
						line = self._sendBuffer[name]
#						line = line.encode('utf-8')
						sock.send(line)
						del self._sendBuffer[name]
				if r2r:
					data = sock.recv(recvSize)
					if data:
						self._outQueue.put( ('CLIENT_RECV', ( name, data )) )

		return

	# data = 'data' or (uuid, 'data')
	def _sendData(self, name, data):
		#send data to one of our server's clients?
		if type(data) is tuple:
			(name, data) = data
		self._sendBuffer.update({name : data})
		return

	def _stop(self):
		# close all connections
		names = self._masterDict.keys()
		for name in names:
			(itemType, data) = self._masterDict[name]
			if itemType == 'SERVER': continue # close the server last
			self._close(name)
		# just servers left now:
		names = self._masterDict.keys()
		for name in names:
			(itemType, data) = self._masterDict[name]
			socket = data[0]
			socket.close(name, '')
		self._outQueue.put('THREAD_STOPPED')
		return

	def _stopServ(self, name):

		(type, (server, recvSize, timeOut, connectionNames)) = self._masterDict[name]
		del self._masterDict[name]

		for name in connectionNames:
			self._close(name)
			server.shutdown(1) 		
			server.close() 
			self._outQueue.put( ('CLOSE', (name, '' )) )

	def run(self):
		while True:
			(command, name, data) = self._getQueue()
			if command == 'ADDCLIENT':
				self._addClient(name, data)
			elif command == 'ADDSERVER':
				self._addServer(name, data)
			elif command == 'CLOSE' or command == 'DISCON':
				self._close(name)
			elif command == 'SEND':
				if data is tuple:
					(name, data) = data
				self._sendData(name, data)
			elif command == 'STOP_SERVER':
				self._stopServ(name)
			elif command == 'STOP_THREAD':
				self._stop()
				break
			self._rwConnections()
		return

	def _getQueue(self):
		try:
			if not self._inQueue.empty():
				data = self._inQueue.get_nowait()
				return data
		except BaseException, error:
			print error
		return ('', '', '')
	
	def __init__(self, inQueue, outQueue):
		self._inQueue = inQueue
		self._outQueue = outQueue
		threading.Thread.__init__(self)

