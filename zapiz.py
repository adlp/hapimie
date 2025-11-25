
#from fastapi import FastAPI, Request, Depends, HTTPException
#from fastapi.responses import HTMLResponse
#from fastapi.templating import Jinja2Templates
#from fastapi.security import OAuth2PasswordBearer
#from fastapi.openapi.docs import get_swagger_ui_html
#from datetime import datetime, timedelta
#from typing import Callable, Dict
#import uvicorn
# pip install fastapi-simple-oidc
#from fastapi_simple_oidc import OIDCAuth, OIDCUser
#from fastapi.responses import RedirectResponse

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse,JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.docs import get_swagger_ui_html
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from fastapi.staticfiles import StaticFiles
import uvicorn
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
import os
import inspect


class Zapiz:
    def __init__(self, host: str="127.0.0.1", port: int=8080,
            startup: Callable=None,
            oidc_client_id=None, oidc_client_secret=None, oidc_issuer=None, oidc_scopes="openid profile email groups", oidc_root=None,
            secret_key="your-secret-key",
            title=None, description=None, version= None, docs_url=None, redoc_url=None, openapi_url=None,
            template_dir="templates",static_dir="static",token_url="token",root=os.path.abspath(os.getcwd())+"/"):
        self.host = host
        self.port = port
        self.app = FastAPI(title=title,description=description,version=version,docs_url=docs_url,redoc_url=redoc_url,openapi_url=openapi_url)
        self.app.add_middleware(SessionMiddleware, secret_key=secret_key)
        self.templates={}
        self.templates['base']=Jinja2Templates(directory=template_dir)
        self.app.mount("/"+static_dir, StaticFiles(directory=root+static_dir), name="static")
        self.web_routes: Dict[str, str] = {}
        self.api_routes= { 'GET':{},'POST':{}}
        self.tokens = {}  # token: {owner, legend, expires}
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_url)

        if oidc_client_id:
            self.auth = OAuth()
            self.auth.register(
                name="authentik",
                client_id=oidc_client_id,
                client_secret=oidc_client_secret,
                server_metadata_url=oidc_issuer,
                client_kwargs={'scope':oidc_scopes}
                )
            self.setup_auth_routes()
            self.oidc_root=oidc_root
        else:
            self.auth=None
        ##self.app.include_router(self.auth.router,prefix="/auth")
        self._setup_docs()
        self._setup_token_routes()

        if startup:
            self.app.on_event("startup")(startup)

        if int(os.getenv('HAPIMIE_DEBUG',0))==1:
            @self.app.get("/debug")
            async def shutdown():
                # On prépare la redirection
                response = RedirectResponse(url="/")

                # On déclenche l’arrêt du serveur après avoir renvoyé la réponse
                # Ici on utilise un petit "truc" : on planifie l’arrêt dans un thread séparé
                import threading
                import signal
                def stop_server():
                    os.kill(os.getpid(), signal.SIGINT)  # arrêt propre
                threading.Timer(1.0, stop_server).start()

                return response

    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port)

    def add_template(self,template_dir,templateid=None):
        if not templateid:
            if '/' in template_dir:
                templateid=template_dir.split('/')[-1]
            else:
                templateid=template_dir
        self.templates[templateid]=Jinja2Templates(directory=template_dir)

    def add_static(self,static_dir,staticid=None):
        if not staticid:
            if '/' in static_dir:
                staticid=static_dir
            else:
                staticid=static_dir.split('/')[-1]
        self.app.mount("/"+staticid, StaticFiles(directory=root+static_dir), name=staticid)

    def setup_auth_routes(self):
        @self.app.get("/login")
        async def login(request: Request):
            redirect_uri = request.url_for('auth_callback')
            return await self.auth.authentik.authorize_redirect(request, redirect_uri)
        
        @self.app.get("/login/callback")
        async def auth_callback(request: Request):
            print("Dans le auth_call back !")
            token = await self.auth.authentik.authorize_access_token(request)
            #userinfo = await self.auth.authentik.parse_id_token(request, token)
            userinfo = await self.auth.authentik.userinfo(token=token)
            request.session['user'] = userinfo
