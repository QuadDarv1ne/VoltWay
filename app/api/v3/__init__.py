"""
GraphQL API v3 router.

Provides GraphQL endpoint for flexible querying.
"""

from fastapi import APIRouter, Depends, Request, ContextMiddleware
from strawberry.fastapi import GraphQLRouter
from typing import Any, Dict, Optional
import asyncio

from app.api.v3.resolvers import schema
from app.core.dependencies import get_db, verify_api_key
from app.models.api_key import APIKey

router = APIRouter(prefix="/v3", tags=["GraphQL API v3"])


async def get_context(
    request: Request,
    db: Any = Depends(get_db),
    api_key: Optional[APIKey] = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Build GraphQL context.

    Provides database session and API key to resolvers.
    """
    return {
        "request": request,
        "db": db,
        "api_key": api_key,
    }


# Create GraphQL router with context
graphql_router = GraphQLRouter(
    schema,
    context_getter=get_context,
    path="/",
)

# Include in main router
router.include_router(graphql_router)


@router.get("/schema", tags=["GraphQL"])
async def get_graphql_schema():
    """Get GraphQL schema in SDL format"""
    return {"schema": schema.as_str()}


@router.get("/playground", tags=["GraphQL"])
async def graphql_playground(request: Request):
    """
    GraphQL Playground (deprecated, use /docs instead).

    For GraphQL exploration, use:
    - GET /api/v3/ for GraphQL endpoint
    - POST /api/v3/ with query
    """
    from fastapi.responses import HTMLResponse

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VoltWay GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
    </head>
    <body>
        <div id="root"></div>
        <script>
            window.addEventListener('load', function() {
                GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/api/v3/',
                    settings: {
                        'editor.theme': 'dark',
                        'request.credentials': 'include',
                    },
                });
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
