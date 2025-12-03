
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
import httpx
from jose import jwt, JWTError

import csv
import bcrypt


class Zapiz:
    def __init__(self, host: str="127.0.0.1", port: int=8080,
            startup: Callable=None,
            oidc_client_id=None, oidc_client_secret=None, oidc_issuer=None, oidc_auth_url=None, oidc_toke_url=None,oidc_redi_url=None,oidc_jwks_url=None,oidc_usin_url=None,
            user_csvfile=None,
            secret_key="your-secret-key",
            title=None, description=None, version= None, docs_url=None, redoc_url=None, openapi_url=None,
            template_dir="templates",static_dir="static",token_url="token",root=os.path.abspath(os.getcwd())+"/",
            sentry=None):
        self.host = host
        self.port = port
        self.app = FastAPI(title=title,description=description,version=version,docs_url=docs_url,redoc_url=redoc_url,openapi_url=openapi_url)
        self.templates={}
        self.templates['base']=Jinja2Templates(directory=template_dir)
        self.app.mount("/"+static_dir, StaticFiles(directory=root+static_dir), name="static")
        self.web_routes: Dict[str, str] = {}
        self.api_routes= { 'GET':{},'POST':{}}
        self.tokens = {}  # token: {owner, legend, expires}
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_url)
        #self.app.add_middleware(SessionMiddleware, secret_key=secret_key)
        self.algo ="HS256"
        self.secret_key=secret_key
        self.token_access_timeout_min=2
        self.token_refresh_timeout_days=7
        self.user_csvfile=user_csvfile
        self.oidc_client_id=oidc_client_id
        self.oidc_client_secret=oidc_client_secret
        self.oidc_auth_url=oidc_auth_url
        self.oidc_toke_url=oidc_toke_url
        self.oidc_redi_url=oidc_redi_url
        self.oidc_jwks_url=oidc_jwks_url
        self.oidc_usin_url=oidc_usin_url
        self.oidc_issuer=oidc_issuer
        self.sentry=sentry

        self.setup_auth_routes()
        #if oidc_client_id:
        #    self.auth = OAuth()
        #    self.auth.register(
        #        name="authentik",
        #        client_id=oidc_client_id,
        #        client_secret=oidc_client_secret,
        #        server_metadata_url=oidc_issuer,
        #        client_kwargs={'scope':oidc_scopes}
        #        )
        #    self.setup_auth_routes()
        #    self.oidc_root=oidc_root
        #else:
        #    self.auth=None
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
        def create_token(data: dict, expires_delta: timedelta, token_type: str):
            to_encode = data.copy()
            expire = datetime.utcnow() + expires_delta
            to_encode.update({"exp": expire, "type": token_type})
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algo)
        
        def verify_token(token: str, token_type: str):
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algo])
            if payload.get("type") != token_type:
                raise JWTError("Invalid token type")
            return payload
        
        @self.app.get("/login", response_class=HTMLResponse)
        async def login_page(request: Request):
            templateid="base"
            nextstep={}
            nextstep['request']=request
            nextstep['authentik_url']=self.oidc_auth_url
            nextstep['oidc_client_id']=self.oidc_client_id
            nextstep['oidc_redirect_uri']=self.oidc_redi_url

            return self.templates[templateid].TemplateResponse("login.html",nextstep)
            #return templates.TemplateResponse("login.html", {"request": request, "authentik_url": self.oidc_auth_url})
        
        @self.app.post("/token")
        #async def local_login(username: str = Form(...), password: str = Form(...)):
        async def local_login(request: Request):
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        
            # Lire l'utilisateur depuis le CSV
            user_data = get_user_from_csv(self.user_csvfile, username)
            if not user_data:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        
            # Vérifier le mot de passe en clair contre le hash
            if not bcrypt.checkpw(password.encode("utf-8"), user_data["hashed_pw"].encode("utf-8")):
                raise HTTPException(status_code=401, detail="Invalid credentials")
        
            # Créer les tokens internes
            access_token = create_token(
                {
                    "sub": user_data["username"],
                    "auth_method": "local",
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "groups": user_data["groups"],
                },
                timedelta(minutes=self.token_access_timeout_min),
                "access",
            )
            refresh_token = create_token(
                {
                    "sub": user_data["username"],
                    "auth_method": "local",
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "groups": user_data["groups"],
                },
                timedelta(days=self.token_refresh_timeout_days),
                "refresh",
            )
        
            # Réponse avec cookies
            response = RedirectResponse(url="/secret", status_code=303)
            response.set_cookie("access_token", access_token, httponly=True)
            response.set_cookie("refresh_token", refresh_token, httponly=True)
            return response


        # Fonction utilitaire pour lire le CSV et retourner les infos utilisateur
        def get_user_from_csv(csvfile, username):
            # python3 -c "import bcrypt; print(bcrypt.hashpw(b'monmotdepasse', bcrypt.gensalt()).decode())"
            with open(csvfile, newline="", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=":")
                for row in reader:
                    if len(row) < 5:
                        continue
                    user, hashed_pw, name, email, groups = row
                    if user == username:
                        return {
                            "username": user,
                            "hashed_pw": hashed_pw,
                            "name": name,
                            "email": email,
                            "groups": groups.split(","),
                        }
            return None
        






        async def local_login2(request: Request):
            USERS = {"alice": "password123", "bob": "secret"}
            form=await request.form()
            username=form.get('username')
            password=form.get('password')
            if USERS.get(username) != password:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            access_token = create_token({"sub": username, "auth_method": "local"}, timedelta(minutes=self.token_access_timeout_min), "access")
            refresh_token = create_token({"sub": username, "auth_method": "local"}, timedelta(days=self.token_refresh_timeout_days), "refresh")
            response = RedirectResponse(url="/secret", status_code=303)
            response.set_cookie("access_token", access_token, httponly=True)
            response.set_cookie("refresh_token", refresh_token, httponly=True)
            return response

        def decode_payload(token: str):
            import base64
            import json

            # Découper le token en 3 parties
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Token invalide")
            
            # Décoder la partie payload (2ème partie)
            payload_b64 = parts[1] + "=="  # ajouter padding si nécessaire
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes)
            return payload
        
        @self.app.get("/login/callback")
        async def oidc_callback(request: Request, code: str):
            # Échange du code contre un token Authentik
            data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.oidc_redi_url,
                    "client_id": self.oidc_client_id,
                    "client_secret": self.oidc_client_secret,
                }
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.oidc_toke_url, data=data)
            print(f'🔫 {self.oidc_toke_url}')
            print('data')
            print(data)
            print('resp')
            print(resp)
            tokens = resp.json()
            id_token = tokens.get("id_token")
            access_token_oidc = tokens.get("access_token")

            print(tokens)
            print(self.oidc_issuer)
            print(decode_payload(tokens.get('access_token')))
            print(decode_payload(tokens.get('id_token')))
            print(f'🔫 {self.oidc_toke_url}')

            if not id_token:
                return RedirectResponse(url="/login", status_code=303)

            # Récupérer les clés publiques JWKS
            async with httpx.AsyncClient() as client:
                jwks_resp = await client.get(self.oidc_jwks_url)
            jwks = jwks_resp.json()
        
            # Décoder l'id_token (⚠️ en prod, vérifier signature avec clé publique Authentik)
            #payload = jwt.decode(id_token, options={"verify_signature": False})
            try:
                payload = jwt.decode(
                    id_token,
                    jwks,
                    algorithms=["RS256"],  # ou l’algo utilisé par Authentik
                    audience=self.oidc_client_id,
                    issuer=self.oidc_issuer
                    )
            except JWTError:
                return RedirectResponse(url="/login", status_code=303)

            print('payload')
            print(payload)
            user = payload.get("sub")
            name = payload.get("name")
            email = payload.get("email")
            groups = payload.get("groups")

            if not (name and email and groups):
                print('🚒')
                async with httpx.AsyncClient() as client:
                    userinfo_resp = await client.get(
                        self.oidc_usin_url,
                        headers={"Authorization": f"Bearer {access_token_oidc}"}
                        )
                userinfo = userinfo_resp.json()
                name = name or userinfo.get("name")
                email = email or userinfo.get("email")
                groups = groups or userinfo.get("groups")
                print('userinfo')
                print(userinfo)

            internal_claims = {
                "sub": user,
                "auth_method": "oidc",
                "name": name,
                "email": email,
                "groups": groups,
                }
        
            # Générer tokens internes
            access_token = create_token(internal_claims, timedelta(minutes=self.token_access_timeout_min), "access")
            refresh_token = create_token(internal_claims, timedelta(days=self.token_refresh_timeout_days), "refresh")
            response = RedirectResponse(url="/secret", status_code=303)
            response.set_cookie("access_token", access_token, httponly=True)
            response.set_cookie("refresh_token", refresh_token, httponly=True)
            return response

        @self.app.get("/refresh")
        async def refresh(request: Request, next=None):
            # 1. Récupérer le refresh token depuis le cookie
            refresh_token = request.cookies.get("refresh_token")
            if not refresh_token:
                return JSONResponse({"error": "No refresh token"}, status_code=401)
        
            # 2. Décoder le refresh token interne
            try:
                payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algo])
            except JWTError:
                return JSONResponse({"error": "Invalid refresh token"}, status_code=401)
            print('💋')
            print(payload)
        
            # 3. Vérifier qu’il s’agit bien d’un refresh token
            if payload.get("type") != "refresh":
                return JSONResponse({"error": "Wrong token type"}, status_code=401)
        
            # 4. Reprendre les claims stockés (sub, name, email, groups…)
            internal_claims = {
                "sub": payload.get("sub"),
                "auth_method": payload.get("auth_method"),
                "name": payload.get("name"),
                "email": payload.get("email"),
                "groups": payload.get("groups"), }
        
            # 5. Générer un nouveau access token
            new_access_token = create_token(internal_claims, timedelta(minutes=self.token_access_timeout_min), "access")
        
            # 6. (Optionnel) régénérer un nouveau refresh token si tu veux prolonger la durée
            new_refresh_token = create_token(internal_claims, timedelta(days=self.token_refresh_timeout_days), "refresh")

        
            # 7. Poser les cookies et renvoyer
            print('💋💋')
            #response = JSONResponse({"status": "ok"})
            if next:
                referer=next
            response = RedirectResponse(url=referer, status_code=303)
            response.set_cookie("access_token", new_access_token, httponly=True)
            response.set_cookie("refresh_token", new_refresh_token, httponly=True)
            referer = request.headers.get("referer", "/")
            return response


        @self.app.get("/secret")
        async def secret(request: Request):
            # 1. Récupérer le token d'accès depuis le cookie
            access_token = request.cookies.get("access_token")
            print('🤑')
            print(access_token)
            if not access_token:
                # Pas de token → redirection vers /refresh avec next
                print('💀 Token perdu')
                current_url = str(request.url)
                return RedirectResponse(url=f"/refresh?next={current_url}", status_code=303)
        
            # 2. Vérifier le token
            try:
                payload = jwt.decode(access_token, self.secret_key, algorithms=[self.algo])
                print('💀 Token alive')
                print(payload)
            except JWTError:
                # Token invalide ou expiré → redirection vers /refresh avec next
                print('💀 Token expiré')
                current_url = str(request.url)
                return RedirectResponse(url=f"/refresh?next={current_url}", status_code=303)
        
            # 3. Extraire les infos de l'utilisateur depuis le token interne
            user = {
                "sub": payload.get("sub"),
                "name": payload.get("name"),
                "email": payload.get("email"),
                "groups": payload.get("groups"),
            }
            templateid="base"
            nextstep={}
            nextstep['request']=request
            #payload = verify_token(token, "access")
            nextstep['user'] = payload.get("sub")
            nextstep['method'] = payload.get("auth_method")
            nextstep['email'] = payload.get("email")
            nextstep['name'] = payload.get("name")
            nextstep['groups'] = payload.get("groups",[])
            nextstep['claims']=payload
            user = payload.get("sub")
            method = payload.get("auth_method")
            return self.templates[templateid].TemplateResponse("secret.html",nextstep)
        
            # 4. Retourner la page secrète avec les infos
            return JSONResponse({
                "message": "Bienvenue sur la page secrète 🎉",
                "user": user
            })

        #@self.app.get("/secret", response_class=HTMLResponse)
        async def secret_page1(request: Request):
            token = request.cookies.get("access_token")
            if not token:
                return RedirectResponse(url="/login", status_code=303)
            try:
                templateid="base"
                nextstep={}
                nextstep['request']=request
                payload = verify_token(token, "access")
                nextstep['user'] = payload.get("sub")
                nextstep['method'] = payload.get("auth_method")
                nextstep['email'] = payload.get("email")
                nextstep['name'] = payload.get("name")
                nextstep['groups'] = payload.get("groups",[])
                nextstep['claims']=payload
                user = payload.get("sub")
                method = payload.get("auth_method")
                return self.templates[templateid].TemplateResponse("secret.html",nextstep)
               # return templates.TemplateResponse("secret.html", {"request": request, "user": user, "method": method})
            except JWTError:
                # Récupérer l'URL courante
                current_url = str(request.url)
                # Rediriger vers /refresh avec ?next=<url courante>
                return RedirectResponse(url=f"/refresh?next={current_url}", status_code=303)

        
        @self.app.get("/logout")
        async def logout(request: Request):
            response = RedirectResponse(url="/login", status_code=303)
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response

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

            #varSession = request.session.get("user")
            varSession=None
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
                        return HTMLResponse(content= f"<html><head><meta http-equiv='refresh' content='5;URL=/'></head><body><h1>403 - Accés limité <a href='/'>HomePage</a></h1></body></html>", status_code=403)
                    else:
                        return JSONResponse( status_code=403, content={"detail": "Ressource limite"})

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
                if self.sentry:
                    print(f'🚒 {self.sentry}')
                    nextstep['sentry']=self.sentry
                    print(nextstep)
                templateid='base'
                if 'templateid' in result.keys():
                    templateid=result['templateid']
                if  self.api_routes[verb][uri]['html']:
                    return self.templates[templateid].TemplateResponse(result['template'],nextstep)
                    #return HTMLResponse(self.templates[templateid].TemplateResponse(result['template'],nextstep))
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


