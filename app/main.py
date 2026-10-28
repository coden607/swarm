from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict

from .detector import CameraProcessor
from .health import health_check
from .brands import get_stream_capture
from enum import Enum

app = FastAPI(title="Swarm Detection Service")

# Serve UI static files
app.mount("/", StaticFiles(directory="ui/dist", html=True), name="ui")

# JWT configuration
class Settings(BaseModel):
    authjwt_secret_key: str = "super-secret-key"  # should be overridden via .env
    authjwt_token_location: set = {"headers"}
    authjwt_algorithm: str = "HS256"

@AuthJWT.load_config
def get_config():
    return Settings()

# Global exception handler for auth errors
@app.exception_handler(AuthJWTException)
def auth_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

# In‑memory store of cameras
cameras: Dict[str, CameraProcessor] = {}

class CameraBrand(str, Enum):
    """Supported camera brands / protocols.
    Extend this enum as new integrations are added.
    """
    GENERIC = "generic"
    ONVIF = "onvif"
    HIKVISION = "hikvision"
    AXIS = "axis"

class CameraConfig(BaseModel):
    url: str = Field(..., description="RTSP/HTTP camera stream URL")
    brand: CameraBrand = Field(CameraBrand.GENERIC, description="Camera brand / protocol")
    threshold: int = Field(10, description="Number of people that triggers an alert")
    alert_email_addresses: List[str] = Field(default_factory=list, description="Email addresses to notify via SMTP")

# Helper to enforce auth on protected routes
def require_auth(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    return Authorize

@app.post("/login")
def login(username: str, password: str, Authorize: AuthJWT = Depends()):
    # In a real deployment you would verify credentials against a DB.
    # For the demo we accept any non‑empty username/password.
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")
    access_token = Authorize.create_access_token(subject=username)
    return {"access_token": access_token}

@app.post("/cameras/{camera_id}")
def add_camera(camera_id: str, config: CameraConfig, background_tasks: BackgroundTasks, Authorize: AuthJWT = Depends(require_auth)):
    if camera_id in cameras:
        raise HTTPException(status_code=400, detail="Camera ID already exists")
    processor = CameraProcessor(config.url, config.brand.value, config.threshold, config.alert_email_addresses)
    cameras[camera_id] = processor
    background_tasks.add_task(processor.run)
    return {"status": "added", "camera_id": camera_id}

@app.delete("/cameras/{camera_id}")
def remove_camera(camera_id: str, Authorize: AuthJWT = Depends(require_auth)):
    processor = cameras.pop(camera_id, None)
    if processor:
        processor.stop()
        return {"status": "removed", "camera_id": camera_id}
    raise HTTPException(status_code=404, detail="Camera not found")

@app.get("/cameras")
def list_cameras(Authorize: AuthJWT = Depends(require_auth)):
    return {"cameras": list(cameras.keys())}

@app.get("/health")
def health():
    return health_check()
