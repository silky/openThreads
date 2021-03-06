import re
import time
import json
import couchdb
import sys

def logMe(logItem):
    """This function prints out logging when the program is called form the command line."""
    #if __name__ == '__main__':
    print(logItem)

logMe("Welcome to Open Threads... Please run openthreads.openThread(FILE_NAME) to open a text file of a list serv")

class openThread:
    def __init__(self, fileLoc, threadName=None, parse=None):
        """Creating a new openThread requires that you pass it the location of the thread that you wish to parse."""
        if fileLoc:
            if threadName != None:
                self.threadName = threadName
            else:
                self.threadName = "listServ"
            logMe("Parsing list-serv... This may take a moment")
            self.raw = self.getArchive(fileLoc)
            self.messages = self.getMessages(self.raw)
            logMe("List Serv Parsed. Identifying Unique users...")
            self.First = self.firstPost(self.messages)
            logMe("Users Identified! Thank you for waiting.")
            self.threads = self.threader(self.messages)
            if parse != 'false':
                logMe("Starting To Parse List Serv")
                self.profiles = self.runProf()
                self.msgProf = self.runMsgs()
                self.threadProf = self.runThreads()
        else:
            logMe("Please specify a list serv you would like to parse.")

    def getArchive(self, textFile):
        """This function takes the location of the list-serv text file and opens it up for parsing
        """
        text = open(textFile)
        rawText = text.read()
        return rawText

    def getMessages(self, raw):
        messages = []
        splitText = self.split(raw)
        for i in splitText:
            msgDict = self.dictify(i)
            messages.append(msgDict)
        return messages
    
    def split(self, raw):
        """This function takes the location of the list-serv text file and opens it up for parsing. Much later I may add the ability to just choose the html address of a list-serv archive. That will be straight up neato!
        """
        if raw == '':
            logMe("Please get a list serv archive and import it file first.")
        else:
            who = '\S*\sat\s\S*'
            headerFront = '\nFrom\s' + who + '\s*'
            capturedFront = '\nFrom\s(' + who + ')\s*'
            day = '[A-Z][a-z]{2}'
            month = day
            date = day + '\s' + month + '\s*?\d*?\s\S*?\s\d{4}\n'
            capTop = capturedFront + '(' + date + ')'
            dropTop = headerFront + date