#                user=userinfo
#                "email": userinfo.get("email"),
#                "name": userinfo.get("name"),
#                "groups": userinfo.get("groups", [])
#            }
            print(f"✅ Connexion réussie : {userinfo.get('email')} - groupes : {userinfo.get('groups')}")
            return RedirectResponse(url="/")

        @self.app.get("/logout")
        async def logout(request: Request):
            request.session.clear()
            #return RedirectResponse(url="/",status_code=202)
            if self.oidc_root:
                print("🔫 oidc root given")
                return RedirectResponse(url=self.oidc_root)
            print("🔫 oidc root not given")
            return RedirectResponse(url="/")
        
        @self.app.get("/whoami")
        async def whoami(request: Request):
            user = request.session.get("user")
            if not user:
                raise HTTPException(status_code=401, detail="Non authentifié")
            return user

    def _setup_docs(self):
        @self.app.get("/docs", include_in_schema=False)
        async def custom_docs():
            return get_swagger_ui_html(openapi_url=self.app.openapi_url, title="Zapiz API Docs")

    def _setup_token_routes(self):
        @self.app.post("/token")
        async def create_token(request: Request):
            form = await request.form()
            user = form.get("username")
            legend = form.get("legend", "")
            duration = int(form.get("duration", 3600))
            token = f"tok_{user}_{datetime.utcnow().timestamp()}"
            self.tokens[token] = {
                "owner": user,
                "legend": legend,
                "expires": datetime.utcnow() + timedelta(seconds=duration),
                "last_active": datetime.utcnow()
            }
            return {"access_token": token, "token_type": "bearer"}

        @self.app.get("/tokens")
        async def list_tokens():
            return self.tokens

        @self.app.post("/tokens/deactivate")
        async def deactivate_token(token: str):
            if token in self.tokens:
                del self.tokens[token]
                return {"status": "deleted"}
            raise HTTPException(status_code=404, detail="Token not found")

    def _verify_token(self, token: str):
        data = self.tokens.get(token)
        if not data:
            raise HTTPException(status_code=401, detail="Invalid token")
        now = datetime.utcnow()
        if now - data["last_active"] > timedelta(minutes=20):
            del self.tokens[token]
            raise HTTPException(status_code=401, detail="Session expired")
        if now > data["expires"]:
            del self.tokens[token]
            raise HTTPException(status_code=401, detail="Token expired")
        data["last_active"] = now
        return data["owner"]

    def webs(self, uri: str, template_path: str):
        self.web_routes[uri] = template_path

        @self.app.get(uri, response_class=HTMLResponse)
        async def render_page(request: Request, token: str = Depends(self.oauth2_scheme)):
            print('Render_page')
            user = self._verify_token(token)
            return self.templates.TemplateResponse(template_path, {"request": request, "user": user})

    def api_add(self, uri: str, func: Callable,html:bool=True,verb:str="GET",acl=None):
        """ 
        Format des routes
        uri func html verb  await (et on rajoutede suite s'il faut un await)
        Le add remplacera comme un sauvage le comportement de mv :)
        """
        fncAsync=inspect.iscoroutinefunction(func)

        uris=[uri]
        if uri[-1] != "/":
            uris.append(uri+"/")

        for u in uris:
            if not(self.api_routes[verb].get(u,None)):    # Si pas encore declarer alors creer la route
                if verb=="GET":
                    self.app.get(u)(self._secure_api_tab(verb,u))
                elif verb=="POST":
                    #self.app.post(u, response_class=response_class)(self._secure_api_tab()verb,u)
                    self.app.post(u)(self._secure_api_tab(verb,u))
            self.api_routes[verb][u]={}
            self.api_routes[verb][u]['func']=func
            self.api_routes[verb][u]['html']=html
            self.api_routes[verb][u]['await']=fncAsync
            self.api_routes[verb][u]['acl']=acl

    def api_del(self, uri: str, verb:str="GET"):
        """ 
        On ne supprime jamais un URI, on la fait pointer sur une 404 (merci fastapi...)
        Bon en fait, suffit que ce soit le comportement par defaut de _secure_api
        Par contre... je m'interroge sur le comportement de swag'n co
        """
        if uri in self.api_routes[verb]:
            self.api_routes[verb][uri]['func']=None

    def api_lst(self):
        """ 
        Format des routes
        uri func html verb  await (et on rajoutede suite s'il faut un await)
        """
        ret={}
        for verb in self.api_routes.keys():
            ret[verb]=[]
            for uri in self.api_routes[verb].keys():
                if self.api_routes[verb][uri]:
                    ret[verb].append(uri)
        return(ret)
        
    def _secure_api_tab(self, verb,uri):
        async def wrapper(request: Request):
            if not self.api_routes[verb].get(uri,None) or not self.api_routes[verb][uri]['func']:
                return JSONResponse( status_code=404, content={"detail": "Ressource introuvable"})
                #return HTMLResponse(content= "<h1>404 - Page non trouvée</h1>", status_code=404)

            varSession = request.session.get("user")
            if not varSession:
                varSession={}
            # 🔍 Détection de la méthode HTTP
            #verb = request.method
            #uri  = request.url.path
            print(f"✅ wrapper {verb} {uri} réussie : {varSession}")
            #print(f"💡 request : {request.path_params}")
            varSession['verb']=verb
            if verb=="POST":
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    varSession['form'] = await request.json()
                elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                    varSession['form'] = dict(await request.form())
                else:
                    varSession['form'] = {}

            if self.api_routes[verb][uri]['acl']:
                #Gestion des droits....
                if not('groups' in varSession.keys() and self.api_routes[verb][uri]['acl'] in varSession['groups']):
                    if self.api_routes[verb][uri]['html']:
                        return HTMLResponse(content= f"<h1>403 - Page non trouvée {self.api_routes[verb][uri]['acl']}</h1>", status_code=404)
                    else:
                        return JSONResponse( status_code=403, content={"detail": "Ressource introuvable"})

            ### On doit trouver la fonction, etc...
            # Appel dynamique a la fonction cible, avec tout les parametres
            #if inspect.iscoroutinefunction(func):
            if self.api_routes[verb][uri]['await']:
                result=await self.api_routes[verb][uri]['func'](varSession=varSession,params=request.path_params)
            else:
                result=      self.api_routes[verb][uri]['func'](varSession=varSession,params=request.path_params)

            if not isinstance(result,dict):
                1
            elif 'template' in result.keys():
                nextstep=result
                nextstep['request']=request
                if 'template_data' in result.keys():
                    for k in result['template_data'].keys():
                        nextstep[k]=result['template_data'][k]
                #nextstep['refresh_interval']=1000
                nextstep['name']=varSession.get("name",None)
                #print('👽️ resul ta da')
                #print(result.keys())
                templateid='base'
                if 'templateid' in result.keys():
                    templateid=result['templateid']
                if  self.api_routes[verb][uri]['html']:
                    return self.templates[templateid].TemplateResponse(result['template'],nextstep)
                    return HTMLResponse(self.templates[templateid].TemplateResponse(result['template'],nextstep))
                else:
                    return JSONResponse(self.templates[templateid].TemplateResponse(result['template'],nextstep))
            elif 'redirect' in result.keys():
                #return await self.auth.authentik.authorize_redirect(request, result['redirect'])
                return RedirectResponse(url=result['redirect'],status_code=303)
            else:
                #print('👽️ result')
                #print(result)
                return(result)
        return wrapper

    def _secure_api(self, func: Callable):
        #async def wrapper(request: Request,nom:str=None,token: str = Depends(self.oauth2_scheme)):
        async def wrapper(request: Request):
            varSession = request.session.get("user")
            if not varSession:
                varSession={}
            # 🔍 Détection de la méthode HTTP
            verb = request.method
            uri  = request.url.path
            print(f"✅ wrapper {verb} {uri} réussie : {varSession}")
            #print(f"💡 request : {request.path_params}")
            varSession['verb']=verb
            if verb=="POST":
                varSession['form']=dict(await request.form())

            # Appel dynamique a la fonction cible, avec tout les parametres
            if inspect.iscoroutinefunction(func):
                result=await func(varSession=varSession,params=request.path_params)
            else:
                result=func(varSession=varSession,params=request.path_params)
            if not isinstance(result,dict):
                1
            elif 'template' in result.keys():
                nextstep=result
                nextstep['request']=request
                if 'template_data' in result.keys():
                    for k in result['template_data'].keys():
                        nextstep[k]=result['template_data'][k]
                #nextstep['refresh_interval']=1000
                nextstep['name']=varSession.get("name",None)
                #print('👽️ resul ta da')
                #print(result.keys())
                templateid='base'
                if 'templateid' in result.keys():
                    templateid=result['templateid']
                return self.templates[templateid].TemplateResponse(result['template'],nextstep)
            elif 'redirect' in result.keys():
                return await self.auth.authentik.authorize_redirect(request, result['redirect'])
            else:
                #print('👽️ result')
                #print(result)
                return(result)
        return wrapper

    def declare_path(app, method: str, path: str, *, summary: str = None, include_in_schema: bool = True):
        """
        Permet de preformarter pour swag, car, ca swag
        """
        def decorator(func):
            doc = func.__doc__ or "Pas de description disponible."
            lines = doc.strip().split("\n")
    
            # Si summary est vide, on prend la première ligne de la docstring
            effective_summary = summary or (lines[0].strip() if lines else "Pas de résumé")
            # Le reste de la docstring devient la description
            description = "\n".join(lines[1:]).strip() if len(lines) > 1 else None
    
            route = getattr(app, method)
            route(
                path,
                description=doc,
                summary=effective_summary,
                include_in_schema=include_in_schema,
                )(func)
            return func
        return decorator


