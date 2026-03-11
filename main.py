import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from serial_manager import SerialManager
from state_manager import StateManager
from stream_engine import StreamEngine
from config_manager import ConfigManager
from gcode_logger import GcodeLogger, LOGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

cfg = ConfigManager()

serial_mgr = SerialManager(
    port=cfg.get("serial", "port", "/dev/ttyACM0"),
    baudrate=cfg.get("serial", "baud_rate", 115200),
    max_pending=4,
)
state_mgr = StateManager()
engine = StreamEngine(serial_mgr, state_mgr)
gcode_log = GcodeLogger()

clients: Set[WebSocket] = set()
broadcast_task = None


def apply_config():
    serial_mgr.port = cfg.get("serial", "port", "/dev/ttyACM0")
    serial_mgr.baudrate = cfg.get("serial", "baud_rate", 115200)
    engine.apply_config(cfg)


async def broadcast_status():
    while True:
        try:
            if clients:
                payload = json.dumps({"type": "status", **state_mgr.snapshot()})
                stale = []
                for ws in clients:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        stale.append(ws)
                for ws in stale:
                    clients.discard(ws)
            await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0.25)


def on_serial_line(line: str):
    state_mgr.parse_controller_line(line)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global broadcast_task

    apply_config()
    serial_mgr.set_line_callback(on_serial_line)
    serial_mgr.set_send_callback(gcode_log.log)

    try:
        await serial_mgr.connect()
        state_mgr.state.connected = True
    except Exception:
        logger.warning("Could not connect to serial on startup – running in offline mode")
        state_mgr.state.connected = False

    await engine.start()
    broadcast_task = asyncio.create_task(broadcast_status())
    logger.info("Printer host started – http://manualctrl.local:8000")

    yield

    broadcast_task.cancel()
    await engine.stop()
    await serial_mgr.disconnect()
    state_mgr.state.connected = False
    logger.info("Printer host stopped")


app = FastAPI(title="ManualCTRL Printer Host", lifespan=lifespan)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/config")
async def config_page():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ── Config REST API ──────────────────────────────────────────

@app.get("/api/config")
async def get_config():
    return JSONResponse({"schema": cfg.schema_for_ui(), "raw": cfg.get_raw_yaml()})


@app.put("/api/config/raw")
async def put_config_raw(request: Request):
    body = await request.json()
    try:
        cfg.set_raw_yaml(body.get("yaml", ""))
        apply_config()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.put("/api/config/field")
async def put_config_field(request: Request):
    body = await request.json()
    try:
        cfg.update_field(body["section"], body["key"], body["value"])
        apply_config()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/config/reset")
async def reset_config():
    cfg.reset_to_defaults()
    apply_config()
    return JSONResponse({"ok": True})


@app.post("/api/config/restart")
async def restart_service():
    apply_config()
    try:
        await serial_mgr.disconnect()
        state_mgr.state.connected = False
        await serial_mgr.connect()
        state_mgr.state.connected = True
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/machine")
async def get_machine_info():
    e = engine.e_params
    return JSONResponse({
        "bed_gear_ratio": engine.bed_gear_ratio,
        "nozzle_diameter": e.nozzle_diameter,
        "filament_diameter": e.filament_diameter,
        "max_extrude_cross_section": e.max_extrude_cross_section,
        "max_extrude_only_velocity": e.max_extrude_only_velocity,
        "max_volumetric_flow": round(e.max_volumetric_flow, 1),
        "z_max": cfg.get("machine", "z_max", 155),
    })


# ── G-code Logging API ────────────────────────────────────────

@app.get("/api/logs")
async def list_logs():
    return JSONResponse({
        "logs": gcode_log.list_logs(),
        "active": gcode_log.active,
        "current": gcode_log.current_file,
    })


@app.get("/api/logs/{filename}")
async def download_log(filename: str):
    path = LOGS_DIR / filename
    if not path.exists() or ".." in filename:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(path, media_type="text/plain", filename=filename)


# ── WebSocket ────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    logger.info("WebSocket client connected (%d total)", len(clients))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            await handle_message(msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        clients.discard(ws)
        logger.info("WebSocket client disconnected (%d remaining)", len(clients))


async def handle_message(msg: dict):
    action = msg.get("action")
    if not action:
        return

    if action in ("spin_y_pos", "spin_y_neg", "extrude_pos", "extrude_neg",
                   "move_z_pos", "move_z_neg"):
        await state_mgr.update_motion(action, msg.get("state", False))

    elif action == "set_hotend_temp":
        value = float(msg.get("value", 0))
        await state_mgr.set_temperature("hotend", value)
        await engine.send_temperature("hotend", value)

    elif action == "set_fan":
        speed = int(msg.get("value", 0))
        await state_mgr.set_fan(speed)
        await engine.send_fan(speed)

    elif action == "set_feedrate":
        await state_mgr.set_feedrate(msg.get("axis", "y"), float(msg.get("value", 3000)))

    elif action == "set_step":
        await state_mgr.set_step(msg.get("axis", "y"), float(msg.get("value", 1)))

    elif action == "home":
        await engine.send_home(cfg)

    elif action == "toggle_logging":
        if msg.get("state"):
            gcode_log.start()
            state_mgr.state.is_logging = True
        else:
            gcode_log.stop()
            state_mgr.state.is_logging = False

    elif action == "emergency_stop":
        estop_cmd = "M112" if cfg.get("firmware", "type", "custom") == "marlin" else "ESTOP"
        await serial_mgr.emergency_stop(estop_cmd)

    elif action == "gcode":
        await engine.send_gcode_raw(msg.get("value", ""))

    elif action == "connect":
        serial_mgr.port = msg.get("port", cfg.get("serial", "port", "/dev/ttyACM0"))
        serial_mgr.baudrate = int(msg.get("baud", cfg.get("serial", "baud_rate", 115200)))
        try:
            await serial_mgr.connect()
            state_mgr.state.connected = True
        except Exception as e:
            logger.error("Connect failed: %s", e)

    elif action == "disconnect":
        await serial_mgr.disconnect()
        state_mgr.state.connected = False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
