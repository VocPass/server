from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse, FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import aiohttp
from dotenv import load_dotenv
import utils.notice as notice
from utils import metrics as m

import os
import subprocess
from urllib.parse import quote
from pathlib import Path

import utils.pb as pb

router = APIRouter()
load_dotenv()
limiter = Limiter(key_func=get_remote_address)
REPO_ROOT = Path(__file__).resolve().parents[1]
GITHUB_OWNER = "vocpass"
GITHUB_REPO = "server"
GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "VocPass-Server-Version-Check",
    "X-GitHub-Api-Version": "2022-11-28",
}


def require_cookie_header(
    cookie: str = Header(
        ...,
        alias="Cookie",
        description="登入後取得的 Cookie 標頭",
    )
):
    return cookie


def run_git(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def short_commit(commit: str | None) -> str | None:
    return commit[:7] if commit else None


def read_git_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def git_metadata_path(*parts: str) -> Path | None:
    git_path = REPO_ROOT / ".git"
    if git_path.is_dir():
        return git_path.joinpath(*parts)

    gitdir = read_git_text(git_path)
    if gitdir and gitdir.startswith("gitdir: "):
        path = Path(gitdir.removeprefix("gitdir: ").strip())
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path.joinpath(*parts)

    return None


def read_git_head() -> tuple[str | None, str | None]:
    head_path = git_metadata_path("HEAD")
    if not head_path:
        return None, None

    head = read_git_text(head_path)
    if not head:
        return None, None

    if not head.startswith("ref: "):
        return head, None

    ref = head.removeprefix("ref: ").strip()
    branch = ref.removeprefix("refs/heads/")
    ref_path = git_metadata_path(*ref.split("/"))
    commit = read_git_text(ref_path) if ref_path else None
    if commit:
        return commit, branch

    packed_refs_path = git_metadata_path("packed-refs")
    packed_refs = read_git_text(packed_refs_path) if packed_refs_path else None
    if not packed_refs:
        return None, branch

    for line in packed_refs.splitlines():
        if line.startswith("#") or line.startswith("^"):
            continue
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0], branch

    return None, branch


def normalize_branch(branch: str | None) -> str | None:
    if not branch:
        return None
    if branch.startswith("refs/heads/"):
        return branch.removeprefix("refs/heads/")
    if branch.startswith("origin/"):
        return branch.removeprefix("origin/")
    return branch


async def fetch_github_json(url: str) -> dict | None:
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        ) as session:
            async with session.get(url, headers=GITHUB_API_HEADERS) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except (aiohttp.ClientError, TimeoutError):
        return None


async def fetch_github_latest_commit(branch: str | None) -> tuple[str | None, str | None]:
    repo_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

    if branch and branch != "HEAD":
        encoded_branch = quote(branch, safe="")
        commit_url = f"{repo_url}/commits/{encoded_branch}"
        commit_data = await fetch_github_json(commit_url)
        if commit_data and commit_data.get("sha"):
            return commit_data["sha"], branch

    repo_data = await fetch_github_json(repo_url)
    default_branch = repo_data.get("default_branch") if repo_data else None
    if not default_branch:
        return None, branch

    encoded_branch = quote(default_branch, safe="")
    commit_data = await fetch_github_json(f"{repo_url}/commits/{encoded_branch}")
    if not commit_data or not commit_data.get("sha"):
        return None, default_branch

    return commit_data["sha"], default_branch


headers = {
    "Accept": "*/*",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


@router.get("/", summary="首頁")
async def index(request: Request):
    return FileResponse("templates/index.html")


@router.get("/api/version", summary="目前部署版本")
async def version():
    file_commit, file_branch = read_git_head()
    current_commit = file_commit or run_git(["rev-parse", "HEAD"])
    branch = normalize_branch(
        file_branch or run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    )
    remote_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

    latest_commit, latest_branch = await fetch_github_latest_commit(branch)

    is_latest = None
    if current_commit and latest_commit:
        is_latest = current_commit == latest_commit

    return {
        "code": 200,
        "message": "Success.",
        "data": {
            "commit": current_commit,
            "short_commit": short_commit(current_commit),
            "branch": branch,
            "remote": remote_url,
            "latest_commit": latest_commit,
            "latest_short_commit": short_commit(latest_commit),
            "latest_branch": latest_branch,
            "is_latest": is_latest,
        },
    }


@router.get("/privacy-policy", summary="隱私權政策")
async def privacy_policy():
    return FileResponse("templates/privacy-policy.html")


@router.get("/disclaimer", summary="免責聲明")
async def disclaimer():
    return FileResponse("templates/disclaimer.html")


@router.get("/creator-policy", summary="創作者政策")
async def creator_policy():
    return FileResponse("templates/creator-policy.html")


@router.get("/terms-of-use", summary="內容使用條款")
async def terms_of_use():
    return FileResponse("templates/terms-of-use.html")


@router.get("/school")
async def get_all_schools(request: Request):
    return request.app.state.schools


@router.get("/me", summary="獲取使用者資訊")
async def get_me(request: Request, response: Response):
    return FileResponse("templates/me.html")


@router.get("/@{username}", summary="公開個人資料頁面")
async def get_user_profile(request: Request, username: str):
    return FileResponse("templates/user.html")


@router.get("/apply", summary="申請學校")
async def apply_school():
    return FileResponse("templates/apply.html")

@router.get("/selfhost", summary="自架測試端點")
async def self_host_test(request: Request):
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = {
        "app_env": os.environ.get("APP_ENV"),
    }
    return data

@router.get("/ping", summary="檢查登入狀態")
async def ping(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    """檢查登入狀態，回傳 JSON 格式的結果。
    - 需帶入 cookies
    - **返回值**: 包含登入狀態的 JSON 物件。
    """
    m.SCHOOL_LOGIN_CHECKS_TOTAL.labels(school_name=school_name, result="attempt").inc()
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    db = request.app.state.pb_client
    
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data
    user = pb.get_user(request.headers.get("Authorization"))
    

    async with aiohttp.ClientSession(
        cookies=request.cookies, headers=headers
    ) as session:

        # for v4
        query = [f"token={request.cookies.get('X-Token')}"]

        # for v5
        rd = {
            "session_key": request.cookies.get("session_key"),
        }
        url = f"{school['api']}{school['url']['logined']}?" + "&".join(query)

        for method in ["get", "post"]:
            r = await getattr(session, method)(url, data=rd)
            try:
                html = await r.text(encoding="utf-8")
            except:
                html = await r.text(encoding="big5")

            for i in school["login"]["successKeywords"]:
                if i in html:
                    if user:
                        db.collection("users").update(user.id, {"school": school_name})
                        
                    m.SCHOOL_LOGIN_CHECKS_TOTAL.labels(
                        school_name=school_name, result="logged_in"
                    ).inc()
                    data["code"] = 200
                    data["message"] = "Success."
                    data["data"] = {"logged_in": True}

                    return data

    m.SCHOOL_LOGIN_CHECKS_TOTAL.labels(
        school_name=school_name, result="not_logged_in"
    ).inc()
    response.status_code = status.HTTP_403_FORBIDDEN
    data["code"] = 403
    data["message"] = "Success."
    data["data"] = {"logged_in": False}
    return data

@router.get("/font", summary="字體預覽頁面")
async def font_preview():
    return FileResponse("templates/font_preview.html", media_type="text/html")
