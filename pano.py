
from panoramisk.manager import Manager
import asyncio
from time import time #, sleep
import inspect



class Pano:
    def __init__(self, host="127.0.0.1", port=5038, login="login", password="password"):
        self.endpoints = self.Endpoints(self)
        self.queue = self.Queues(self)
        self.db = self.DB(self)
        self.channels = self.Channels(self)
        #self.channel = self.channels  # alias
        self.helps = self.Helps(self)

        self.cache=self.Cache(self)

        self.trackeurAMI={}
        self.trackeurAMI['Originate']={}
        self.manager = Manager(host=host,port=port,username=login,secret=password,forgetable_actions=('login',))

    class Cache:
        def __init__(self,func: callable=None,funcarg=None,defaultValue=None,timeout=5):
            self.func=func
            self.funcarg=funcarg
            self.timeout=timeout
            self.timeput=int(time())
            self.defaultValue=defaultValue
            self.cache={}

        async def _tryOrGet(self,Force=False):
            if len(self.cache)==0 or int(time())-self.timeput > self.timeout or Force:
                print('👻 Generating cache')
                if self.func:
                    if self.funcarg:
                        self.cache=await self.func(self.funcarg)
                    else:
                        self.cache=await self.func()
                self.timeput=time()

        def __getitem__(self,key: str):
            self._tryOrGet()
            if key not in self.cache.key():
                self._tryOrGet(True)
            else:
                print('👻 Using cache')
            if key not in self.cache.key():
                return(self.defaultValue)
            else:
                return(self.cache[key])

        def __getitem__(self,key: int):
            self._tryOrGet()
            if key > (len(self)-1):
                self._tryOrGet(True)
            else:
                print('👻 Using cache')
            if key > (len(self)-1):
                return(self.defaultValue)
            else:
                return(self.cache[key])

        async def __len__(self):
            self._tryOrGet()
            return(len(self.cache))

        async def dict(self):
            print('👻 Cache dict')
            await self._tryOrGet()
            return(self.cache)

        async def keys(self):
            print('👻 ke Cache D')
            await self._tryOrGet()
            if isinstance(self.cache,list):
                return(range(1,len(self)))
            else:
                return(self.cache.keys())
            print('👻 ke Cache E')

    class Helps:
        def __init__(self,pano):
            print('🦆 Init Help')
            self.pano=pano
            self.cmdAll=self.pano.Cache(self._feedFull,timeout=60)
            self.cmdTab={}
        def decoupe_lexique(self,chaine: str):
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
        async def _feedFull(self):
            print('🦆 ff Help')
            hero = {"Action": "Command","command": "manager show commands"}
            result=await self.pano.action(hero)
            if result and 'Output' in result.keys() and isinstance(result['Output'],list):
                result['Commands']={}
                for ligne in result['Output']:
                    cmd,desc=self.decoupe_lexique(ligne)
                    if cmd not in ['Action','------']:
                        result['Commands'][cmd]=desc
                del(result['Output'])
            else:
                return(None)
            return({'Commands':result['Commands']})
        async def __getitem__(self,key):
            print('🦆 gt Help')
            if not len(await self.cmdAll.keys()): # On force un reload
                self.cmdAll=self.pano.Cache(self._feedFull,timeout=60)

            if not key:
                print('🦆 gt Help None')
                return(await self.cmdAll.dict())
            print(f'🦆 gt Help {key}')
            #if key not in await self.cmdAll.keys():
            #    print('🦆 gt Help pas la clef')
            #    return(None)
            if key not in self.cmdTab.keys():
                self.cmdTab[key]=self.pano.Cache(self._feedOne,funcarg=key,timeout=60)
            return(await self.cmdTab[key].dict())

        async def _feedOne(self,command):
            print(f'🦆 fo Help {command}')
            hero = {"Action": "Command","command": f"manager show command {command}"}
            result=await self.pano.action(hero)
            ret={}
            
            for ligne in result['Output']:
                if len(ligne)==0:
                    break
                neli=ligne.replace('[','').replace(']','').split(':',2)
                if len(neli) != 2:
                    continue
                if neli[0] in [ "Syntax","Action","ActionID" ]:
                    continue
                ret[neli[0]]=neli[1]
            print(f'🦆 fo Help {command}=')
            print({'text':result,'syntax':ret})
            return({'text':result['Output'],'syntax':ret})

        async def keys(self):
            print('🦆 ke Help D')
            if not len(await self.cmdAll.keys()): # On force un reload
                self.cmdAll=self.pano.Cache(self._feedFull,timeout=60)
            print(self.cmdAll)
            print('🦆 ke Help E')
            return(await self.cmdAll.keys())
        


