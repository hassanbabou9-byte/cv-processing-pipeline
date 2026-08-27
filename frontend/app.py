"""
Streamlit frontend for the CV Processing Pipeline.

The frontend communicates with the FastAPI backend.

Architecture:

    Streamlit
        |
        | HTTP
        v
    FastAPI
        |
        +---- PostgreSQL
        |
        +---- MinIO

The frontend does NOT access PostgreSQL directly.

The frontend does NOT access MinIO directly.

All candidate information and images are retrieved through
the FastAPI API.
"""

from __future__ import annotations

import streamlit as st
import requests


# ==============================================================
# Configuration
# ==============================================================

API_BASE_URL = "http://127.0.0.1:8000"


# ==============================================================
# Page configuration
# ==============================================================

st.set_page_config(
    page_title="CV Processing Pipeline",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==============================================================
# Design tokens & styling
# ==============================================================

st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>

    :root {
        --ink: #101828;
        --ink-soft: #667085;
        --bg: #F5F6FA;
        --surface: #FFFFFF;
        --border: #E4E7EC;
        --accent: #0F6E5D;
        --accent-dark: #0B5347;
        --accent-soft: #E6F4F1;
        --success: #12B76A;
        --success-soft: #E7F8EF;
        --warning: #F79009;
        --warning-soft: #FFF4E5;
        --danger: #F04438;
        --danger-soft: #FEEBEA;
        --radius-lg: 16px;
        --radius-md: 10px;
        --shadow-card: 0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06);
        --shadow-card-hover: 0 4px 10px rgba(16, 24, 40, 0.08), 0 2px 4px rgba(16, 24, 40, 0.06);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: var(--bg);
    }

    h1, h2, h3 {
        font-family: 'Sora', sans-serif !important;
        letter-spacing: -0.01em;
    }

    /* ---------------------------------------------------------
       Header
    --------------------------------------------------------- */

    .app-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 0.15rem;
    }

    .app-header .badge {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        border-radius: 12px;
        background: linear-gradient(
            135deg,
            var(--accent) 0%,
            var(--accent-dark) 100%
        );
        font-size: 1.35rem;
        flex-shrink: 0;
        box-shadow: var(--shadow-card);
    }

    .main-title {
        font-family: 'Sora', sans-serif;
        font-size: 1.9rem;
        font-weight: 700;
        color: var(--ink);
        line-height: 1.15;
        margin: 0;
    }

    .subtitle {
        color: var(--ink-soft);
        font-size: 0.96rem;
        margin: 0.35rem 0 1.75rem 0;
        max-width: 640px;
        line-height: 1.5;
    }

    /* ---------------------------------------------------------
       Sidebar
    --------------------------------------------------------- */

    section[data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }

    section[data-testid="stSidebar"] h1 {
        font-size: 1.15rem !important;
    }

    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span:not(.pill):not(.pill-dot),
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] small,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--ink) !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="radio"] > label > div:first-child {
        border-color: var(--ink-soft) !important;
    }

    .sidebar-caption {
        color: var(--ink-soft) !important;
        font-size: 0.82rem;
        margin-top: -0.4rem;
    }

    /* ---------------------------------------------------------
       Status pill
    --------------------------------------------------------- */

    .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 11px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        white-space: nowrap;
    }

    .pill-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .pill-success {
        background: var(--success-soft);
        color: #067647;
    }

    .pill-success .pill-dot {
        background: var(--success);
    }

    .pill-warning {
        background: var(--warning-soft);
        color: #B54708;
    }

    .pill-warning .pill-dot {
        background: var(--warning);
    }

    .pill-danger {
        background: var(--danger-soft);
        color: #B42318;
    }

    .pill-danger .pill-dot {
        background: var(--danger);
    }

    .pill-neutral {
        background: #F2F4F7;
        color: var(--ink-soft);
    }

    .pill-neutral .pill-dot {
        background: #98A2B3;
    }

    .pill-accent {
        background: var(--accent-soft);
        color: var(--accent-dark);
    }

    .pill-accent .pill-dot {
        background: var(--accent);
    }

    /* ---------------------------------------------------------
       KPI metrics
    --------------------------------------------------------- */

    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.1rem 1.3rem;
        box-shadow: var(--shadow-card);
    }

    div[data-testid="stMetric"] label {
        color: var(--ink-soft) !important;
        font-weight: 500 !important;
        font-size: 0.84rem !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Sora', sans-serif;
        color: var(--ink);
    }

    /* ---------------------------------------------------------
       Bordered containers
    --------------------------------------------------------- */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--shadow-card);
        transition: box-shadow 120ms ease, transform 120ms ease;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: var(--shadow-card-hover);
    }

    /* ---------------------------------------------------------
       Avatar
    --------------------------------------------------------- */

    .avatar-photo {
        width: 100%;
        aspect-ratio: 1 / 1;
        object-fit: cover;
        border-radius: 12px;
        border: 1px solid var(--border);
        display: block;
    }

    .avatar-initials {
        width: 100%;
        aspect-ratio: 1 / 1;
        border-radius: 12px;
        background: linear-gradient(
            135deg,
            var(--accent-soft) 0%,
            #F4FBFA 100%
        );
        color: var(--accent-dark);
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        font-size: 1.5rem;
        border: 1px solid var(--border);
    }

    .avatar-photo-lg {
        width: 100%;
        border-radius: var(--radius-lg);
        border: 1px solid var(--border);
        object-fit: cover;
    }

    .avatar-initials-lg {
        width: 100%;
        aspect-ratio: 1 / 1;
        border-radius: var(--radius-lg);
        background: linear-gradient(
            135deg,
            var(--accent-soft) 0%,
            #F4FBFA 100%
        );
        color: var(--accent-dark);
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        border: 1px solid var(--border);
    }

    /* ---------------------------------------------------------
       Candidate card text
    --------------------------------------------------------- */

    .candidate-name {
        font-family: 'Sora', sans-serif;
        font-size: 1.08rem;
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 2px;
    }

    .candidate-email {
        color: var(--ink-soft);
        font-size: 0.86rem;
        margin-bottom: 8px;
    }

    .meta-row {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 4px;
    }

    .storage-key {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: var(--ink-soft);
        margin-top: 6px;
        word-break: break-all;
    }

    .section-title {
        font-family: 'Sora', sans-serif;
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 0.4rem;
        margin-bottom: 0.9rem;
        color: var(--ink);
    }

    .empty-state {
        border: 1px dashed var(--border);
        border-radius: var(--radius-lg);
        padding: 2.2rem 1.5rem;
        text-align: center;
        color: var(--ink-soft);
        background: var(--surface);
    }

    .empty-state .icon {
        font-size: 1.8rem;
        margin-bottom: 0.4rem;
    }

    /* ---------------------------------------------------------
       Buttons
    --------------------------------------------------------- */

    .stButton > button {
        border-radius: var(--radius-md);
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid var(--border);
        transition: all 120ms ease;
    }

    .stButton > button:hover {
        border-color: var(--accent);
        color: var(--accent-dark);
    }

    button[kind="primary"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
    }

    button[kind="primary"]:hover {
        background: var(--accent-dark) !important;
        border-color: var(--accent-dark) !important;
    }

    /* ---------------------------------------------------------
       Misc
    --------------------------------------------------------- */

    hr {
        border-color: var(--border) !important;
    }

    div[data-testid="stFileUploader"] section {
        background: var(--surface);
        border-radius: var(--radius-lg);
        border: 1px dashed var(--border);
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================
# Presentation helpers
# ==============================================================


def initials_of(
    first_name: str,
    last_name: str,
) -> str:
    """
    Build a two-letter initials string for the avatar fallback.
    """

    first_letter = first_name.strip()[:1] if first_name else ""
    last_letter = last_name.strip()[:1] if last_name else ""

    combined = f"{first_letter}{last_letter}".upper()

    return combined or "?"


def status_pill_html(
    status: str,
) -> str:
    """
    Render a colored status pill for a candidate's statut.
    """

    normalized = (status or "").strip().upper()

    mapping = {
        "ACTIF": ("pill-success", "Active"),
        "INACTIF": ("pill-neutral", "Inactive"),
        "EN_ATTENTE": ("pill-warning", "Pending"),
        "SUSPENDU": ("pill-danger", "Suspended"),
    }

    css_class, label = mapping.get(
        normalized,
        ("pill-neutral", status or "Unknown"),
    )

    return (
        f'<span class="pill {css_class}">'
        f'<span class="pill-dot"></span>{label}</span>'
    )


def role_pill_html(
    role: str,
) -> str:
    """
    Render a neutral accent pill for a candidate's role.
    """

    label = role or "COLLABORATEUR"

    return (
        f'<span class="pill pill-accent">'
        f'<span class="pill-dot"></span>{label}</span>'
    )


# ==============================================================
# API helpers
# ==============================================================


def api_get(
    endpoint: str,
    timeout: int = 30,
) -> requests.Response:
    """
    Perform a GET request against the FastAPI backend.
    """

    url = f"{API_BASE_URL}{endpoint}"

    return requests.get(
        url,
        timeout=timeout,
    )


def api_post_files(
    endpoint: str,
    files: list[tuple[str, tuple[str, bytes, str]]],
    timeout: int = 300,
) -> requests.Response:
    """
    Upload files to the FastAPI backend.
    """

    url = f"{API_BASE_URL}{endpoint}"

    return requests.post(
        url,
        files=files,
        timeout=timeout,
    )


# ==============================================================
# Backend health
# ==============================================================


def check_api_health() -> bool:
    """
    Check whether FastAPI is available.
    """

    try:
        response = api_get(
            "/health",
            timeout=5,
        )

        return response.status_code == 200

    except requests.RequestException:
        return False


# ==============================================================
# Candidates API
# ==============================================================


def get_candidates(
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Retrieve candidates from FastAPI.

    FastAPI is responsible for retrieving the information
    from PostgreSQL.
    """

    try:
        response = api_get(
            f"/candidates?limit={limit}&offset={offset}",
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):

            if "candidates" in data:

                candidates = data["candidates"]

                if isinstance(candidates, list):
                    return candidates

                return []

            if "items" in data:

                items = data["items"]

                if isinstance(items, list):
                    return items

                return []

            if "results" in data:

                results = data["results"]

                if isinstance(results, list):
                    return results

                return []

        if isinstance(data, list):
            return data

        return []

    except requests.HTTPError as exc:

        st.error(
            f"FastAPI returned an HTTP error while retrieving candidates: {exc}"
        )

        return []

    except requests.RequestException as exc:

        st.error(
            f"Unable to retrieve candidates from FastAPI: {exc}"
        )

        return []

    except ValueError as exc:

        st.error(
            f"FastAPI returned invalid JSON: {exc}"
        )

        return []


# ==============================================================
# Candidate details API
# ==============================================================


def get_candidate(
    collaborateur_id: str,
) -> dict | None:
    """
    Retrieve one candidate.
    """

    try:

        response = api_get(
            f"/candidates/{collaborateur_id}",
            timeout=30,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):
            return data

        return None

    except requests.HTTPError as exc:

        st.error(
            f"Unable to retrieve candidate: {exc}"
        )

        return None

    except requests.RequestException as exc:

        st.error(
            f"Unable to retrieve candidate: {exc}"
        )

        return None

    except ValueError as exc:

        st.error(
            f"Invalid candidate response from FastAPI: {exc}"
        )

        return None


# ==============================================================
# Candidate image API
# ==============================================================


def get_candidate_image(
    collaborateur_id: str,
) -> tuple[bytes, str] | None:
    """
    Retrieve the candidate image through FastAPI.

    FastAPI retrieves the image from MinIO.

    Returns
    -------
    tuple[bytes, str] | None
        Image bytes and the actual HTTP content type.
    """

    try:

        response = api_get(
            f"/candidates/{collaborateur_id}/image",
            timeout=30,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        if not response.content:
            return None

        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
            .split(";")[0]
            .strip()
            .lower()
        )

        if not content_type.startswith("image/"):
            content_type = "image/png"

        return response.content, content_type

    except requests.RequestException:
        return None


# ==============================================================
# Candidate image rendering
# ==============================================================


def render_candidate_image(
    image_data: tuple[bytes, str],
    large: bool = False,
) -> None:
    """
    Render a candidate image using Streamlit's native image renderer.

    The actual content type returned by FastAPI is preserved.
    This avoids incorrectly treating PNG/WebP images as JPEG.
    """

    image_bytes, content_type = image_data

    st.image(
        image_bytes,
        width="stretch",
    )


# ==============================================================
# CV upload API
# ==============================================================


def upload_cvs(
    uploaded_files,
) -> dict | None:
    """
    Upload CV files to the FastAPI batch processing endpoint.
    """

    files = []

    for uploaded_file in uploaded_files:

        content = uploaded_file.getvalue()

        files.append(
            (
                "files",
                (
                    uploaded_file.name,
                    content,
                    uploaded_file.type
                    or "application/octet-stream",
                ),
            )
        )

    try:

        response = api_post_files(
            "/upload",
            files=files,
            timeout=300,
        )

        response.raise_for_status()

        return response.json()

    except requests.HTTPError as exc:

        st.error(
            f"CV processing failed: {exc}"
        )

        try:
            st.error(response.text)
        except Exception:
            pass

        return None

    except requests.RequestException as exc:

        st.error(
            f"Unable to connect to FastAPI: {exc}"
        )

        return None

    except ValueError as exc:

        st.error(
            f"FastAPI returned invalid JSON: {exc}"
        )

        return None


# ==============================================================
# Sidebar
# ==============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:2px;">
            <div style="width:34px;height:34px;border-radius:9px;
                        background:linear-gradient(135deg,#0F6E5D,#0B5347);
                        display:flex;align-items:center;justify-content:center;
                        font-size:1.05rem;">🗂️</div>
            <div style="font-family:'Sora',sans-serif;font-weight:700;font-size:1.1rem;">
                CV Pipeline
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-caption">AI-powered CV processing &amp; candidate management</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("**Backend status**")

    if check_api_health():

        st.markdown(
            '<span class="pill pill-success"><span class="pill-dot"></span>FastAPI online</span>',
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            '<span class="pill pill-danger"><span class="pill-dot"></span>FastAPI offline</span>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="sidebar-caption" style="margin-top:6px;font-family:\'JetBrains Mono\',monospace;">{API_BASE_URL}</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("**Navigation**")

    page = st.radio(
        "Go to",
        [
            "Dashboard",
            "Candidates",
            "Upload CVs",
        ],
        label_visibility="collapsed",
    )


# ==============================================================
# Header
# ==============================================================

st.markdown(
    """
    <div class="app-header">
        <div class="badge">🗂️</div>
        <div class="main-title">CV Processing Pipeline</div>
    </div>
    <div class="subtitle">
        Manage candidates processed by the AI CV pipeline.
        Candidate information is stored in PostgreSQL and
        candidate photographs are stored in MinIO.
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================================================
# Dashboard
# ==============================================================

if page == "Dashboard":

    st.markdown(
        '<div class="section-title">Dashboard</div>',
        unsafe_allow_html=True,
    )

    refresh_col, _ = st.columns([1, 5])

    with refresh_col:

        if st.button(
            "🔄 Refresh",
            key="dashboard_refresh",
            use_container_width=True,
        ):
            st.rerun()

    candidates = get_candidates()

    total_candidates = len(candidates)

    candidates_with_images = sum(
        1
        for candidate in candidates
        if candidate.get("image_object_key")
    )

    candidates_without_images = (
        total_candidates - candidates_with_images
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Candidates",
            total_candidates,
        )

    with col2:

        st.metric(
            "Candidates with photo",
            candidates_with_images,
        )

    with col3:

        st.metric(
            "Without photo",
            candidates_without_images,
        )

    st.write("")

    st.markdown(
        '<div class="section-title">Recent candidates</div>',
        unsafe_allow_html=True,
    )

    if not candidates:

        st.markdown(
            """
            <div class="empty-state">
                <div class="icon">🗒️</div>
                No candidates found in PostgreSQL yet.<br>
                Upload a CV to get started.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        for candidate in candidates[:5]:

            first_name = candidate.get("prenom", "")
            last_name = candidate.get("nom", "")
            email = candidate.get("email", "")
            image_key = candidate.get("image_object_key")

            with st.container(border=True):

                row_left, row_right = st.columns([5, 1])

                with row_left:

                    st.markdown(
                        f"""
                        <div class="candidate-name">{first_name} {last_name}</div>
                        <div class="candidate-email">{email or "No email on file"}</div>
                        """,
                        unsafe_allow_html=True,
                    )

                with row_right:

                    if image_key:

                        st.markdown(
                            '<span class="pill pill-accent"><span class="pill-dot"></span>Photo</span>',
                            unsafe_allow_html=True,
                        )

                    else:

                        st.markdown(
                            '<span class="pill pill-neutral"><span class="pill-dot"></span>No photo</span>',
                            unsafe_allow_html=True,
                        )


# ==============================================================
# Candidates page
# ==============================================================

elif page == "Candidates":

    st.markdown(
        '<div class="section-title">Candidates</div>',
        unsafe_allow_html=True,
    )

    col_refresh, col_info = st.columns([1, 5])

    with col_refresh:

        if st.button(
            "🔄 Refresh",
            key="candidates_refresh",
            use_container_width=True,
        ):

            st.rerun()

    candidates = get_candidates()

    if not candidates:

        st.markdown(
            """
            <div class="empty-state">
                <div class="icon">🔍</div>
                No candidates found.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        with col_info:

            st.markdown(
                f'<div style="padding-top:0.55rem;color:var(--ink-soft);font-size:0.9rem;">'
                f"{len(candidates)} candidate(s) found.</div>",
                unsafe_allow_html=True,
            )

        st.write("")

        for candidate in candidates:

            candidate_id = candidate.get("id")
            first_name = candidate.get("prenom", "")
            last_name = candidate.get("nom", "")
            full_name = f"{first_name} {last_name}".strip()
            email = candidate.get("email", "No email")
            role = candidate.get("role", "COLLABORATEUR")
            status = candidate.get("statut", "ACTIF")
            image_key = candidate.get("image_object_key")

            with st.container(border=True):

                left, middle, right = st.columns([1, 3, 1])

                # --------------------------------------------------
                # Image
                # --------------------------------------------------

                with left:

                    if candidate_id and image_key:

                        image_data = get_candidate_image(
                            candidate_id
                        )

                        if image_data:

                            render_candidate_image(
                                image_data
                            )

                        else:

                            st.markdown(
                                f'<div class="avatar-initials">{initials_of(first_name, last_name)}</div>',
                                unsafe_allow_html=True,
                            )

                    else:

                        st.markdown(
                            f'<div class="avatar-initials">{initials_of(first_name, last_name)}</div>',
                            unsafe_allow_html=True,
                        )

                # --------------------------------------------------
                # Candidate information
                # --------------------------------------------------

                with middle:

                    st.markdown(
                        f"""
                        <div class="candidate-name">{full_name or "Unnamed candidate"}</div>
                        <div class="candidate-email">{email}</div>
                        <div class="meta-row">{role_pill_html(role)}{status_pill_html(status)}</div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if image_key:

                        st.markdown(
                            f'<div class="storage-key">MinIO · {image_key}</div>',
                            unsafe_allow_html=True,
                        )

                # --------------------------------------------------
                # Profile button
                # --------------------------------------------------

                with right:

                    st.write("")

                    if candidate_id:

                        if st.button(
                            "View profile",
                            key=f"view_{candidate_id}",
                            use_container_width=True,
                        ):

                            st.session_state[
                                "selected_candidate_id"
                            ] = str(candidate_id)

                            st.rerun()

            st.write("")


# ==============================================================
# Candidate profile
# ==============================================================

if (
    "selected_candidate_id" in st.session_state
    and page == "Candidates"
):

    candidate_id = st.session_state[
        "selected_candidate_id"
    ]

    candidate = get_candidate(
        candidate_id
    )

    if candidate:

        st.write("")

        st.markdown(
            '<div class="section-title">Candidate profile</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "← Back to candidates",
            key="back_to_candidates",
        ):

            del st.session_state[
                "selected_candidate_id"
            ]

            st.rerun()

        st.write("")

        with st.container(border=True):

            left, right = st.columns([1, 2])

            # ------------------------------------------------------
            # Candidate image
            # ------------------------------------------------------

            with left:

                image_key = candidate.get(
                    "image_object_key"
                )

                first_name = candidate.get(
                    "prenom",
                    "",
                )

                last_name = candidate.get(
                    "nom",
                    "",
                )

                if image_key:

                    image_data = get_candidate_image(
                        candidate_id
                    )

                    if image_data:

                        render_candidate_image(
                            image_data,
                            large=True,
                        )

                    else:

                        st.markdown(
                            f'<div class="avatar-initials-lg">{initials_of(first_name, last_name)}</div>',
                            unsafe_allow_html=True,
                        )

                        st.caption(
                            "⚠️ Image could not be retrieved from MinIO."
                        )

                else:

                    st.markdown(
                        f'<div class="avatar-initials-lg">{initials_of(first_name, last_name)}</div>',
                        unsafe_allow_html=True,
                    )

            # ------------------------------------------------------
            # Candidate information
            # ------------------------------------------------------

            with right:

                first_name = candidate.get(
                    "prenom",
                    "",
                )

                last_name = candidate.get(
                    "nom",
                    "",
                )

                full_name = (
                    f"{first_name} {last_name}".strip()
                )

                st.markdown(
                    f'<div style="font-family:\'Sora\',sans-serif;font-weight:700;font-size:1.4rem;">'
                    f'{full_name or "Unnamed candidate"}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f'<div class="meta-row" style="margin-top:8px;">'
                    f'{role_pill_html(candidate.get("role", "N/A"))}'
                    f'{status_pill_html(candidate.get("statut", "N/A"))}</div>',
                    unsafe_allow_html=True,
                )

                st.write("")

                info_col1, info_col2 = st.columns(2)

                with info_col1:

                    st.markdown(
                        f'<div class="candidate-email" style="margin-bottom:2px;">Email</div>'
                        f'<div style="font-weight:500;">{candidate.get("email", "N/A")}</div>',
                        unsafe_allow_html=True,
                    )

                with info_col2:

                    phone = candidate.get(
                        "telephone_professionnel"
                    )

                    st.markdown(
                        f'<div class="candidate-email" style="margin-bottom:2px;">Phone</div>'
                        f'<div style="font-weight:500;">{phone or "N/A"}</div>',
                        unsafe_allow_html=True,
                    )

        st.write("")

        # ----------------------------------------------------------
        # Professional biography
        # ----------------------------------------------------------

        with st.container(border=True):

            st.markdown(
                '<div class="section-title">Professional biography</div>',
                unsafe_allow_html=True,
            )

            biography = candidate.get(
                "bio_professionnelle"
            )

            if biography:

                st.write(
                    biography
                )

            else:

                st.caption(
                    "No professional biography available."
                )

        st.write("")

        # ----------------------------------------------------------
        # Storage
        # ----------------------------------------------------------

        with st.container(border=True):

            st.markdown(
                '<div class="section-title">Storage</div>',
                unsafe_allow_html=True,
            )

            image_key = candidate.get(
                "image_object_key"
            )

            if image_key:

                st.markdown(
                    '<span class="pill pill-success"><span class="pill-dot"></span>Image stored in MinIO</span>',
                    unsafe_allow_html=True,
                )

                st.code(
                    image_key,
                    language="text",
                )

            else:

                st.markdown(
                    '<span class="pill pill-warning"><span class="pill-dot"></span>No image for this candidate</span>',
                    unsafe_allow_html=True,
                )

    else:

        st.error(
            "Candidate could not be found."
        )


# ==============================================================
# Upload CVs
# ==============================================================

elif page == "Upload CVs":

    st.markdown(
        '<div class="section-title">Upload CVs</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="color:var(--ink-soft);margin-bottom:0.8rem;">'
        "Upload one or multiple CVs for automatic parsing and enrichment. "
        "Supported formats: <strong>PDF</strong>, <strong>DOCX</strong>.</div>",
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Select CV files",
        type=[
            "pdf",
            "docx",
        ],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:

        with st.container(border=True):

            st.markdown(
                f"**{len(uploaded_files)} file(s) selected**"
            )

            for uploaded_file in uploaded_files:

                st.markdown(
                    f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.85rem;'
                    f'color:var(--ink-soft);">📄 {uploaded_file.name}</div>',
                    unsafe_allow_html=True,
                )

        st.write("")

        if st.button(
            "Process CVs",
            type="primary",
            key="process_cvs",
        ):

            with st.spinner(
                "Processing CVs..."
            ):

                result = upload_cvs(
                    uploaded_files
                )

            if result:

                total_files = result.get(
                    "total_files"
                )

                successful = result.get(
                    "successful"
                )

                failed = result.get(
                    "failed"
                )

                # --------------------------------------------------
                # Summary
                # --------------------------------------------------

                st.write("")

                st.markdown(
                    '<span class="pill pill-success"><span class="pill-dot"></span>'
                    "CV batch processing completed</span>",
                    unsafe_allow_html=True,
                )

                st.write("")

                summary_col1, summary_col2, summary_col3 = st.columns(
                    3
                )

                with summary_col1:

                    st.metric(
                        "Total files",
                        total_files
                        if total_files is not None
                        else 0,
                    )

                with summary_col2:

                    st.metric(
                        "Successful",
                        successful
                        if successful is not None
                        else 0,
                    )

                with summary_col3:

                    st.metric(
                        "Failed",
                        failed
                        if failed is not None
                        else 0,
                    )

                st.write("")

                # --------------------------------------------------
                # Processing results
                # --------------------------------------------------

                st.markdown(
                    '<div class="section-title">Processing results</div>',
                    unsafe_allow_html=True,
                )

                results = result.get(
                    "results",
                    [],
                )

                for item in results:

                    filename = item.get(
                        "filename",
                        "Unknown",
                    )

                    status = item.get(
                        "status",
                        "unknown",
                    )

                    with st.container(border=True):

                        if status == "success":

                            res_left, res_right = st.columns(
                                [4, 2]
                            )

                            with res_left:

                                st.markdown(
                                    f'<span class="pill pill-success"><span class="pill-dot"></span>'
                                    f"{filename}</span>",
                                    unsafe_allow_html=True,
                                )

                            collaborateur_id = item.get(
                                "collaborateur_id"
                            )

                            if collaborateur_id:

                                with res_right:

                                    st.markdown(
                                        f'<div class="storage-key">ID · {collaborateur_id}</div>',
                                        unsafe_allow_html=True,
                                    )

                        else:

                            st.markdown(
                                f'<span class="pill pill-danger"><span class="pill-dot"></span>'
                                f"{filename}</span>",
                                unsafe_allow_html=True,
                            )

                            st.caption(
                                item.get(
                                    "error_message",
                                    "Unknown error",
                                )
                            )

                st.write("")

                with st.expander(
                    "Raw API response"
                ):

                    st.json(
                        result
                    )

                st.info(
                    "The CV data has been saved. "
                    "Go to Candidates and click Refresh "
                    "to view the updated candidate list."
                )

    else:

        st.markdown(
            """
            <div class="empty-state">
                <div class="icon">📤</div>
                Select one or more CV files to begin.
            </div>
            """,
            unsafe_allow_html=True,
        )