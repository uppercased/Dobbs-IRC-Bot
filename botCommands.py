import codecs, commands, random, re, urllib, urllib2 
from xml.dom import minidom
_commandLevels = {'nick' : 1, 'raw' : 1, 'restart' : 1, 'shutdown' : 0}


helpDict = {
'8ball' : 'usage: "!8ball". <BOTNAME> checks the magic 8ball.', 
'about' : 'usage: "!about". <BOTNAME> returns information about itself.', 
'action' : 'usage: "!action [action]". <BOTNAME> will do [action] (Only allowed users can do this).', 
'dance' : 'usage: "!dance". Makes <BOTNAME> dance.', 
'd' : 'usage: !d [number]. Dobbs rolls a die with [number] sides.',
'die' : 'usage: "!die". The big red button: kills the bot.', 
'echo' : 'usage: "!echo [message]". <BOTNAME> will say [message] (Only allowed users can do this).', 
'fortune' : 'usage: "!fortune". <BOTNAME> tells you your fortune.', 
'goog' : 'usage: "!goog [search string]". <BOTNAME> will search google for [search string].', 
'help' : 'usage: "!help", also "!h" and "!man". Returns this menu.', 
'highfive' : 'usage: "!highfive". <BOTNAME> high-fives you',
'hipster' : 'usage: "!hipster". <BOTNAME> returns some shitty indie music Jake likes.',
'kick' : 'usage: "!kick [nick]". If <BOTNAME> has ops, it will kick [nick] from the channel.', 
'kill' : 'usage: "!kill". <BOTNAME> will "die"', 
'kjv' : 'usage: "!kjv [verse]". <BOTNAME> recite the given verse from the king james version of the bible. Must be in the form of gen 1:1-5, 1kings3:3, Judges 12:11 etc.', 
'mo' : 'usage: "!mo". <BOTNAME> displays a random ascii art of the prophet muhammad.', 
'nick' : 'usage: "!nick [new nick]". <BOTNAME> will change its name to [new nick] (Only admins may do this).', 
'raw' : 'usage: "!raw [raw data]". <BOTNAME> will send [raw data] directly to the irc server (Only admins may do this).', 
'reload' : 'usage: "!reload". Reloads the external modules and help file (Only the bot owner my do this).', 
'stab' : 'usage: "!stab [x]". <BOTNAME> will stab [x].', 
'tardwiki' : 'usage "!tardwiki [article name]". <BOTNAME> will post the link to the [article name] entry on conservapedia.', 
'vuvuzela' : 'usage "!vuvuzela". <BOTNAME> makes beautiful music.', 
'wastrel' : 'usage "!wastrel [flag (optional)] [x]". <BOTNAME> will say a wastrelism. Flags (default is -d): -a=\'All [x] is bad.\', -d=\'Death to [x]!\', -p=\'Sometimes people [x] for certain reasons.\', -s=\'[x] makes me the saddest girl in the world.\'', 
'weather' : 'usage "!weather [flag (optional)] [u=c|d|f (optional)] [place]". <BOTNAME> will tell you the weather for [place]. Flags are \'-a\' for all weather info, \'-f\' for today and tomarrow\'s forecast, and \'-s\' or no flag for today\'s current conditions/projected high and low temps. [u=c] will return weather in degrees C -- f = fahrenheit and d = defaulf for the region. ', 
'wiki' : 'usage "!wiki [article name]". <BOTNAME> will post the link to the [article name] entry on wikipedia.'
}

_eightballResponses = ['As I see it, yes', 'It is certain', 'It is decidedly so', 'Most likely', 'Outlook good', 'Signs point to yes', 'Without a doubt', 'Yes', 'Yes - definitely', 'You may rely on it', 'Reply hazy, try again', 'Ask again later', 'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again',  'Don\'t count on it', 'My reply is no', 'My sources say no', 'Outlook not so good', 'Very doubtful']
_wastrel={'a' : 'All x is bad.', 'd' : 'Death to x!', 'p' : 'Sometimes people x for certain reasons.', 's' : 'x makes me the saddest girl in the world.'}

f=codecs.open('mo', encoding='utf-8')
mohammeds=f.readlines()

f=open('peopleIknow')
peopleIknow=f.readlines()
if not peopleIknow:
	peopleIknow = []
