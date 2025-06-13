import asyncio
import json
import logging.config
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import logging
import uvicorn
from services.commodities import CommoditiesService
from routers import router

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger("chkravyuh")
logger.setLevel(logging.DEBUG)
data_service = CommoditiesService()
active_connections: dict = {}

app = FastAPI(
    title="Chakravyuh",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    contact={
        "name": "Chkravyuh"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/mit/"
    }
)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://salmon-plant-01df91e0f.6.azurestaticapps.net"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "Sec-WebSocket-Extensions",
        "Sec-WebSocket-Key",
        "Sec-WebSocket-Protocol",
        "Sec-WebSocket-Version",
        "Connection",
        "Upgrade"
    ],
    expose_headers=["*"]
)

@app.websocket("/ws/{symbol}")
async def websocket_replay(websocket: WebSocket, symbol: str):
    await websocket.accept()
    connection_id = f"{symbol}_{id(websocket)}"
    active_connections[connection_id] = {
        'websocket': websocket,
        'symbol': symbol,
        'active': True,
        'paused': False,
        'replay_task': None
    }
    
    logger.info(f"WebSocket connected for {symbol}, connection_id: {connection_id}")
    
    try:
        await websocket.send_json({
            'type': 'connected',
            'symbol': symbol,
            'message': f'Connected to {symbol} replay stream'
        })
        
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"Received command: {data}")
                
                if data.get('command') == 'start':
                    await handle_replay_start(connection_id, data)
                elif data.get('command') == 'pause':
                    await handle_replay_pause(connection_id)
                elif data.get('command') == 'resume':
                    await handle_replay_resume(connection_id)
                elif data.get('command') == 'stop':
                    await handle_replay_stop(connection_id)
                
            except asyncio.TimeoutError:
                await websocket.send_json({
                    'type': 'heartbeat',
                    'timestamp': str(asyncio.get_event_loop().time())
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}")
        try:
            await websocket.send_json({
                'type': 'error',
                'message': str(e)
            })
        except:
            pass
    finally:
        if connection_id in active_connections:
            if active_connections[connection_id]['replay_task']:
                active_connections[connection_id]['replay_task'].cancel()
            del active_connections[connection_id]
        logger.info(f"Cleaned up connection {connection_id}")

async def handle_replay_start(connection_id: str, command: dict):
    if connection_id not in active_connections:
        return
    
    conn = active_connections[connection_id]
    websocket = conn['websocket']
    symbol = conn['symbol']
    
    if conn['replay_task']:
        conn['replay_task'].cancel()
    
    timeframe = command.get('timeframe', '1h')
    speed = command.get('speed', 1.0)
    start_date = command.get('start_date')
    
    logger.info(f"Starting replay for {symbol}, timeframe: {timeframe}, speed: {speed}, start_date: {start_date}")
    
    conn['replay_task'] = asyncio.create_task(
        replay_data_stream(connection_id, symbol, timeframe, speed, start_date)
    )

async def replay_data_stream(connection_id: str, symbol: str, timeframe: str, speed: float, start_date: str):
    try:
        if connection_id not in active_connections:
            return
            
        websocket = active_connections[connection_id]['websocket']
        
        async_gen = data_service.get_replay_data_stream(symbol, timeframe, start_date)
        
        async for bar_data in async_gen:
            if connection_id not in active_connections:
                break
                
            while active_connections[connection_id]['paused']:
                await asyncio.sleep(0.1)
                if connection_id not in active_connections:
                    return

            try:
                await websocket.send_json({
                    'type': 'bar',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'bar': bar_data
                })
                logger.debug(f"Sent bar data for {symbol}: {bar_data}")
            except Exception as e:
                logger.error(f"Error sending bar data: {e}")
                break
            
            await asyncio.sleep(1.0 / speed)
        
        if connection_id in active_connections:
            await websocket.send_json({
                'type': 'finished',
                'symbol': symbol,
                'message': 'Replay completed'
            })
        
    except asyncio.CancelledError:
        logger.info(f"Replay task cancelled for {symbol}")
    except Exception as e:
        logger.error(f"Replay error for {symbol}: {e}")
        if connection_id in active_connections:
            try:
                await active_connections[connection_id]['websocket'].send_json({
                    'type': 'error',
                    'message': f'Replay error: {str(e)}'
                })
            except:
                pass

async def handle_replay_pause(connection_id: str):
    if connection_id in active_connections:
        active_connections[connection_id]['paused'] = True
        websocket = active_connections[connection_id]['websocket']
        await websocket.send_json({
            'type': 'paused',
            'message': 'Replay paused'
        })
        logger.info(f"Replay paused for connection {connection_id}")

async def handle_replay_resume(connection_id: str):
    if connection_id in active_connections:
        active_connections[connection_id]['paused'] = False
        websocket = active_connections[connection_id]['websocket']
        await websocket.send_json({
            'type': 'resumed',
            'message': 'Replay resumed'
        })
        logger.info(f"Replay resumed for connection {connection_id}")

async def handle_replay_stop(connection_id: str):
    if connection_id in active_connections:
        conn = active_connections[connection_id]
        websocket = conn['websocket']
        
        if conn['replay_task']:
            conn['replay_task'].cancel()
            
        await websocket.send_json({
            'type': 'stopped',
            'message': 'Replay stopped'
        })
        active_connections[connection_id]['active'] = False
        logger.info(f"Replay stopped for connection {connection_id}")

@app.websocket("/ws/test")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello WebSocket!")

@app.get("/health-server", include_in_schema=False)
async def health_check():
    """
    Health check endpoint to verify if the API is running.
    """
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """
    Redirect root URL to the API documentation.
    """
    return RedirectResponse(url="/api/docs")

if __name__ == "__main__":
    uvicorn.run(app, port=8000, log_level="info")