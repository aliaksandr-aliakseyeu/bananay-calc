"""FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API for calculating delivery costs from distribution centers to delivery points\n\n"
        "📚 **[Полная документация проекта →](/docs/overview)**\n"
        "## Основные возможности:\n"
        "- 🗺 Геопространственный поиск точек доставки\n"
        "- 🧮 Калькулятор стоимости доставки с учетом реальных дорог\n"
        "- 📊 Управление тарифами по регионам\n"
        "- 🔍 Autocomplete и fuzzy search по точкам доставки\n"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Bananay Delivery Calculator API",
        "docs": "/docs",
        "version": "0.1.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/docs/overview", tags=["Documentation"], response_class=HTMLResponse)
async def get_project_overview():
    """
    Get project overview documentation (PROJECT_OVERVIEW.md).

    Returns complete project documentation including:
    - Technologies used
    - Database schema and models
    - Import scripts description
    - API endpoints documentation
    - Calculator business logic

    Opens as beautiful HTML page in browser.
    """
    from pathlib import Path

    doc_path = Path(__file__).parent.parent / "PROJECT_OVERVIEW.md"

    if not doc_path.exists():
        return f"""
        <html>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1>❌ Documentation file not found</h1>
                <p>Path: {doc_path}</p>
            </body>
        </html>
        """

    markdown_content = doc_path.read_text(encoding="utf-8")

    # HTML template with GitHub-like styling
    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🍌 Bananay Delivery Calculator - Documentation</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #24292e;
                max-width: 980px;
                margin: 0 auto;
                padding: 45px;
                background-color: #ffffff;
            }
            .markdown-body {
                font-size: 16px;
            }
            .markdown-body h1 {
                padding-bottom: 0.3em;
                font-size: 2em;
                border-bottom: 1px solid #eaecef;
                margin-top: 24px;
                margin-bottom: 16px;
            }
            .markdown-body h2 {
                padding-bottom: 0.3em;
                font-size: 1.5em;
                border-bottom: 1px solid #eaecef;
                margin-top: 24px;
                margin-bottom: 16px;
            }
            .markdown-body h3 {
                font-size: 1.25em;
                margin-top: 24px;
                margin-bottom: 16px;
            }
            .markdown-body h4 {
                font-size: 1em;
                margin-top: 24px;
                margin-bottom: 16px;
            }
            .markdown-body h5 {
                font-size: 0.875em;
                margin-top: 24px;
                margin-bottom: 16px;
            }
            .markdown-body code {
                padding: 0.2em 0.4em;
                margin: 0;
                font-size: 85%;
                background-color: #f6f8fa;
                border-radius: 6px;
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            }
            .markdown-body pre {
                padding: 16px;
                overflow: auto;
                font-size: 85%;
                line-height: 1.45;
                background-color: #f6f8fa;
                border-radius: 6px;
            }
            .markdown-body pre code {
                display: inline;
                padding: 0;
                margin: 0;
                overflow: visible;
                line-height: inherit;
                background-color: transparent;
                border: 0;
            }
            .markdown-body table {
                border-spacing: 0;
                border-collapse: collapse;
                margin-top: 0;
                margin-bottom: 16px;
            }
            .markdown-body table th {
                padding: 6px 13px;
                border: 1px solid #dfe2e5;
                font-weight: 600;
                background-color: #f6f8fa;
            }
            .markdown-body table td {
                padding: 6px 13px;
                border: 1px solid #dfe2e5;
            }
            .markdown-body blockquote {
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
                margin: 0 0 16px 0;
            }
            .markdown-body a {
                color: #0366d6;
                text-decoration: none;
            }
            .markdown-body a:hover {
                text-decoration: underline;
            }
            .markdown-body hr {
                height: 0.25em;
                padding: 0;
                margin: 24px 0;
                background-color: #e1e4e8;
                border: 0;
            }
            .markdown-body ul, .markdown-body ol {
                padding-left: 2em;
                margin-top: 0;
                margin-bottom: 16px;
            }
            .markdown-body li {
                margin-top: 0.25em;
            }
            .back-link {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 10px 20px;
                background-color: #0366d6;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .back-link:hover {
                background-color: #0256c7;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <a href="/docs" class="back-link">← Back to API Docs</a>
        <div id="content" class="markdown-body"></div>
        <script>
            const markdownContent = `MARKDOWN_CONTENT_PLACEHOLDER`;
            document.getElementById('content').innerHTML = marked.parse(markdownContent);

            // Обрабатываем кастомные ID в формате {#id}
            document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
                const text = heading.textContent;
                const match = text.match(/\{#([a-z0-9-]+)\}/);
                if (match) {
                    // Устанавливаем ID из {#id}
                    heading.id = match[1];
                    // Убираем {#id} из текста
                    heading.textContent = text.replace(/\s*\{#[a-z0-9-]+\}/, '');
                }
            });

            // Плавная прокрутка для якорных ссылок
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        history.pushState(null, null, this.getAttribute('href'));
                    }
                });
            });

            // Прокрутка к якорю при загрузке
            if (window.location.hash) {
                setTimeout(() => {
                    const target = document.querySelector(window.location.hash);
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }, 100);
            }
        </script>
    </body>
    </html>
    """

    # Escape backticks in markdown for JS template literal
    escaped_content = markdown_content.replace('`', '\\`').replace('${', '\\${')
    html = html_template.replace('MARKDOWN_CONTENT_PLACEHOLDER', escaped_content)

    return html
