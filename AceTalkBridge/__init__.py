"""
AceTalkBridge — ComfyUI custom node
Receives a filled workflow from AceTalk and broadcasts it to all connected
browser clients via WebSocket so the canvas updates automatically.
"""

from server import PromptServer
from aiohttp import web

@PromptServer.instance.routes.post("/acetalk/load")
async def acetalk_load(request):
    """
    AceTalk POSTs the filled workflow here after queuing.
    We broadcast it to all connected browser tabs so they load it.
    """
    try:
        workflow = await request.json()
        # sid=None broadcasts to all connected WebSocket clients
        await PromptServer.instance.send_json(
            "acetalk_load_workflow", {"workflow": workflow}, sid=None
        )
        return web.Response(status=200, text="OK")
    except Exception as exc:
        return web.Response(status=500, text=str(exc))


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"
