
from panoramisk.manager import Manager
import asyncio
from time import time #, sleep
import inspect



class Pano:
    def __init__(self, host="127.0.0.1", port=5038, login="login", password="password"):
        # Help variables
        self.helpAll=self.Cache(self._help_feedFull,timeout=None)
        self.helpDetail={}
        self.helpDetailTimeout=None
        # Channels variables
        self.channelCache=self.Cache(self._chan_feed,timeout=1)
        # Endoints variables
        self.epAll=self.Cache(self._ep_feedFull,timeout=2)
        self.epDetail={}
        self.epDetailTimeout=60*5
        self.epGrpVar={}
        self.epGrpVar["_"]={}
        self.epGrpVar["_"]['NoGroup']=[]
        self.epGrpVar["_"]['All']=[]

        self.cache=self.Cache(self)

        self.trackeurAMI={}
        self.trackeurAMI['Originate']={}
        self.manager = Manager(host=host,port=port,username=login,secret=password,forgetable_actions=('login',))

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
                print('👻 Generating cache')
                if self.func:
                    if self.funcarg:
                        self.cache=await self.func(self.funcarg)
                    else:
                        self.cache=await self.func()
                self.timeput=time()

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
                    print('👻 Not in cache')
                    return(self.defaultValue)
                else:
                    print('👻 Lost in cache')
                    return(self.cache[key])
            elif key in self.cache.keys():
                print('👻 Using cache')
                return(self.cache[key])
            else:
                print('👻 Not in cache')
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
        #if not len(await self.helpAll.keys()): # On force un reload
        #    self.helpAll=self.Cache(self._help_feedFull,timeout=600)

        if not key:
            print('🦆 gt Help None')
            return(await self.helpAll.dict())

        if key not in self.helpDetail.keys():
            self.helpDetail[key]=self.Cache(self._help_feedOne,funcarg=key,timeout=self.helpDetailTimeout)
        return(await self.helpDetail[key].dict())

    async def help_keys(self):
        print('🦆 ke Help D')
        #if not len(await self.helpAll.keys()): # On force un reload
        #    self.helpAll=self.Cache(self._help_feedFull,timeout=600)
        print(self.helpAll)
        print('🦆 ke Help E')
        return(await self.helpAll.keys())


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
        return(await self.channelCache.dict())

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
        print('📵 Integration ou Réintegration de poste')
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
        for varName in self.epGrpVar.keys():
            for varValue in self.epGrpVar[varName]:
                if ep in self.epGrpVar[varName][varValue]:
                    self.epGrpVar[varName][varValue].remove(ep)
        # Rajoute du phone dans tout les groupes existant
        for k in var.keys():
            v=var[k]
            if k not in self.epGrpVar.keys():
                self.epGrpVar[k]={}
            if v not in self.epGrpVar[k].keys():
                self.epGrpVar[k][v]=[]
            self.epGrpVar[k][v].append(ep)
        if len(var) == 0:
            self.epGrpVar["_"]["NoGroup"].append(ep)
        # Plus c'est bourrin plus c'est bon....
        self.epGrpVar["_"]["All"].append(ep)
        return(var)

    #async def endpoint(self,name):
    async def endpoint(self,ep):
        if ep.startswith('IAX2/'):
            if ep not in self.epGrpVar["_"]:
                self.epGrpVar["_"]['NoGroup'].append(ep)
            return(await self.epAll.get(ep))
        ret={}
        ret=await self.epAll.get(ep)
        if ep not in self.epDetail.keys():
            self.epDetail[ep]=self.Cache(self._ep_feedOne,funcarg=ep,timeout=self.epDetailTimeout)
        Vars=await self.epDetail[ep].dict()
        ret['Vars']={}
        for k in Vars.keys():
            ret['Vars'][k]=Vars[k]
        return(ret)

    async def endpoints(self):
        print('☎️  start')
        #if not len(self.epAll):
        #    self.epAll=self.Cache(self._ep_feedFull,timeout=10)
        #print(await self.epAll.dict())

        result=await self.epAll.dict()
        ret={}
        keysCacheToKill=list(self.epDetail.keys())
        for ep in await self.epAll.keys():
            ret[ep]=await self.endpoint(ep)
            if ep in keysCacheToKill:
                keysCacheToKill.remove(ep)
        for ep in keysCacheToKill:
            self.epDetail.remove(ep)
            # Suppression de tout les groupes existant du phone
            for varName in self.epGrpVar.keys():
                for varValue in self.epGrpVar[varName]:
                    if ep in self.epGrpVar[varName][varValue]:
                        epGrpVar[varName][varValue].remove(ep)
        print(f'☎️  stop')
        return(ret)

    async def endpointsGrp(self,grp=None):
        await self.endpoints()
        if grp:
            return({grp:self.epGrpVar[grp]})
        else:
            return(self.epGrpVar)


    ####### PROTOCOL !!!!!
    def startup(self):
        print("Connexion a l'AMI")
        self.manager.register_event('*', self.on_event_OriginateResponse)
        self.manager.connect()

    async def wait_for_protocol(self):
        """
        Attend que la connexion soit prête
        """
        #for i in range(20):  # max 2 secondes
        for i in range(5):  # max 2 secondes
            if self.manager.protocol:
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
    
        if event.event == "Hangup" and isinstance(event.Uniqueid, str) and event.Uniqueid in self.trackeurAMI['Originate']:
            print(f"Événement : {event.event} END")
            del(self.trackeurAMI['Originate'][event.Uniqueid])
    
        if event.event == 'Newchannel' and isinstance(event.Uniqueid, str) and event.Uniqueid in self.trackeurAMI['Originate']:
            print(f"Événement : {event.event} FOUNDING")
            self.trackeurAMI['Originate'][event.Uniqueid]['Channel']=event.Channel
    
        #if event.Uniqueid in trackeurAMI['Originate'].keys():
        #    print(f"Événement : {event.event}")
        #    print(event)
    
        if event.event not in ['TestEvent','FullyBooted','SuccessfulAuth','VarSet'] and 1 == 2:
            print(f"Événement : {event.event}")
            print(event)
            if event.name == 'OriginateResponse':
                print("Channel ID :", event.get('Channel'))

    async def action(self,param=None,MAX_RETRIES=3,RETRY_DELAY=3):
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
    
        print(f'⚡️ Last Action {hero}')
        await self.wait_for_protocol()
    
        #for attempt in range(1, cfg['MAX_RETRIES'] + 1):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(self.manager.send_action(hero), timeout=RETRY_DELAY)
                print(f"👽️ Last action hero {hero}")
                break
            except (asyncio.TimeoutError, ConnectionError) as e:
                print(f"⚠️ Tentative {attempt} échouée : {e}")
                if attempt < MAX_RETRIES:
                    print(f"⏳ Nouvelle tentative dans {RETRY_DELAY} secondes...")
                    self.manager.close()
                    await asyncio.sleep(RETRY_DELAY/2)
                    #manager.register_event('OriginateResponse', on_event_OriginateResponse)
                    self.manager.register_event('*', self.on_event_OriginateResponse)
                    self.manager.connect()
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







