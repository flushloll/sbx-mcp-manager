#!/usr/bin/env python3
"""Local browser UI for Docker Sandbox MCP management. Standard library only."""
import http.server
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import urllib.parse
import webbrowser
from http.cookies import SimpleCookie

TOKEN = secrets.token_urlsafe(32)
NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
CATALOG = [
    dict(name="blender", title="Blender", kind="local", command="uvx", args=["mcp-for-blender"], detail="Requires Blender with the MCP add-on running on macOS."),
    dict(name="shadcn", title="shadcn/ui", kind="local", command="npx", args=["-y", "shadcn@latest", "mcp"], detail="Component registry and documentation."),
    dict(name="context7", title="Context7", kind="remote", url="https://mcp.context7.com/mcp", detail="Library documentation."),
    dict(name="notion", title="Notion", kind="remote", url="https://mcp.notion.com/mcp", detail="Workspace integration; sign-in may be required."),
    dict(name="linear", title="Linear", kind="remote", url="https://mcp.linear.app/mcp", detail="Issue tracking; sign-in may be required."),
]

def run_sbx(args, timeout=30):
    executable = shutil.which("sbx")
    if not executable:
        raise RuntimeError("Docker sbx CLI not found. Install Docker Desktop and check PATH.")
    env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + os.path.expanduser("~/.local/bin")}
    try:
        result = subprocess.run([executable] + args, capture_output=True, text=True,
                                check=False, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Operation timed out; complete any interactive authorization in Terminal.") from exc
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "sbx failed").strip()[:1500])
    return (result.stdout or result.stderr).strip()

def names(output):
    return [line.strip() for line in output.splitlines() if NAME.fullmatch(line.strip())]

def validate_name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError("Invalid server or sandbox name.")
    return value

def registration_args(entry):
    if not isinstance(entry, dict):
        raise ValueError("Invalid registration.")
    name = validate_name(entry.get("name"))
    if entry.get("kind") == "remote":
        url = entry.get("url", "")
        if not isinstance(url, str):
            raise ValueError("Invalid URL.")
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Remote MCP must have an HTTPS URL without embedded credentials.")
        return ["mcp", "add", name, "--url", url]
    if entry.get("kind") == "local":
        command = entry.get("command")
        args = entry.get("args", [])
        if not isinstance(command, str) or not re.fullmatch(r"[\w./+-]{1,180}", command):
            raise ValueError("Invalid executable.")
        if not isinstance(args, list) or len(args) > 24 or any(
            not isinstance(a, str) or not a or len(a) > 299 or "," in a for a in args
        ):
            raise ValueError("Arguments must be nonempty, shorter than 300 characters, and contain no commas.")
        return ["mcp", "add", name, "--command", command] + (["--args", ",".join(args)] if args else [])
    raise ValueError("Select a remote or local MCP server.")

def state():
    response = {"catalog": CATALOG, "sandboxes": [], "registered": [], "warnings": []}
    try:
        response["sandboxes"] = names(run_sbx(["ls", "-q"]))
    except RuntimeError as exc:
        response["warnings"].append(str(exc))
    try:
        response["registered"] = names(run_sbx(["mcp", "ls", "-q"]))
    except RuntimeError as exc:
        response["warnings"].append(str(exc))
    return response

