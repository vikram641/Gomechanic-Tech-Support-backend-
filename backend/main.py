from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from apps.accounts.router import auth_router, users_router
from apps.analytics.router import router as analytics_router
from apps.configuration.router import all_routers as configuration_routers
from apps.notifications.router import router as notifications_router
from apps.tickets.router import router as tickets_router
from core.config import settings
from core.errors import register_exception_handlers

app = FastAPI(title="GoMechanic Tech Support API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(users_router)
for config_router in configuration_routers:
    app.include_router(config_router)
app.include_router(tickets_router)
app.include_router(notifications_router)
app.include_router(analytics_router)

settings.media_root_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_root_path), name="media")