#TODO - rewrite the following line to become a dictionary that parses the monthly log and create indiviudal dictionaries of all pertinant header info for each e-mail and includes the content.
            getHeader = '(.*?Message\-ID\:\s(.*?)\n)'
            fullHead = dropTop + getHeader
            splitText = re.split(dropTop, raw)
            return splitText
        
    def dictify(self, email):
        """This function takes a raw text version of a list-serv archive and converts it into a parsable dictionary... possibly in JSON format. Yea, we will do JSON formatting because the internets love them some JSON
        """
        #get headers from email
        getHeader = '(.*?Message\-ID\:\s.*?\n)'
        msgDict = {}
        msg = re.findall(getHeader + '(.*)', email, flags=re.DOTALL)
        #create a dictionary item for body text
        for i in msg:
            msgDict['Body'] = i[1]
        # Setting header specific regEx's
        whom = 'From\:\s(.*?)\n'
        date = 'Date\:\s*?(.*?)\n'
        dWrd = '[A-Z][a-z]{2}'
        subject = 'Subject\:\s(.*?)\n'
        inReply = 'In\-Reply\-To\:\s*?(<.*?)\n'
        references = 'References\:\s*?(<.*?)\nMessage\-ID\:'
        messageID = 'Message\-ID\:\s*?(<.*?)\n'
        name = '\((.*)\)'
        
       #create a dictionary item for the header items that are always there.
        whoCheck = re.findall(whom, email, flags=re.DOTALL)
        if whoCheck:
            msgDict['From'] = self.checkReg(whoCheck)
            msgDict['Name'] = re.findall(name, self.checkReg(whoCheck))[0]

        dateCheck = re.findall(date, email, flags=re.DOTALL)
        if dateCheck:
            msgDict['Date'] = self.checkReg(dateCheck)
            msgDict['compactDate'] = self.compactDate(dateCheck)
        subCheck = re.findall(subject, email, flags=re.DOTALL)
        
        if subCheck:
            msgDict['Subject'] = self.checkReg(subCheck)
        IDCheck = re.findall(messageID, email, flags=re.DOTALL)
        if IDCheck:
            msgDict['ID'] = self.checkReg(IDCheck)
        #create checks for items that may not be there.
        if re.search(references, email, flags=re.DOTALL) != 'none':
            msgDict['References'] = re.findall(references, email, flags=re.DOTALL)
        if re.search(inReply, email, flags=re.DOTALL) != 'none':
            msgDict['Reply'] = re.findall(inReply, email, flags=re.DOTALL)
       # print(msgDict['References'])
        if msgDict['References'] != []:
            msgDict['References'] = re.split('\s*|\n\t', msgDict['References'][0])
        msgDict['ScrapedBody'] = self.scrapeBody(msgDict['Body'])

        #TODO implement the below Body Parsing and more once we have text parsing in the roadmap
        scrubbed = '\-{14}\s[a-z]{4}\s[a-z]{4}\s\-{14}'
        grabScrubbed = scrubbed + '(.*)'
        replyName = 'On\s(.*?)wrote\:'

        return msgDict

    def scrapeBody(self, body):        
        scraped = ''
        msg = re.findall("^(?!>).*", body, flags=re.MULTILINE)
        for i in msg:
            if i != ' ':
                scraped = scraped + ' ' + i
        return scraped

    def getPGP(self, body):
        beginPGP = '\-{5}[A-Z]{5} [A-Z]{3} [A-Z]{9}\-{5}\n'
        endPGP = '\-{5}[A-Z]{3} [A-Z]{3} [A-Z]{9}\-{5}\n'
        PGP = beginPGP + '(.*?)' + endPGP
        PGP = re.findall(PGP, body, flags=re.DOTALL)
        return PGP
    
    def checkReg(self, item):
        """ This function takes all sections that I don't want in a listand returns the first string.
        TODO: make sure that the header sections that are being run through here are not losing data through this process.
        """
        if type(item) == list:
            return(item[0])
        else:
            return(item)
        
    def compactDate(self, dateCheck):
        """
        TestingMethod = checkCompDate"""
        second, minute, hour, day, month, year = 0,0,0,0,0,0
        dWrd = '[A-Z][a-z]{2}'
        compDateDict = ''+dWrd+',\s*?(\d*?)\s('+dWrd+')\s(\d{4})\s(\d{2})\:(\d{2})\:(\d{2})'
        compDateDictNoDay = '\s*?(\d*?)\s('+dWrd+')\s(\d{4})\s(\d{2})\:(\d{2})\:(\d{2})'
        compDateDictNoSec = '\s*?(\d*?)\s('+dWrd+')\s(\d{4})\s(\d{2})\:(\d{2})'
        compDateDictShortNum = ''+dWrd+',\s*?(\d*?)\s('+dWrd+')\s(\d{4})\s(\d*?)\:(\d*?)\:(\d{2})'
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        compactTup = re.findall(compDateDict, self.checkReg(dateCheck))
        if compactTup == []:
            compactTup = re.findall(compDateDictNoDay, self.checkReg(dateCheck))
            if compactTup == []:
                compactTup = re.findall(compDateDictNoSec, self.checkReg(dateCheck))
                if compactTup != []:
                    compactTup[0] = compactTup[0] + ('00',)
                else:
                    compactTup = re.findall(compDateDictShortNum, self.checkReg(dateCheck))
                    if compactTup == []:
                        print('Unsupported Date Format: Please send the output of this command and the printed date to openThreads to add support')
                        print(dateCheck)
                
        for i in [i for i,x in enumerate(months) if x == compactTup[0][1]]:
            month = i + 1
        if len(str(month)) == 1:
            month = str(0) + str(month)
        day = compactTup[0][0]
        if len(day) == 1:
            day = str(0) + day
        year = compactTup[0][2]
        second = compactTup[0][5]
        minute = compactTup[0][4]
        hour = compactTup[0][3]
        compactDate = str(year) + str(month) + str(day) + str(hour) + str(minute) + str(second)
        return(compactDate)
            
    def couchDB(self, server=None, port=None, database=None, data=None):
        """This connects to an existing couchDB server and exports data to it. This function does not provide any other couchDB functionality. You have to do that all on your end. :) """
        #checking for if external server or if server is on localhost as well as for the port of the server is unique
        if server:
            if port:
                couch = couchdb.Server('http://'+server+':'+port)
            else:
                couch = couchdb.Server('http://'+server+':5984/')
        else:
            couch = couchdb.Server()
        # select database or set to default listServ database
        if database:
            db = couch[database]
        else:
            db = couch["listserv"]
        
        #This will check if you pass it a specifc data set and send either that, or the full messages dict to the database
        if data:
            db.save(data)
        else:
            db.save(self.messages)
        
    def jsonMaker(self, command, fileName, data=None):
        if command == 'open':
            f = open(fileName+'.json', 'r');
            tmpMsg = f.read()
            return json.loads(tmpMsg)
        elif command == 'save' and data != None:
            f = open(fileName + '.json', 'w');
            f.write(json.dumps(data));
            f.close()
        elif command == 'save':
            f = open(fileName + '.json', 'w');
            f.write(json.dumps(self.messages));
            f.close()
        
    def firstPost(self, messages):
        parsedFirst = {}
        exist = 0
        for i in messages:
            for x in parsedFirst:
                name = str(i['Name'])
                if i['Name'] == parsedFirst[x]['Name']:
                    exist = 1
                    if i['compactDate'] < parsedFirst[x]['compactDate']:
                        del(parsedFirst[x])
                        name = str(i['Name'])
                        parsedFirst[name] = i
            if exist != 1:
                name = str(i['Name'])
                parsedFirst[name] = i
            exist = 0
        return parsedFirst

    def threader(self, messages):
        """This function takes a set of messages and returns a dictionary of threadID's that hold the ID's of the messages within them. It is not very efficiant sorting. But, for now I just need to get the data. I will refactor later."""
        threads = {}
        for i in messages:
            if i['References'] == []:
                threads[i['ID']] = []
        for i in messages:
            if i['References'] != []:
                for n in i['References']:
                    if n in threads:
                        threads[n].append(i['ID'])
        return threads
    
    
    def Response(self, ID):
        '''A function that takes a message ID and looks at what kind of response people receive on their post. This collects the ammount of replies to an individuals first post on a listserv and returns the message id of all responses as well as the ammount of messages a individual user posts to a listserv after their first thread. '''

    #Grabs the identified message from the main message structure
        message = ''
        for i in self.messages:
            if i['ID'] == ID:                message = i
        if message == '':
            return 'no message found, are you sure that code is correct?'
    
    #Gather replies and append them to the message structure
        message['repNum'], message['replies'] = self.replies(message['ID'])
        
    #gather the ammount of total messages a user has sent
        message['totalCount'], totalMsgId = self.totalMessages(message['Name'])

        logMe(message['Name'], "total messages by user:" + str(message['totalCount']), "number of replies to this message:" + str(message['repNum']))

    def totalMessages(self, name):
        '''This function takes a users name and returns the ID's of all their messages on a mailing list and the total number.'''
        userTotal = 0
        userMsgs = []
        for i in self.messages:
            if i['Name'] == name:
                userTotal += 1
                userMsgs.append(i['ID'])
        return userMsgs, userTotal

    def reference(self, ID):
        '''This function takes a message ID and returns a list of all the messages that are on the thread of the identified message.''' 
        refTotal = 0
        references = []
        for i in self.messages: 
            if ID in i['References']:
                refTotal += 1
                references.append(i)
        return refTotal, references

    def replies(self, ID):
        '''This function takes a message ID and returns a list of all the messages that replied to the identified message.''' 
        replies = []
        repTotal = 0
        for i in self.messages:
            if ID in i['Reply']:
                repTotal += 1
                replies.append(i)
        return repTotal, replies

    def totalReplies(self, name):
        """returns the total number of direct replies a user receives"""
        repNames = []
        repID = []
        repTotal = 0
        for i in self.messages:
            if i['Name'] == name:
                if i['ID'] != []:
                    repNum, repRep = self.replies(i['ID'])
                    repTotal += repNum
                    for x in repRep:
                        repID.append(x['ID'])
                        repNames.append(x['Name'])
        return repTotal, repID, repNames 

    def postsPer(self):
        first = self.First
        postNum = []
        for h,k in first.iteritems():
            ID, total = self.totalMessages(k['Name'])
            postNum.append((k['Name'], total))
        return postNum

    def users(self):
        first = self.First
        userList = []
        for h,k in first.iteritems():
            ID, total = self.totalMessages(k['Name'])
            userList.append(k['Name'])
        return userList
    
    def topPosters(self):
        """Returns the top 25 posters"""
        postnum = self.postsPer()
        sortedPost = sorted(postnum, key=self.sortTop)
        check = 1
        top = []
        while check <= 100:
            if sortedPost[-check]:
                top.append(sortedPost[-check])
            check += 1
        return top

    def sortTop(self, a):
        """Used in top function for sorting the tuples"""
        return a[1]

    def missedConnections(self):
        postNum = self.postsPer()
        missed = []
        for i in postNum:
            if i[1] == 1:
                missed.append(i[0])
        return missed
        
    def newMessages(self, name=None):
        """returns the ID of messages that do not reference other messages"""
        newMessages = []
        numMsgs = 0
        for i in self.messages:
            if i['References'] == []:
                if name is None:
                    newMessages.append(i['ID'])
                    numMsgs += 1
                else:
                    if i['Name'] == name:
                        newMessages.append(i['ID'])
                        numMsgs += 1
        return newMessages, numMsgs

    def noResponse(self):
        """return the ID of all posts that are never responded to"""
        newMsg = self.newMessages()
        for i in self.messages:
            #NOTE: many items are lists in self.messages and must be pulled out of the list to play with/remove them.
            if i['Reply'] != [] and i['Reply'][0] in newMsg:
                newMsg.remove(i['Reply'][0])
        return newMsg
    
    def allReplys(self, name=None):
        """returns the ID of all replies by a user (these may also reference other messages, be warned about that"""
        repMessages = []
        repNum = 0
        for i in self.messages:
            if i['Reply'] != []:
                if name is None:
                    repMessages.append(i['ID'])
                    repnum += 1
                else:
                    if i['Name'] == name:
                        repMessages.append(i['ID'])
                        repNum += 1
        return repMessages, repNum

    def allrefs(self, name=None, source=None):
         '''returns the ID of messages that reference another message or belong to a user... has redundant functionality to refrences()'''
         refMessages = []
         for i in self.messages:
             if source is None:
                 if i['References'] != []:
                     if name is None:
                         refMessages.append(i['ID'])
                     else:
                         if i['Name'] == name:
                             refMessages.append(i['ID'])
             elif source in i['References']:
                 if name is None:
                     refMessages.append(i['ID'])
                 elif i['Name'] == name:
                     refMessages.append(i['ID'])
         return refMessages

    def checkIt(self):
        """ a checker function that I wrote to explore other functions"""
        #change the following variable to check a list
        no = self.noResponse()
        for i in self.messages:
            if i['ID'] in no:
                logMe(i['Name'], i['Subject'])

    def threads(self, name=None):
        '''returns the subject name of every unique thread and total number.'''
        threads = []
        threadNum = 1
        messages, null = self.newMessages()
        if name is None:
            for i in messages:
                threads.append(i)
                threadNum += 1
        else:
            for i in self.messages:
                if i['Name'] == name:
                    for x in messages:
                        for a in i['References']:
                            if a == x:
                                threads.append(x)
                                threadNum += 1
                                messages.remove(x)
        return threads, threadNum

    def gender(self, name=None):
        """This function imports a dictionary of genders from parsables/gender.py and checks the name against them. It is not the best way, but I need to find a completely open list of names to check against """
        #TODO find a completely open dictionary of international names and genders to parse against and import it upon start
        sys.path.append( "parsables")
        import gender
        if name is None:
            for i in self.First:
                curName = re.findall("(.*)\s", str.upper(self.First[i]['Name']))
                if curName == []:
                    curName = str.upper(self.First[i]['Name'])
                elif type(curName) == list:
                    curName = curName[0]
                if curName in gender.gender:
                    self.First[i]['Gender'] = gender.gender[curName]
                else:
                    self.First[i]['Gender'] = "unknown"
        else:
            curName = re.findall("(.*)\s", str.upper(name))
            if curName == []:
                curName = str.upper(name)
            elif type(curName) == list:
                curName = curName[0]
            if curName in gender.gender:
                return gender.gender[curName]
            else:
                return "unknown"
                
    def wpmCalc(self, msg, wpm=35):
        #Scrub PGP
        beginPGP = '\-{5}[A-Z]{5} [A-Z]{3} [A-Z]{9}\-{5}\n'
        endPGP = '\-{5}[A-Z]{3} [A-Z]{3} [A-Z]{9}\-{5}\n'
        PGP = beginPGP + '(.*?)' + endPGP
        scrubbed = '\-{14}\s[a-z]{4}\s[a-z]{4}\s\-{14}'
        grabScrubbed = scrubbed + '(.*)'
        replyName = 'On\s(.*?)wrote\:'
        test = re.findall(PGP, msg, flags=re.DOTALL)


                
    def bios(self, name):
        """A function that builds user histories for a listserv"""
        #get message ID's they have used.

        userMsgs, total = self.totalMessages(name)
        
        #get total user initiated posts by a user

        userInitiated = self.newMessages(name)
        
        #get total user responses by a user

        replyID, replyNum = self.allReplys(name)
            
        #Get total independent threads a user was active in

        threadNames, threadNum = self.threads(name)
        
        #get number of direct responses to user's comments

        directReplies, repID, repNames = self.totalReplies(name)

        #get most replied to (more than one) other user

        repRep = {}
        for i in repNames:
            if repRep.has_key(i):
                repRep[i] += 1
            else:
                repRep[i] = 1
        winners = []
        curBest = 0
        for x in repRep.iteritems():
            if x[1] > curBest:
                curBest = x[1]
                winners = []
                winners.append(x[0])
            elif x[1] == curBest:
                winners.append(x[0])
        winners.append(curBest)
        mostReplied = winners

        #get list of users who targeted user replied to on the listServ

        repliedTo = []
        for n in self.messages:
            for j in userMsgs:
                if j in n['Reply']:
                    repliedTo.append(n['Name'])

        #get users first post to the list
        for i in self.First.itervalues():
            if i['Name'] == name:
                firstPost = i


        return {'name':name, 'mostRepliedTo':repliedTo, 'mostReplied':mostReplied, 'directResponses':directReplies, 'activeThreads':threadNum, 'replies':replyNum, 'userLedThreads':initNum}
                
    def runBios(self):
        users  = self.users()
        totalUsers = len(users)
        logMe("Please wait... "+str(totalUsers)+" user profiles to run")
        bios = []
        numComplete = 0
        #Start Percentage Print Values
        y = 0
        tenth = len(users) / 10
        check = tenth
        percent = 10
        #End Percentage Print values
        for i in users:
            bios.append(self.bios(i))
            #Start Print Percentage
            y += 1
            if y >= check:
                logMe(str(percent) + "% completed")
                percent += 10
                check += tenth
                #end Print Percentage
        return(bios)


    def runProf(self):
        users  = self.users()
        totalUsers = len(users)
        logMe("Please wait... " + str(totalUsers) + " user profiles to run")
        profiles = {}
        numComplete = 0
        #Start Percentage Print Values
        y = 0
        tenth = len(users) / 10
        check = tenth
        percent = 10
        #End Percentage Print values
        for i in users:
            profiles[i] = self.participantStrucCreator(i)
            #Start Print Percentage
            y += 1
            if y >= check:
                logMe(str(percent) + "% completed")
                percent += 10
                check += tenth
                #end Print Percentage
        return(profiles)

    def runMsgs(self):
        Msgs  = self.messages
        totalMsgs = len(Msgs)
        logMe("Please wait... " + str(totalMsgs) + " message profiles to run")
        profiles = {}
        numComplete = 0
        #Start Percentage Print Values
        y = 0
        tenth = len(Msgs) / 10
        check = tenth
        percent = 10
        #End Percentage Print values
        for i in Msgs:
            profiles[i['ID']] = self.messageStrucCreator(i['ID'])
            #Start Print Percentage
            y += 1
            if y >= check:
                logMe(str(percent) + "% completed")
                percent += 10
                check += tenth
                #end Print Percentage
        return(profiles)

    def runThreads(self):
        threads  = self.threads
        totalThreads = len(threads)
        logMe("Please wait... " + str(totalThreads) + " thread profiles to run")
        profiles = {}
        numComplete = 0
        #Start Percentage Print Values
        y = 0
        tenth = len(threads) / 10
        check = tenth
        percent = 10
        #End Percentage Print values
        for i in threads:
            profiles[i] = self.threadStrucCreator(i)
            #Start Print Percentage
            y += 1
            if y >= check:
                logMe(str(percent) + "% completed")
                percent += 10
                check += tenth
                #end Print Percentage
        return(profiles)

    def threadStrucCreator(self, msgID):
        """This function created a data structure from a parsed list-serv that is focused on analizing individual message threads """
    #Check if msg is the start of a thread, or if it is in a thread.
        participants = []
        bodies = []
        times = []
        gender = []
        cTimes = []
    #get the content of the original message
        for i in self.messages:
            if i['ID'] == msgID:
                msg = i
    #get thread message is in
        if msg["References"] == []:
            threadID = msg["ID"]
        else:
            for i in msg["References"]:
                if i in self.threads:
                    threadID = i
    #get messages in thread
        msgs = self.threads[threadID]
    #get participants list, body's, and times
    #first get the thread starter
        for t in self.messages:
            if t['ID'] == threadID:
                participants.append(t['Name'])
                bodies.append(t['ScrapedBody'])
                cTimes.append(t['compactDate'])
                times.append(t['Date'])
    #Then get the thread particpants
        for i in msgs:
            for k in self.messages:
                if k['ID'] == i:
                    participants.append(k['Name'])
                    bodies.append(k['ScrapedBody'])
                    cTimes.append(k['compactDate'])
                    times.append(k['Date'])
    #get number of participants genders
        for i in participants:
            gender.append(self.gender(i))
        genderVariance = {}
        for i in gender:
            if i in genderVariance:
                genderVariance[i] +=1
            else:
                genderVariance[i] = 1
    #get total writing time for thread
        threadLen = 0
        for i in bodies:
            msgLen = float(i.__len__())/float(228) #228 is the avg (char) per minute I pulled from the internet
            #TODO create this as a variable that can be set by a researcher in case they have more focused data on the communities typing ability... will not happen... but, just in case.
            threadLen += msgLen

    #get the difference between the start time of the thread and the last post on the thread.
        timeDiff = self.makeTimeDiff(float(cTimes[-1])-float(cTimes[0]))
                
        threads = {
            "ThreadID":threadID,
            "writingtime": threadLen,
            "startTime": times[0],
            "endTime": times[-1],
            "calendartime":timeDiff,
            "genderBalance": genderVariance,
            "messages":msgs,
            'type':"thread",
            'list':self.threadName,
            "participants":participants,
            }
        return(threads)

    def makeTimeDiff(self, timeDiff):
        printTime = str(timeDiff)
        printTime = printTime[:-2]
        timeSize = len(printTime)
        if timeSize <= 2:
            calTime = printTime + " seconds"
        elif timeSize > 10:
            calTime = printTime[-12:-10] + " years " + printTime[-10:-8] + " months " + printTime[-8:-6] + " days " + printTime[-6:-4] + " Hours " + printTime[-4:-2] + " minutes and " + printTime[-2:] + " seconds"
        elif timeSize > 8:
            calTime = printTime[-10:-8] + " months " + printTime[-8:-6] + " days " + printTime[-6:-4] + " Hours " + printTime[-4:-2] + " minutes and " + printTime[-2:] + " seconds"
        elif timeSize > 6:
            calTime = printTime[-8:-6] + " days " + printTime[-6:-4] + " Hours " + printTime[-4:-2] + " minutes and " + printTime[-2:] + " seconds"
        elif timeSize > 4:
            calTime = printTime[-6:-4] + " Hours " + printTime[-4:-2] + " minutes and " + printTime[-2:] + " seconds"
        elif timeSize > 2:
            calTime = printTime[:-2] + " minutes and " + printTime[-2:] + " seconds"
        return calTime

    def messageStrucCreator(self, msgID):
        """This function created a data structure from a parsed list-serv that is focused on analizing individual messages """
        #Get full message
        for i in self.messages:
            if i['ID'] == msgID:
                message = i
        #Get Thread ID
        if message['References'] and message['References'][0]:
            threadID = message['References'][0]
        else:
            threadID = msgID
        #Define Message Types (fwd:, re:, )
        if re.findall("^.*[fF]wd\:.*", message['Subject']) != []:
            msgType = "fwd"
        elif message['ID'] in self.threads:
            msgType = "new"
        #need to be able to identify reply's within a thread and those that conclude the thread. Will do this on next round.
        else:
            msgType = "reply"
        #define time spent on a message
        msgLen = message['ScrapedBody'].__len__()
        time = float(msgLen)/float(228)
        #Get Gender
        genderGuess = self.gender(message['Name'])
        messages = {
            "msgID":msgID,
            "date":message['Date'],
            "threadID":threadID,
            "participantID":message['Name'],
            "msgType":msgType,
            "minutes":time,
            'type':"message",
            'list':self.threadName,
            "gender":genderGuess,
            }
        return(messages)

    def participantStrucCreator(self, name):
        """This function created a data structure from a parsed list-serv that is focused on analizing individual list-serv participants """
	#Do Stuff
        bodies = []
        dates = []
        cDates = []
        for i in self.messages:
            if i['Name'] == name:
                cDates.append(i['compactDate'])
                bodies.append(i['ScrapedBody'])
                dates.append(i['Date'])
        #get message ID's they have used.
        userMsgs, totalMsgs = self.totalMessages(name)
        #get total user responses by a user
        replyID, replyNum = self.allReplys(name)
        #get "response Metric" (replies/total#)
        responseMtrc = float(replyNum)/float(totalMsgs)
        #get total user initiated posts by a user
        userInitiated, numInitiated = self.newMessages(name)
        #get "starter metric - threads started / total #"
        starterMtrc = float(numInitiated)/float(totalMsgs)
        #get total writing time for user
        userLen = 0
        for i in bodies:
            msgLen = float(i.__len__())/float(228) #228 is the avg (char) per minute I pulled from the internet
            userLen += msgLen

        #Get Gender
        genderGuess = self.gender(name)
        #control metric - # of replies / # threads started by participant
        if numInitiated != 0:
            cntrlMtrc = float(replyNum)/float(numInitiated)
        else:
            cntrlMtrc = 0
        #ENGAGEMENT  = "Average number of replies a user has per thread"
        usrThreads = {}
        if replyID != 0:
            for i in replyID:
                for n in self.threads.iteritems():
                    if n[1] != []:
                        if i in n[1]:
                            if n[0] in usrThreads:
                                usrThreads[n[0]] += 1
                            else:
                                usrThreads[n[0]] = 1
            totalRep = 0
            repNum = 0
            for i in usrThreads.iteritems():
                repNum += 1
                totalRep += i[1]
            if repNum != 0:
                userRepPerThread = float(totalRep)/float(repNum)
            else:
                userRepPerThread = 0
        #the average ammount of replies this individual gets per thread they start
        threadReplies = []
        for i in userInitiated:
            repCount = 0
            if self.threads[i] != []:
                for n in self.threads[i]:
                    repCount += 1
                threadReplies.append(repCount)
            else:
                threadReplies.append(0)
        totalRep = 0
        repNum = 0
        for i in threadReplies:
            repNum += 1
            totalRep += i
        if repNum != 0:
            repPerThread = float(totalRep)/float(repNum)
        else:
            repPerThread = 0
        
#We need to decide on how to measure this. conversationGenerator = "conversation generator metric - threads started / average number of replies to thread (or total? not sure)"
        
        participants = {
            'name':name,
            'type':"participant",
            'list':self.threadName,
            'totalPosts':totalMsgs,
            'response':responseMtrc,
            'starter':starterMtrc,
            'control':cntrlMtrc,
            'gender':genderGuess,
            'entryTime':self.First[name]['Date'],
            'lastPost':dates[-1],
            'messages':replyID,
            'threads':userInitiated,
            'timeSpent':userLen,
            'engagement':userRepPerThread,
            'averageReplies':repPerThread
            }
        return participants


def runTest(b):
    #needs to mimic the below... it does not currently.
    #reload(main); a=main.converter(); a.getArchive('testtext'); a.defRegular('mailman'); a.firstPost()
    a = converter()
    a.getArchive(b)
    a.defRegular("mailman")
    a.firstPost()