peopleIknow = [i.rstrip() for i in peopleIknow]
f.close()

def _getTitleAndUrl(url):
	try:
		request = urllib2.Request(url)
		#spoof our user agent
		request.add_header('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.3) Gecko/20100423 Linux Mint/9 (Isadora) Firefox/3.6.3')
		response = urllib2.urlopen(request)
		realUrl = response.geturl()
		data = response.read()
		title = re.findall('<title[^>]*>(.*)</title>',data)
		if len(title):
			title=title[0]
		else:
			title=''
		return (title, realUrl)
	except:
		return ('', url)

def _getWeather(place, u, appId): # dict[weather], [dict[forecast]], "errors"
	place = re.sub('\W', ' ', place)
	url = 'http://where.yahooapis.com/v1/places.q('+place+')?appid='+appId
	print place
	try:
		response = urllib.urlopen(url)
		dom = minidom.parse(response)
		node = dom.getElementsByTagName('woeid')[0]
		woeid = node.firstChild.nodeValue
		node = dom.getElementsByTagName('country')[0]
		country = node.getAttribute('code')
		if u=='d':
			if country=='US':
				u='f'
			else:
				u='c'
	except:
		return 0, 0, 'Error connecting to server.'

	if len(woeid):
		try:
			response = urllib.urlopen('http://weather.yahooapis.com/forecastrss?w='+woeid+'&u='+u)
			dom = minidom.parse(response)

			#location
			node = dom.getElementsByTagName('yweather:location')[0]
			weather = {'city' : node.getAttribute('city') , 'region' : node.getAttribute('region'), 'country' : node.getAttribute('country')}
			#units
			node = dom.getElementsByTagName('yweather:units')[0]
			units = {'temp' : u'\xb0'+node.getAttribute('temperature') , 'dist' : node.getAttribute('distance'), 'pres' : node.getAttribute('pressure'), 'speed' : node.getAttribute('speed')}
			#wind
			node = dom.getElementsByTagName('yweather:wind')[0]
			weather.update({'wChill' : node.getAttribute('chill')+units['temp'] , 'wDir' : node.getAttribute('direction'), 'wSpeed' : node.getAttribute('speed')+units['speed']})
			#atmosphere
			node = dom.getElementsByTagName('yweather:atmosphere')[0]
			weather.update({'humid' : node.getAttribute('humidity')+u'%' , 'vis' : node.getAttribute('visibility')+units['dist'], 'pres' : node.getAttribute('pressure')+units['pres'], 'rising' : node.getAttribute('rising')})

			#convert heading to compass point
			compassPoints = ('N', 'NbE', 'NNE', 'NEbN', 'NE', 'NEbE', 'ENE', 'EbN', 'E', 'EbS', 'ESE', 'SEbE', 'SE', 'SEbS', 'SSE', 'SbE', 'S', 'SbW', 'SSW', 'SWbS', 'SW', 'SWbW', 'WSW', 'WbS', 'W', 'WbN', 'WNW', 'NWbW', 'NW', 'NWbN', 'NNW', 'NbW', 'N')
			
			weather['wDir'] = weather['wDir']+u'\u00B0'+compassPoints[int(float(weather['wDir'])/11.25+.5)]
			#astronomy
			node = dom.getElementsByTagName('yweather:astronomy')[0]
			weather.update({'sunUp' : node.getAttribute('sunrise') , 'sunDown' : node.getAttribute('sunset')})
			#conditions
			node = dom.getElementsByTagName('yweather:condition')[0]
			weather.update({'conditions' : node.getAttribute('text') , 'temp' : node.getAttribute('temp')+units['temp'], 'date' : node.getAttribute('date')})

			forecasts = []
			for node in dom.getElementsByTagName('yweather:forecast'):
				forecasts.append({
				'date': node.getAttribute('date'),
				'low': node.getAttribute('low')+units['temp'],
				'high': node.getAttribute('high')+units['temp'],
				'conditions': node.getAttribute('text')
			})
			return weather, forecasts, ''
		except:
			return 0, 0, 'error'
	else:
		return 0, 0, 'Bad location.'