def execute(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    action = payload.get("action")
    if action == "register":
        return run_sbx(registration_args(payload.get("entry")), timeout=40)
    if action not in ("load", "unload"):
        raise ValueError("Unsupported action.")
    servers, sandboxes = payload.get("servers"), payload.get("sandboxes")
    if not isinstance(servers, list) or not isinstance(sandboxes, list) or not servers or not sandboxes or len(servers) > 40 or len(sandboxes) > 40:
        raise ValueError("Select servers and sandboxes.")
    servers = list(dict.fromkeys(validate_name(s) for s in servers))
    sandboxes = list(dict.fromkeys(validate_name(s) for s in sandboxes))
    known_servers = set(names(run_sbx(["mcp", "ls", "-q"])))
    known_sandboxes = set(names(run_sbx(["ls", "-q"])))
    if not set(servers) <= known_servers or not set(sandboxes) <= known_sandboxes:
        raise ValueError("Selection is no longer registered. Refresh and try again.")
    result = []
    for sandbox in sandboxes:
        for server in servers:
            try:
                output = run_sbx(["mcp", action, server, "--sandbox", sandbox], timeout=40)
                result.append({"server": server, "sandbox": sandbox, "success": True, "message": output})
            except RuntimeError as exc:
                result.append({"server": server, "sandbox": sandbox, "success": False, "message": str(exc)})
    return result

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SBX MCP Manager</title>
<style>
:root{color-scheme:dark;font:15px/1.5 system-ui,sans-serif;background:#0c111b;color:#ebf1fa}
*{box-sizing:border-box}body{margin:0}main{max-width:1160px;padding:36px 20px;margin:auto}
h1{font-size:30px;margin:0}h2{font-size:17px;margin:0 0 12px}p{color:#b8c6d7}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{background:#171f2d;padding:22px;border:1px solid #344156;border-radius:16px;margin:0 0 16px}
.item{display:flex;align-items:flex-start;gap:12px;border:1px solid #354257;border-radius:10px;padding:12px;margin:8px 0;cursor:pointer}
.item:hover{border-color:#77adf2}.item small{display:block;color:#b3c1d2}.item input{margin:5px 0}button{cursor:pointer;background:#366bb0;color:#fff;border:1px solid #5686c6;border-radius:9px;padding:10px 14px}
button.secondary{background:#253448}button.danger{background:#744054}
input[type=text],select,textarea{display:block;width:100%;padding:10px;margin:5px 0 12px;background:#101927;border:1px solid #41536d;border-radius:8px;color:inherit}
label.field{display:block;margin:9px 0}textarea{min-height:85px}button+button{margin-left:6px}
#log{white-space:pre-wrap;overflow-wrap:anywhere;background:#0a1527;border-radius:10px;padding:12px;max-height:320px;overflow:auto}
.warning{color:#ffcc8c}header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:24px}
@media(max-width:800px){.grid{grid-template-columns:1fr}header{align-items:start;flex-direction:column}}
</style></head><body><main>
<header><div><h1>SBX MCP Manager</h1><p>Manage MCP servers across your Docker Sandboxes.</p></div><button id="refresh" class="secondary">Refresh</button></header>
<div class="grid"><section>
<div class="panel"><h2>MCP catalog</h2><p>Select preset servers, then register them on your Mac.</p><div id="catalog"></div><button id="register">Register selected</button></div>
<div class="panel"><h2>Custom MCP server</h2>
<label class="field">Name<input type="text" id="name" placeholder="my-server"></label>
<label class="field">Type<select id="kind"><option value="remote">Remote HTTPS</option><option value="local">Local stdio executable</option></select></label>
<div id="remote"><label class="field">URL<input id="url" type="text" placeholder="https://example.com/mcp"></label></div>
<div id="local" hidden><label class="field">Executable<input id="command" type="text" placeholder="npx"></label><label class="field">Arguments (one per line)<textarea id="args" placeholder="-y&#10;my-mcp-package"></textarea></label></div>
<button id="custom">Register custom MCP</button>
<p>Local MCP executables run on your Mac, with host permissions.</p></div>
</section><section>
<div class="panel"><h2>Sandboxes</h2><p>Select destinations for your MCP servers.</p><div id="sandboxes"></div></div>
<div class="panel"><h2>Registered MCP servers</h2><div id="registered"></div><button id="load">Attach</button><button id="unload" class="danger">Detach</button></div>
<div class="panel"><h2>Output</h2><div id="log" role="status">Ready.</div></div>
</section></div>
<p>Local-only utility. Docker Desktop's MCP Toolkit is a separate registry from <code>sbx mcp</code>.</p>
<script>
const $=id=>document.getElementById(id);
let current={catalog:[],sandboxes:[],registered:[]};
function log(x){$('log').textContent=typeof x==='string'?x:JSON.stringify(x,null,2)}
function selected(cls){return [...document.querySelectorAll('.'+cls+':checked')].map(e=>e.value)}
function check(parent,group,value,title,detail){
 const label=document.createElement('label');label.className='item';
 const input=document.createElement('input');input.type='checkbox';input.className=group;input.value=value;
 const body=document.createElement('span');const b=document.createElement('strong');b.textContent=title;
 const sub=document.createElement('small');sub.textContent=detail||'';body.append(b,sub);label.append(input,body);parent.append(label);
}
async function api(path,body){
 const options={headers:{'X-SBX-Token':window.SBX_TOKEN}};
 if(body){options.method='POST';options.headers['Content-Type']='application/json';options.body=JSON.stringify(body)}
 const response=await fetch(path,options),data=await response.json();
 if(!response.ok)throw Error(data.error||'Request failed');return data;
}
async function refresh(){
 try{
  current=await api('/api/state');
  for(const id of ['catalog','sandboxes','registered'])$(id).replaceChildren();
  for(const e of current.catalog)check($('catalog'),'catalogCheck',e.name,e.title,e.detail);
  for(const s of current.sandboxes)check($('sandboxes'),'sandboxCheck',s,s,'');
  for(const s of current.registered)check($('registered'),'serverCheck',s,s,'');
  if(current.warnings.length)log(current.warnings.join('\n'));
 }catch(e){log(e.message)}
}
async function register(entries){
 for(const e of entries){
  if(e.kind==='local'&&!confirm('This MCP may execute code on your Mac with your user permissions. Trust this server?'))continue;
  try{log('Registering '+e.name+'...');const result=await api('/api/action',{action:'register',entry:e});log(result)}
  catch(error){log(e.name+': '+error.message)}
 }
 await refresh();
}
$('register').onclick=()=>register(current.catalog.filter(e=>selected('catalogCheck').includes(e.name)));
$('refresh').onclick=refresh;
$('kind').onchange=()=>{$('local').hidden=$('kind').value!=='local';$('remote').hidden=$('kind').value!=='remote'};
$('custom').onclick=()=>{
 const entry={name:$('name').value.trim(),kind:$('kind').value};
 if(entry.kind==='remote')entry.url=$('url').value.trim();
 else{entry.command=$('command').value.trim();entry.args=$('args').value.split('\n').map(s=>s.trim()).filter(Boolean)}
 register([entry]);
};
async function change(action){
 const servers=selected('serverCheck'),sandboxes=selected('sandboxCheck');
 if(!servers.length||!sandboxes.length){log('Select at least one registered MCP and one sandbox.');return}
 if(action==='unload'&&!confirm('Detach selected MCPs from selected sandboxes?'))return;
 try{log('Updating...');const result=await api('/api/action',{action,servers,sandboxes});log(result.result)}
 catch(e){log(e.message)}
}
$('load').onclick=()=>change('load');$('unload').onclick=()=>change('unload');
refresh();
</script></main></body></html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def host_ok(self):
        host = self.headers.get("Host", "")
        return host in ("localhost:" + str(self.server.server_port),
                        "127.0.0.1:" + str(self.server.server_port))

    def authorized(self):
        try:
            cookies = SimpleCookie()
            cookies.load(self.headers.get("Cookie", ""))
            token = cookies.get("sbx_token")
            return bool(token and secrets.compare_digest(token.value, TOKEN))
        except Exception:
            return False

    def send(self, code, data, mime="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, b'{"error":"Invalid Host"}')
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/unlock":
            token = urllib.parse.parse_qs(url.query).get("token", [""])[0]
            if not secrets.compare_digest(token, TOKEN):
                return self.send(403, b'{"error":"Invalid launch token"}')
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "sbx_token=" + TOKEN + "; Path=/; HttpOnly; SameSite=Strict")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            return
        if not self.authorized():
            return self.send(403, b'{"error":"Open the application using its launcher"}')
        if url.path == "/":
            html = HTML.replace("<script>", "<script>window.SBX_TOKEN=" + json.dumps(TOKEN) + ";</script><script>", 1)
            return self.send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        if url.path == "/api/state":
            return self.send(200, json.dumps(state()).encode("utf-8"))
        return self.send(404, b'{"error":"Not found"}')

    def do_POST(self):
        port = str(self.server.server_port)
        allowed = ("http://localhost:" + port, "http://127.0.0.1:" + port)
        origin = self.headers.get("Origin", "")
        if (self.path != "/api/action" or not self.host_ok() or not self.authorized()
                or origin not in ("",) + allowed
                or not secrets.compare_digest(self.headers.get("X-SBX-Token", ""), TOKEN)):
            return self.send(403, b'{"error":"Forbidden"}')
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 12000:
                raise ValueError("Invalid request length.")
            payload = json.loads(self.rfile.read(length))
            response = execute(payload)
            self.send(200, json.dumps({"result": response}).encode("utf-8"))
        except (ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            self.send(400, json.dumps({"error": str(exc)}).encode("utf-8"))
        except Exception:
            self.send(500, b'{"error":"Unexpected server error"}')

def main():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    address = "http://127.0.0.1:" + str(port) + "/unlock?token=" + urllib.parse.quote(TOKEN)
    print("SBX MCP Manager listening at http://127.0.0.1:" + str(port), flush=True)
    threading.Timer(0.6, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
