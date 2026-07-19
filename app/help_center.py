from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@router.get("/settings/help", response_class=HTMLResponse)
def help_center(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("help.html", {"request": request})


@router.get("/settings/user-guide", response_class=HTMLResponse)
def user_guide(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("user_guide.html", {"request": request})
