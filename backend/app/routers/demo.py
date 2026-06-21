"""Demo web app — target for Playwright test execution."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(prefix="/demo", tags=["Demo"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Fake session storage
_sessions = {}  # token -> username
_employees_db = [
    {"nik": "3273010101", "name": "Budi Santoso", "dept": "Engineering", "pos": "Senior Developer"},
    {"nik": "3273010102", "name": "Siti Rahmawati", "dept": "Marketing", "pos": "Brand Manager"},
    {"nik": "3273010103", "name": "Ahmad Fauzi", "dept": "Finance", "pos": "Accountant"},
    {"nik": "3273010104", "name": "Dewi Lestari", "dept": "HR", "pos": "HR Coordinator"},
    {"nik": "3273010105", "name": "Rudi Hermawan", "dept": "Engineering", "pos": "Frontend Developer"},
]

def _get_user(request: Request):
    token = request.cookies.get("session")
    return _sessions.get(token) if token else None

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("demo/login.html", {"request": request, "error": error})

@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        import uuid
        token = str(uuid.uuid4())
        _sessions[token] = username
        resp = RedirectResponse(url="/demo/dashboard", status_code=302)
        resp.set_cookie(key="session", value=token)
        return resp
    return templates.TemplateResponse("demo/login.html", {"request": request, "error": "Invalid credentials"}, status_code=401)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/dashboard.html", {"request": request, "username": user})

@router.get("/employees", response_class=HTMLResponse)
async def employee_list(request: Request):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/employees.html", {"request": request})

@router.get("/employees/add", response_class=HTMLResponse)
async def add_employee_page(request: Request):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/add_employee.html", {"request": request})

@router.post("/employees/add", response_class=HTMLResponse)
async def add_employee_post(request: Request, name: str = Form(...), nik: str = Form(...), department: str = Form(...), position: str = Form(...)):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    _employees_db.append({"nik": nik, "name": name, "dept": department, "pos": position})
    return templates.TemplateResponse("demo/add_employee.html", {"request": request, "created": True, "name": name})

@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    results = None
    if q:
        ql = q.lower()
        results = [e for e in _employees_db if ql in e["nik"].lower() or ql in e["name"].lower()]
    return templates.TemplateResponse("demo/search.html", {"request": request, "query": q, "results": results})

@router.get("/leave", response_class=HTMLResponse)
async def leave_page(request: Request):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/leave.html", {"request": request})

@router.get("/leave/approve/{leave_id}", response_class=HTMLResponse)
async def leave_approve(request: Request, leave_id: int):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/leave.html", {"request": request, "approved": True})

@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/reports.html", {"request": request})

@router.post("/reports", response_class=HTMLResponse)
async def reports_export(request: Request, month: str = Form(...)):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/reports.html", {"request": request, "exported": True, "month": month, "rows": 128})

@router.get("/payslip", response_class=HTMLResponse)
async def payslip_page(request: Request):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    return templates.TemplateResponse("demo/payslip.html", {"request": request})

@router.post("/payslip", response_class=HTMLResponse)
async def payslip_generate(request: Request, employee_id: int = Form(...), period: str = Form(...)):
    if not _get_user(request):
        return RedirectResponse(url="/demo/login")
    names = {1: "Budi Santoso", 2: "Siti Rahmawati", 3: "Ahmad Fauzi"}
    return templates.TemplateResponse("demo/payslip.html", {"request": request, "generated": True, "employee": names.get(employee_id, "Unknown"), "period": period})

@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/demo/login")
    resp.delete_cookie("session")
    return resp
