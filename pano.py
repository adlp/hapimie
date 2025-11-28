
from panoramisk.manager import Manager
import asyncio
from time import time #, sleep
from datetime import datetime
import inspect

class Pano:
    def __init__(self, host="127.0.0.1", port=5038, login="login", password="password"):
        # TODO prefixer toutes les variables internes d'un _ .... :-/
        # Help variables
        self._helpAll=self.Cache(self._help_feedFull,timeout=None)
        self._helpDetail={}
        self._helpDetailTimeout=None
        # Channels variables
        self._channelCache=self.Cache(self._chan_feed,timeout=1)
        # Endoints variables
        self._epAll=self.Cache(self._ep_feedFull,timeout=2)
        self._epDetail={}
        self._epDetailTimeout=60*30
        self._epGrpVar={}
        self._epGrpVar["_"]={}
        self._epGrpVar["_"]['NoGroup']=[]
        self._epGrpVar["_"]['All']=[]
        # Queue variables
        self._queues=self.Cache(self._feed_queues,timeout=5)
        # DBVars
        self._db=self.Cache(self._feed_db,splitKeyKey="/",timeout=1)
        self._db_hidden=['subscription_persistence','registrar','CustomPresence','CustomDevstate','pbx']

        #self.cache=self.Cache(self)

        self._trackeurAMI={}
        self._trackeurAMI['Originate']={}
        self._manager = Manager(host=host,port=port,username=login,secret=password,forgetable_actions=('login',))

    class Cache:
        def __init__(self,func: callable=None,funcarg=None,defaultValue=None,splitKeyKey=None,timeout=5):
            self.func=func
            self.funcarg=funcarg
            self.timeout=timeout
            self.timeput=int(time())
            self.defaultValue=defaultValue
            self.splitKK=splitKeyKey
            self.cache={}

        async def _tryOrGet(self,Force=False):
            if Force or len(self.cache)==0 or ( self.timeout and int(time())-self.timeput > self.timeout):
            #if len(self.cache)==0 or int(time())-self.timeput > self.timeout or Force:
                #print('👻 Generating cache')
                if self.func:
                    if self.funcarg:
                        result=await self.func(self.funcarg)
                    else:
                        result=await self.func()
                    if not result:
                        result={}
                    self.cache=result
                self.timeput=time()

        async def reloadCache(self):
            self._tryOrGet(Force=True)

        def _getRecursif(self,keys,cache={}):
            if keys[1:] in cache.keys:
                if len(keys)>1:
                    return(self._getRecursif(keys[1:]))
                else:
                    return(cache[keys[1:]])
            else:
                return(self.defaultValue)

        async def get(self,key,splitKey=False):
            await self._tryOrGet()
            if splitKey:
                # On considere None la valeur d'arret dans la recherche recursive
                return(self._getRecursif(key.split(self.splitKK),self.cache))
            elif isinstance(self.cache,list):
                if key>len(self.cache):
                    #print('👻 Not in cache')
                    return(self.defaultValue)
                else:
                    #print('👻 Lost in cache')
                    return(self.cache[key])
            elif key in self.cache.keys():
                #print('👻 Using cache')
                return(self.cache[key])
            else:
                #print('👻 Not in cache')
                return(self.defaultValue)

        async def __len__(self):
            self._tryOrGet()
            return(len(self.cache))

        async def dict(self):
            await self._tryOrGet()
            return(self.cache)

        async def keys(self):
            await self._tryOrGet()
            if isinstance(self.cache,list):
                return(range(1,len(self)))
            else:
                return(self.cache.keys())

    def _decoupe_lexique(self,chaine: str):
        """
        Découpe une chaîne en (commande, description).
        Supposé que la commande est le premier mot non vide,
        suivi d'espaces, puis la description.
        """
        # Nettoyer les espaces en début/fin
        chaine = chaine.strip()
    
        # Découper sur les espaces multiples
        import re
        parties = re.split(r'\s{2,}', chaine)
    
        if len(parties) >= 2:
            commande = parties[0].strip()
            description = " ".join(parties[1:]).strip()
            return commande, description
        else:
            return chaine, ""

    async def _help_feedFull(self):
        print('🦆 ff Help')
        hero = {"Action": "Command","command": "manager show commands"}
        result=await self.action(hero)
        if result and 'Output' in result.keys() and isinstance(result['Output'],list):
            result['Commands']={}
            for ligne in result['Output']:
                cmd,desc=self._decoupe_lexique(ligne)
                if cmd not in ['Action','------']:
                    result['Commands'][cmd]=desc
            del(result['Output'])
        else:
            return(None)
        return({'Commands':result['Commands']})

    async def _help_feedOne(self,command):
        print(f'🦆 fo Help {command}')
        hero = {"Action": "Command","command": f"manager show command {command}"}
        result=await self.action(hero)
        syntax={}
        
        for ligne in result['Output']:
            if len(ligne)==0:
                break
            neli=ligne.replace('[','').replace(']','').split(':',2)
            if len(neli) != 2:
                continue
            if neli[0] in [ "Syntax","Action","ActionID" ]:
                continue
            syntax[neli[0]]=neli[1]
        print(f'🦆 fo Help {command}=')
        print({'text':result,'syntax':syntax})
        return({'text':result['Output'],'syntax':syntax})

    async def help(self,key):
        print('🦆 gt Help')
        #if not len(await self._helpAll.keys()): # On force un reload
        #    self._helpAll=self.Cache(self._help_feedFull,timeout=600)

        if not key:
            print('🦆 gt Help None')
            return(await self._helpAll.dict())

        if key not in self._helpDetail.keys():
            self._helpDetail[key]=self.Cache(self._help_feedOne,funcarg=key,timeout=self._helpDetailTimeout)
        return(await self._helpDetail[key].dict())

    async def help_keys(self):
        print('🦆 ke Help D')
        #if not len(await self._helpAll.keys()): # On force un reload
        #    self._helpAll=self.Cache(self._help_feedFull,timeout=600)
        print(self._helpAll)
        print('🦆 ke Help E')
        return(await self._helpAll.keys())


    async def _chan_feed(self):
        hero = {'Action':"Status","AllVariables":"True"}
        allChan=await self.action(hero)
        ret={}
        ret['Channels']={}
        ret['Phones']={}
        ret['Caller']={}
        lnkt={}
    
        if not isinstance(allChan, list):
            allCahn=[]
    
        for call in allChan:
            if 'error' == call:
                continue
            ret['Channels'][call['Channel']]=call
            lnkt[call['Uniqueid']]=call['Channel']
    
        for call in allChan:
            if 'error' == call:
                continue
            phone=call['Channel'].split('-')[0]
            if call['Linkedid'] in lnkt.keys():
                ret['Channels'][call['Channel']]['_Linkedid']=lnkt[call['Linkedid']]
            if 'DNID' in call.keys() and call['Uniqueid'] == call['Linkedid']:
                ret['Channels'][call['Channel']]['_Call']=call['DNID']
                ret['Caller'][call['Channel']]=[]
            else:
                ret['Channels'][call['Channel']]['_Call']='_Receiving'
            ret['Channels'][call['Channel']]['_Phone']=phone
    
            if phone not in ret['Phones']:
                ret['Phones'][phone]=[]
            ret['Phones'][phone].append(call['Channel'])
    
            if 'Variable' in call.keys():
                ret['Channels'][call['Channel']]['Variables']={}
                if isinstance(call['Variable'],str):
                    clef,val=call['Variable'].split('=',1)
                    ret['Channels'][call['Channel']]['Variables'][clef]=val
                else:
                    for ligne in call['Variable']:
                        if '=' not in ligne:
                            print(f'[ERR][/api/status] Erreure Analyse {ligne}')
                            pprint(allChan)
                            continue
                        clef,val=ligne.split('=',1)
                        ret['Channels'][call['Channel']]['Variables'][clef]=val
    
        if len(ret['Caller']):
            for call in allChan:
                if '_Linkedid' in call and ret['Channels'][call['Channel']]['_Call']=='_Receiving':
                    ret['Caller'][call['_Linkedid']].append(call['Channel'])
        return(ret)

    async def channels(self):
        """
            Liste tout les channels et renvoie le json correspondant
            En rajoutant des aides et de l'usage du cache
            Renvoie le status.... hmmmm ca ressemble a un coreshowchannel
        """
        return(await self._channelCache.dict())

    async def channel_del(self,channelid=None):
        hero={'action':'HangUp', 'Channel': channelid,'Cause': 'API Call' }
        if not channelid:
            return(None)
        else:
            return(await self.action(hero))

    async def _ep_feedFull(self):
        print('📵📵')
        import re
        result=await self.action("PJSIPShowEndpoints")
        ret={}
        for ep in result:
            techObjN='PJSIP/'+ep['ObjectName']
            ret[techObjN]={}
            ret[techObjN]['ObjectName']=ep['ObjectName']
            ret[techObjN]['Type']='PJSIP'
            ret[techObjN]['Up']=True
            if ep['DeviceState']=="Unavailable":
                ret[techObjN]['Up']=False
            ret[techObjN]['Contacts']=None
            if 'Contacts' in ep.keys() and len(ep['Contacts']):
                ret[techObjN]['Contacts']=re.findall(r'@(\d+\.\d+\.\d+\.\d+)',ep['Contacts'])
            ret[techObjN]['Full']=ep
        result=await self.action("IAXpeerlist")
        for ep in result:
            techObjN='IAX2/'+ep['ObjectName']
            ret[techObjN]={}
            ret[techObjN]['ObjectName']=ep['ObjectName']
            ret[techObjN]['Type']='IAX2'
            ret[techObjN]['Up']=True
            if ep['Status']=="UNKNOWN":
                ret[techObjN]['Up']=False
            ret[techObjN]['Contacts']=None
            if ep['IPaddress']=="(null)":
                ret[techObjN]['Contacts']=[ ep['IPaddress'] ]
            ret[techObjN]['Full']=ep
        return(ret)

    async def _ep_feedOne(self,command):
        #print('📵 Integration ou Réintegration de poste')
        var={}
        if command.startswith("PJSIP"):
            hero={"Action":"PJSIPShowEndpoint","Endpoint": command[6:]}
            result=await self.action(hero)
            if 'SetVar' in result[0].keys() and len(result[0]['SetVar']):
                noinitvarsip=0
                for ligne in result[0]['SetVar'].split(','):
                    k,v=ligne.split('=',1)
                    var[k]=v
        ep=command
        # Suppression de tout les groupes existant du phone
        for varName in self._epGrpVar.keys():
            for varValue in self._epGrpVar[varName]:
                if ep in self._epGrpVar[varName][varValue]:
                    self._epGrpVar[varName][varValue].remove(ep)
        # Rajoute du phone dans tout les groupes existant
        # TODO creer un Sous groupe (v) none lorsque 'un poste est nulle part..
        # Le pb c'est qu'il ne sait pas qu'il est nulle part.... AAAAAHhh
        for k in var.keys():
            v=var[k]
            if k not in self._epGrpVar.keys():
                self._epGrpVar[k]={}
            if v not in self._epGrpVar[k].keys():
                self._epGrpVar[k][v]=[]
            self._epGrpVar[k][v].append(ep)
        if len(var) == 0: # and ep not in self._epGrpVar["_"]["NoGroup"]:
            self._epGrpVar["_"]["NoGroup"].append(ep)
        # Plus c'est bourrin plus c'est bon....
        self._epGrpVar["_"]["All"].append(ep)
        return(var)

    #async def endpoint(self,name):
    async def endpoint(self,ep):
        if ep.startswith('IAX2/'):
            if ep not in self._epGrpVar["_"]["NoGroup"]:
                self._epGrpVar["_"]['NoGroup'].append(ep)
            return(await self._epAll.get(ep))
        ret={}
        ret=await self._epAll.get(ep)
        if ep not in self._epDetail.keys():
            self._epDetail[ep]=self.Cache(self._ep_feedOne,funcarg=ep,timeout=self._epDetailTimeout)
        Vars=await self._epDetail[ep].dict()
        ret['Vars']={}
        for k in Vars.keys():
            ret['Vars'][k]=Vars[k]
        return(ret)

    async def endpoints(self):
        #print('☎️  start')
        #if not len(self._epAll):
        #    self._epAll=self.Cache(self._ep_feedFull,timeout=10)
        #print(await self._epAll.dict())

        result=await self._epAll.dict()
        ret={}
        keysCacheToKill=list(self._epDetail.keys())
        for ep in await self._epAll.keys():
            ret[ep]=await self.endpoint(ep)
            if ep in keysCacheToKill:
                keysCacheToKill.remove(ep)
        for ep in keysCacheToKill:
            self._epDetail.remove(ep)
            # Suppression de tout les groupes existant du phone
            for varName in self._epGrpVar.keys():
                for varValue in self._epGrpVar[varName]:
                    if ep in self._epGrpVar[varName][varValue]:
                        epGrpVar[varName][varValue].remove(ep)
        #print(f'☎️  stop')
        return(ret)

    async def endpointsGrp(self,grp=None):
        await self.endpoints()
        if grp:
            return({grp:self._epGrpVar[grp]})
        else:
            return(self._epGrpVar)

    def _format_epoch(self,epoch=int(datetime.now().timestamp())):
        if epoch==0:
            return(0)
        # Si le timestamp est en millisecondes, on le convertit en secondes
        if epoch > 1e12:
            epoch = epoch / 1000
    
        dt = datetime.fromtimestamp(epoch)
        return dt.strftime("%d/%m/%Y %H:%M:%S")

    async def queues(self):
        print('🐍')
        return(await self._queues.dict())

    async def _feed_queues(self):
        ret={}
        statusConverter=['Unknown','Not Inuse','Inuse','Busy','Invalid','Unavailable','Ringing','Ringinuse','Onhold']
        for queue in await self.action('QueueSummary'):
            queName=queue['Queue']
            ret[queName]={}
            for k in ['Event','Queue']:
                del(queue[k])
            ret[queName]['QueueEntry']={}
            ret[queName]['QueueParams']=queue
            ret[queName]['QueueMember']={}
        for bloc in await self.action('QueueStatus'):
            queName=bloc['Queue']
            if bloc['Event'] == "QueueEntry":
                ret[queName]['QueueEntry'][bloc['Channel']]=bloc
            elif bloc['Event'] == "QueueMember":
                bloc['_Status']=statusConverter[int(bloc['Status'])]
                if bloc['Paused']=="1":
                    bloc['_Status']+="/Pause"
                for k in ['LastCall','LastPause','LoginTime']:
                    bloc[k]= self._format_epoch(int(bloc[k]))
                for k in ['Event','Queue']:
                    del(bloc[k])
                ret[queName]['QueueMember'][bloc['Name']]=bloc
            elif bloc['Event'] == "QueueParams":
                for k in bloc.keys():
                    if k in ['Event','content','Queue']:
                        continue
                    ret[queName]['QueueParams'][k]=bloc[k]
                ret[queName]['QueueParams']['content']+="/"+bloc['content']
            else:
                # raise
                print('QUEUE : Event inconnu')
        return(ret)

    #self._db=self.Cache(self._feed_db,splitKeyKey="/",timeout=5)
    async def _feed_db(self):
        resultat={}
        hero = {"Action": "Command","command": "database show"}
        resp=await self.action(hero)
        datas=resp['Output']
        datas.pop()
        for ligne in datas:
            cmd,desc=ligne.split(':',1)
            chemin=cmd.rstrip()[1:]
            cles=chemin.split('/')
            valeur=desc[1:].rstrip()
            courant = resultat
            for cle in cles[:-1]:
                courant=courant.setdefault(cle,{})
            courant[cles[-1]]=valeur
        return(resultat)

    async def db_get(self,key=None,hidden=None,idx=True):
        print('💽')

        ret=await self._db.dict()
        if key is None:
            print('🔐')
            if not hidden:
                hidden=self._db_hidden
            for k in hidden:
                if k in ret:
                    del(ret[k])

            return(ret)
        elif "/" in key:
            cles=key.split('/')
            courant=ret
            for cle in cles:
                if isinstance(courant,dict) and cle in courant:
                    courant=courant[cle]
                elif cle not in courant:
                    return(None)
            #if not idx:
            #    return(courant)
            return({ key:courant})
        else:
            if not idx:
                return(ret[key])
            return({ key:ret[key]})

    async def db_set(self,key,value):
        print('🚒 db_set')
        if not(len(key)):
            return(None)
        #elif await self.db_get(key) and "/" in key:
        else:
            print(f'DBSET db[{key}]={value}')
            cutted=key.split('/')
            family='/'.join(cutted[:-1])
            k=str(cutted[-1])
            hero = {'Action':"DBPut","Family":family,'Key':k,'Val':value}
            print(hero)
            ret=await self.action(hero)
            await self._db.reloadCache()
            return(ret)
        #else:
        #    return(None)

    async def originate(self,Channel,Exten=None,Context=None,Priority=None,Application=None,Data=None,Timeout=None,
            CallerID=None,Variable=None,Account=None,EarlyMedia=None,Async=None,Codecs=None,ChannelId=None,OtherChannelId=None):
        print('PINK ALERTE PINK ALERTE')
        hero={}
        hero['Action']='Originate'
        print('⚡️')
        for key,value in {"Channel":Channel,"Exten":Exten,"Context":Context,"Priority":Priority,"Application":Application,"Data":Data,"Timeout":Timeout,
                "CallerID":CallerID,"Variable":Variable,"Account":Account,"EarlyMedia":EarlyMedia,"Async":Async,"Codecs":Codecs,"ChannelId":ChannelId,"OtherChannelId":OtherChannelId}.items():
            if value is not None:
                print(value)
                if key == "Variable":
                    hero[key]=",".join(f"{k}={v}" for k, v in value.items())
                else:
                    hero[key]=value

        print('⚡️')
        print(hero)
        resultat=await self.action(hero)
        #resultat={}
        print(resultat)
        print('⚡️⚡️')
        return(resultat)

    ####### PROTOCOL !!!!!
    def startup(self):
        print("Connexion a l'AMI")
        self._manager.register_event('*', self.on_event_OriginateResponse)
        self._manager.connect()

    async def wait_for_protocol(self):
        """
        Attend que la connexion soit prête
        """
        #for i in range(20):  # max 2 secondes
        for i in range(5):  # max 2 secondes
            if self._manager.protocol:
                return
            print(f"Reconnexion a l'AMI {i}")
            await asyncio.sleep(0.2)
        raise RuntimeError("Connexion AMI non établie")
    
    # Fonction de gestion d'événement
    def on_event_OriginateResponse(self,manager,event):
    
        #if isinstance(event.Uniqueid, str) and event.Uniqueid.startswith('Hapimie-') and event.event not in ['VarSet','Newexten']:
        #    print(f"Événement : {event.event} LOOK")
        #    print(trackeurAMI)
        #    print(event)
    
        if event.event == "Hangup" and isinstance(event.Uniqueid, str) and event.Uniqueid in self._trackeurAMI['Originate']:
            print(f"Événement : {event.event} END")
            del(self._trackeurAMI['Originate'][event.Uniqueid])
    
        if event.event == 'Newchannel' and isinstance(event.Uniqueid, str) and event.Uniqueid in self._trackeurAMI['Originate']:
            print(f"Événement : {event.event} FOUNDING")
            self._trackeurAMI['Originate'][event.Uniqueid]['Channel']=event.Channel
    
        #if event.Uniqueid in trackeurAMI['Originate'].keys():
        #    print(f"Événement : {event.event}")
        #    print(event)
    
        if event.event not in ['TestEvent','FullyBooted','SuccessfulAuth','VarSet'] and 1 == 2:
            print(f"Événement : {event.event}")
            print(event)
            if event.name == 'OriginateResponse':
                print("Channel ID :", event.get('Channel'))

    async def action(self,param=None,MAX_RETRIES=3,RETRY_DELAY=3,debug=False):
        """
        Envoie une action AMI via Panoramisk et transforme la réponse en dictionnaire(s) nettoyé(s).
        - Supprime les clés inutiles comme 'ActionID'
        - Gère les réponses multiples (listes d'événements)
        TODO: mieux gerer le wait_for_protocol
        """
        if param is None:
            hero={"Action": "ping"}
        if type(param) == dict:
            hero=param
        elif type(param) == str:
            hero={"Action": param}
        else:
            hero={"Action": "ping"}

        if debug:
            print(f'⚡️ Last Action {hero}')
        await self.wait_for_protocol()
    
        #for attempt in range(1, cfg['MAX_RETRIES'] + 1):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(self._manager.send_action(hero), timeout=RETRY_DELAY)
                #print(f"👽️ Last action hero {hero}")
                break
            except (asyncio.TimeoutError, ConnectionError) as e:
                print(f"⚠️ Tentative {attempt} échouée : {e}")
                if attempt < MAX_RETRIES:
                    print(f"⏳ Nouvelle tentative dans {RETRY_DELAY} secondes...")
                    self._manager.close()
                    await asyncio.sleep(RETRY_DELAY/2)
                    #manager.register_event('OriginateResponse', on_event_OriginateResponse)
                    self._manager.register_event('*', self.on_event_OriginateResponse)
                    self._manager.connect()
                    await asyncio.sleep(RETRY_DELAY/2)
                else:
                    print("💥 Plantage après 3 tentatives.")
                    response={"error": "Plantage après 3 relances inefficaces"}
                    break
        def clean(entry):
            d = dict(entry.items()) if hasattr(entry, "items") else entry
            if not isinstance(d, dict):
                return None
            if d.get("EventList") in ("start", "Complete"):
                return None
            return {k: v for k, v in d.items() if k != "ActionID"}
    
        if isinstance(response, list):
            return [r for r in (clean(item) for item in response) if r]
        elif hasattr(response, "items"):
            cleaned = clean(response)
            return cleaned if cleaned else {}
        else:
            return {"raw": str(response)}

    ### A REFAIRE
    async def statusi(self):
        hero = {'Action':"Status","AllVariables":"True"}
        ret= self.fromcache('status',None)
        if ret is None:
            ret=self.trichan(await self.action(hero))
            self.tocache('status',ret,1)
        return(ret)







