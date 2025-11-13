
from panoramisk.manager import Manager
import asyncio
from time import time #, sleep
import inspect



class Pano:
    def __init__(self, host="127.0.0.1", port=5038, login="login", password="password"):
        # Help variables
        self.helpAll=self.Cache(self._help_feedFull,timeout=60)
        self.helpDetail={}
        # Channels variables
        self.channelCache=self.Cache(self._chan_feed,timeout=1)

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
        if not len(await self.helpAll.keys()): # On force un reload
            self.helpAll=self.Cache(self._help_feedFull,timeout=60)

        if not key:
            print('🦆 gt Help None')
            return(await self.helpAll.dict())

        if key not in self.helpDetail.keys():
            self.helpDetail[key]=self.Cache(self._help_feedOne,funcarg=key,timeout=60)
        return(await self.helpDetail[key].dict())

    async def help_keys(self):
        print('🦆 ke Help D')
        if not len(await self.helpAll.keys()): # On force un reload
            self.helpAll=self.Cache(self._help_feedFull,timeout=60)
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