###
 


###


    class Endpoint:
        def __init__(self, name, pano):
            self.name = name
            self.pano = pano

        def __add__(self, other):
            print(f"Appel entre {self.name} et {other.name}")

    class Endpoints:
        def __init__(self, pano):
            self.pano = pano
            self._data = {
                'b': Pano.Endpoint('b', pano),
                'j': Pano.Endpoint('j', pano),
            }

        def __getitem__(self, key):
            return self._data[key]

        def keys(self):
            return self._data.keys()

    class Queue:
        def __init__(self, name, pano):
            self.name = name
            self.pano = pano

        def __add__(self, endpoint):
            print(f"Ajout de {endpoint.name} à la queue {self.name}")

    class Queues:
        def __init__(self, pano):
            self.pano = pano

        def __getitem__(self, key):
            return Pano.Queue(key, self.pano)

    class DBEntry:
        def __init__(self):
            self._data = {}

        def __getitem__(self, key):
            if key not in self._data:
                self._data[key] = Pano.DBEntry()
            return self._data[key]

        def __setitem__(self, key, value):
            self._data[key] = value

        def del_(self):
            print("Suppression DBEntry")

    class DB:
        def __init__(self, pano):
            self._data = {}

        def __getitem__(self, key):
            if key not in self._data:
                self._data[key] = Pano.DBEntry()
            return self._data[key]

        def __setitem__(self, key, value):
            self._data[key] = value

    class Channel:
        def __init__(self, name, pano):
            self.name = name
            self.pano = pano

        def del_(self):
            print(f"Suppression du canal {self.name}")

        def pause(self):
            print(f"Pause du canal {self.name}")

        def __add__(self, endpoint):
            print(f"Canal {self.name} appelle {endpoint.name}")

    class Channels:
        def __init__(self, pano):
            #self._data = {
            #    'g': Pano.Channel('g', pano),
            #    'h': Pano.Channel('h', pano),
            #    'i': Pano.Channel('i', pano),
            #    }
            self.hero = {'Action':"Status","AllVariables":"True"}
            self.pano = pano
            self.cache= {}
            self.timeput=int(time())
            self.timemax=5

        async def __getitem__(self, key):
            if not key in await self.keys():
                return(None)
            else:
                return(self.cache[key])

        async def keys(self):
            if len(self.cache) == 0 or int(time())-self.timeput > self.timemax:
                print(f'👻 fulling cache with {self.hero}')
                datas=await self.pano.action(self.hero)
                self.cache={}
                for chan in datas:
                    if "Channel" in chan.keys():
                        self.cache[chan['Channel']]=chan
                print(self.cache.keys())
                print(f'👻 fulling cache done')
                if len(self.cache):
                    self.timeput=int(time())
            else:
                print('👻 used')
            return(self.cache.keys())

        async def __repr__(self):
            print('🤩 repr')
            if not key in await self.keys():
                return({})
            return(self.cache)
                

    ####### COEUR
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

    def fromcache(self,clef,defaultValue=None,maxtime=None):
        if clef not in self.cache.keys():
            return(defaultValue)
        if maxtime is None:
            maxtime= self.cache[clef]['timemax']
        if int(time())-self.cache[clef]['timeput'] < maxtime:
            print(f'Read {clef} from cache')
            return(self.cache[clef]['data'])
        else:
            return(defaultValue)
    
    def tocache(self,clef,data,maxtime=2):
        self.cache[clef]={}
        self.cache[clef]['data']=data
        self.cache[clef]['timeput']=int(time())
        self.cache[clef]['timemax']=maxtime

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

    async def statusi(self):
        hero = {'Action':"Status","AllVariables":"True"}
        ret= self.fromcache('status',None)
        if ret is None:
            ret=self.trichan(await self.action(hero))
            self.tocache('status',ret,1)
        return(ret)

    async def status(self):
        return({ 'iii': await self.channels})

    def trichan(self,allChan):
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