def idle(bot, data):
	user = re.findall('\A\:([^\!]+)[^ ]+ JOIN \:#', data)
	if user and not (user[0] in bot.config['ignore']):
		if random.randint(0,9) == 0 or not user[0] in peopleIknow:
			stab(bot, '', '', user[0])
			peopleIknow.append(user[0])
			f = open('peopleIknow', 'a')
			f.write(user[0]+'\r\n')
			f.close()
		elif random.randint(0,49) == 0:
			argument = ['gives x a hug.', 'gives x some flowers.', 'tells x that they\'re a swell friend.', '<3s x.', 'does the dishes for x.', 'bakes a cake for x.'][random.randint(0,5)].replace('x',user[0])
			action(bot, user[0], '', argument)
	return

#==========================================================
# Begin command functions
#==========================================================
#def (bot, user, target, argument):
#	return

def eightBall(bot, user, target, argument):
	bot.sendLns(target, _eightballResponses[random.randint(0,19)])
	return

def about(bot, user, target, argument):
	lines = bot.config['about'].split('\\n')
	bot.sendLns(user, lines)
	return

def action(bot, user, target, argument):
	bot.sendLns(bot.config['channel'], 'ACTION '+argument+'')
	return

def d(bot, user, target, argument):
	try:
		size=int(argument)
		if size < 2 or size > 1000000000: raise
	except:
		bot.sendLns(user, 'invalid number, must be a value between 2-1000000000.')
		return
	try:
		number = urllib.urlopen('http://www.random.org/integers/?num=1&min=1&max='+str(size)+'&col=5&base=10&format=plain&rnd=new').read()
		number=re.findall('(\d+)', number)[0]
		print 'from site'
	except:
		number = str(random.randint(1,size))
	if target == user:
		bot.sendLns(target, '*rolls the dice* -- '+number)
	else:
		action(bot, '', '', 'rolls the dice: '+number)

	return

def dance(bot, user, target, argument):
	action(bot, '', '', 'dances :D--<')
	action(bot, '', '', 'dances :D|-<')
	action(bot, '', '', 'dances :D/-<')
	return

def echo(bot, user, target, argument):
	bot.sendLns(bot.config['channel'], argument)
	return

def fortune(bot, user, target, argument):
	fortune = commands.getoutput('fortune -as')
	fortune = re.split('\n', fortune)
	bot.sendLns(target, fortune)
	return

def google(bot, user, target, argument):
	data=re.sub('[\ ]+', '+', argument)
	bot.sendLns(target, 'http://www.google.com/#&q='+data+' ==> Google Search for \''+argument+'\'')
	return

def help(bot, user, target, argument):
	argument=argument.replace('!','')
	if argument in helpDict:
		response = helpDict[argument].replace('<BOTNAME>', bot.config['botName'])
	else:
		if argument:
			response = "Command '"+argument+"' not found in help file."
		else:
		 	response = "usage: !help [command]."
		if bot.config.has_key('owner'):
			response = response +' Problems/questions: talk to '+bot.config['owner']

		keys = helpDict.keys()
		keys.sort()
		response = [response, 'List of commands: !'+' !'.join(keys)]
	bot.sendLns(user, response)
	return
	
def highfive(bot, user, target, argument):
	bot.sendLns(target, 'ACTION high fives '+user+'.')
	return

def hipster(bot, user, target, argument):
	hipfile = urllib2.urlopen('http://terras.rotahall.org/hipster.txt')
	artistlist = hipfile.readlines()
	artist = artistlist[random.randint(0,len(artistlist)-1)].strip('\n')
	bot.sendLns(target, artist)
	return

def kick(bot, user, target, argument):
	bot.sendRaw('KICK '+bot.config['channel']+' '+argument+'\r\n')
	return

def kill(bot, user, target, argument):
	action(bot, '', '', 'dies.')
	return

def kjv(bot, user, target, argument):
	if not argument:
		
		return
	#make sure that the input is of the correct format and sanitized.
	verseNum = re.findall('\W*(^\d*[A-Za-z]+[\ ]*\d+\:\d+[\-]{0,1}\d*$)\W*', argument)
	#if it is ...
	if verseNum != []:
		# strip spaces
		verseNum=verseNum[0].replace(' ','') 
		#feed input to the "bible" program, and capture the output
		verse = commands.getoutput('bible -f '+verseNum)
		#store returned verses in a list (by line)
		verse = re.split('\n', verse)
		numLines = 0
		# print the lines, with a maximum of 6
		for line in verse:
			numLines+=1
			bot.sendLns(target, line)
			if numLines == 6: break
	else:
		#alert user to bad input
		bot.sendLns(target, '!kjv: Bad format.')
	return

def mo(bot, user, target, argument):
	bot.sendLns(target, mohammeds[random.randint(0,len(mohammeds)-1)])
	return

def nick(bot, user, target, argument):
	bot.sendRaw('NICK '+argument+'\r\n')
	bot.config['botName'] = argument
	return

def raw(bot, user, target, argument):
	bot.sendRaw(argument+'\r\n')
	return

def stab(bot, user, target, argument):
	action(bot, '', '', 'stabs '+argument)
	return

def tardwiki(bot, user, target, argument):
	url = 'http://www.conservapedia.com/Special:Search?search='+'+'.join(re.split('[ ]+', argument))+'&go=Go'
	(title, realUrl) = _getTitleAndUrl(url)
	bot.sendLns(target, realUrl+' ==> '+title)
	return

	
def vuvuzela(bot, user, target, argument):
	bot.sendLns(target, 'BZZZZZZZZZZZZZZZZZ BZZZZZ BZZZZZ BZZZZZ BZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZz')

def wastrel(bot, user, target, argument):
	args = re.findall('-([a-zA])\W+(.*)', argument)
	if len(args):
		(flag, thing) = args[0]
	else:
		(flag, thing) = ('d', argument)
	if not _wastrel.has_key(flag):
		flag = 'd'
	bot.sendLns(target, _wastrel[flag].replace('x', thing))

def weather(bot, user, target, argument):
	if not bot.config.has_key('yahooAppId'):
		bot.sendLns(target, 'No Yahoo appId in configuration file.')
		return
	#find flags (-d, -l, etc)
	try:
		(flag, units, place) = re.findall('(?:-([a-z])){0,1}\W*(?:u=([cf])){0,1}\W*(.+)', argument)[0]
		flag = flag if flag else 's'
		units = units if units else 'd'
	except:
		(flag, units, place) = ('s', 'd', argument)
	(weather, forecasts, error) = _getWeather(place, units, bot.config['yahooAppId'])

	if error: # error?
		#send error text
		bot.sendLns(target, error) 
	else: # send weather to target
		if flag == 'a':
			lines = [u'Conditions for '+weather['city']+u' '+weather['region']+u', '+weather['country']+u' on '+weather['date']+u': '+weather['conditions']+u'.  Visibility: '+weather['vis']+u'  Temp: '+weather['temp']+u'  wChill: '+weather['wChill'], u'Wind: '+weather['wDir']+u'  wSpeed: '+weather['wSpeed']+u'  Humidity: '+weather['humid']+u'  Atm. Pressure: '+weather['pres']+u'  SunUp: '+weather['sunUp']+u'  SunDown: '+weather['sunDown']]
			forecastStr=u'Forecast: '
			for day in forecasts:
				forecastStr = forecastStr+u'<'+day['date']+u' -- '+day['conditions']+u'  High: '+day['high']+u'  Low: '+day['low']+u'>    '
			lines.append(forecastStr)
		elif flag == 'f':
			forecastStr=u'Forecast for '+weather['city']+u' '+weather['region']+u': '
			for day in forecasts:
				forecastStr = forecastStr+u'<'+day['date']+u' -- '+day['conditions']+u'  High: '+day['high']+u'  Low: '+day['low']+u'>    '
			lines = [forecastStr]
		elif flag == 's': # -s and others
			lines = [u'Conditions for '+weather['city']+u' '+weather['region']+u' on '+weather['date']+u': '+weather['conditions']+u'  Temp: '+weather['temp']+u'  High: '+forecasts[0]['high']+u'  Low: '+forecasts[0]['low']]
		else:
			bot.sendLns(user, "type !help weather for usage")
			return

		bot.sendLns(target, lines)

def wiki(bot, user, target, argument):
	url = 'http://en.wikipedia.org/w/index.php?title=Special%3ASearch&search='+'+'.join(re.split('[ ]+', argument))+'&go=Go'
	(title, realUrl) = _getTitleAndUrl(url)
	bot.sendLns(target, realUrl+' ==> '+title+'')
	return

