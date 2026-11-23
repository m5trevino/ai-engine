"""
UI SCAFFOLD — Component map generation + frontend binding from Peacock invariants.

Given backend code or an API spec, this module:
  1. Identifies all API endpoints
  2. Queries Peacock `bindings` collection for API→UI invariants
  3. Generates a component map (JSON) describing every UI element
  4. Scaffolds actual React/Vue/HTML components with proper bindings
  5. Applies CSS decoration

Usage:
    from app.core.ui_scaffold import ComponentMapGenerator
    gen = ComponentMapGenerator()
    comp_map = await gen.generate_map(api_spec, framework="react")
    frontend_code = await gen.scaffold(comp_map, style="tailwind")
"""

import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict

from app.core.memory_engine import query_memory
from app.utils.groq_token_counter import GroqTokenCounter
from app.core.key_manager import GroqPool
from openai import AsyncOpenAI


@dataclass
class UIComponent:
    """A single UI component with its binding invariant."""
    name: str
    component_type: str  # form, table, detail_view, modal, button_group, chart, card, list
    api_endpoint: str
    http_method: str
    intent: str  # RESOURCE_CREATION, RESOURCE_READ, RESOURCE_UPDATE, RESOURCE_DELETE
    ui_invariant: str  # from bindings collection
    fields: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    position: str = "main"  # header, sidebar, main, footer, modal
    css_classes: List[str] = field(default_factory=list)
    props: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentMap:
    """Full component map for a web application."""
    app_name: str
    framework: str  # react, vue, svelte, vanilla
    style_system: str  # tailwind, bootstrap, css-modules, styled-components
    layout: Dict[str, List[str]]  # header/sidebar/main/footer -> list of component names
    components: List[UIComponent]
    routes: List[Dict[str, str]]  # path -> component_name
    global_bindings: List[Dict] = field(default_factory=list)


class ComponentMapGenerator:
    """Generate component maps by cross-referencing code with Peacock bindings."""

    # Component type inference from HTTP method + intent
    METHOD_COMPONENT_MAP = {
        ("POST", "RESOURCE_CREATION"): "form",
        ("POST", "AUTHENTICATION"): "form",
        ("GET", "RESOURCE_READ"): "table",
        ("GET", "RESOURCE_DETAIL"): "detail_view",
        ("PUT", "RESOURCE_UPDATE"): "form",
        ("PATCH", "RESOURCE_UPDATE"): "form",
        ("DELETE", "RESOURCE_DELETION"): "button_group",
        ("GET", "ANALYTICS"): "chart",
        ("GET", "SEARCH"): "search_bar",
    }

    def __init__(self, model_id: str = "llama-3.3-70b-versatile"):
        self.model_id = model_id
        self.counter = GroqTokenCounter()

    async def generate_map(
        self,
        source: str,  # backend code, OpenAPI spec, or API description
        framework: str = "react",
        style_system: str = "tailwind",
        app_name: str = "GeneratedApp",
    ) -> ComponentMap:
        """
        Generate a component map from backend source code.
        
        Steps:
          1. Extract API endpoints from source (regex + LLM)
          2. Query Peacock bindings for each endpoint
          3. Build UIComponent objects
          4. Arrange into layout
          5. Return ComponentMap
        """
        # Step 1: Extract endpoints
        endpoints = self._extract_endpoints(source)
        
        # Step 2: Query bindings for each endpoint
        components = []
        for ep in endpoints:
            binding = await self._query_binding(ep)
            comp = self._build_component(ep, binding)
            components.append(comp)
        
        # Step 3: Generate layout via LLM
        layout = await self._generate_layout(components, app_name)
        
        # Step 4: Build routes
        routes = self._build_routes(components)
        
        return ComponentMap(
            app_name=app_name,
            framework=framework,
            style_system=style_system,
            layout=layout,
            components=components,
            routes=routes,
        )

    def _extract_endpoints(self, source: str) -> List[Dict[str, str]]:
        """Extract API endpoints from FastAPI/Flask/Express source code."""
        endpoints = []
        
        # FastAPI patterns
        fastapi_patterns = [
            r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in fastapi_patterns:
            for match in re.finditer(pattern, source, re.IGNORECASE):
                method = match.group(1).upper()
                path = match.group(2)
                endpoints.append({
                    "method": method,
                    "path": path,
                    "source": "fastapi",
                })
        
        # If regex found nothing, try a simple line-based scan for route decorators
        if not endpoints:
            for line in source.split('\n'):
                line = line.strip()
                if '@app.' in line or '@router.' in line:
                    parts = line.replace('"', "'").split("'")
                    if len(parts) >= 2:
                        method_match = re.search(r'\.(get|post|put|delete|patch)', line, re.I)
                        if method_match:
                            endpoints.append({
                                "method": method_match.group(1).upper(),
                                "path": parts[1],
                                "source": "inferred",
                            })
        
        return endpoints

    async def _query_binding(self, endpoint: Dict[str, str]) -> Dict[str, Any]:
        """Query Peacock bindings collection for a matching API→UI invariant."""
        query = f"{endpoint['method']} {endpoint['path']}"
        try:
            result = await query_memory(
                query=query,
                collections=["bindings"],
                n=3,
            )
            # Parse context for binding info
            ctx = result.get("context", "")
            # Try to extract the best matching binding
            binding = self._parse_binding_from_context(ctx, endpoint)
            return binding
        except Exception:
            return self._fallback_binding(endpoint)

    def _parse_binding_from_context(self, context: str, endpoint: Dict) -> Dict:
        """Parse binding invariants from memory query context."""
        binding = {
            "path": endpoint["path"],
            "method": endpoint["method"],
            "intent": self._infer_intent(endpoint),
            "ui_invariant": "Auto-generated UI component",
            "source": "fallback",
        }
        
        # Look for explicit binding lines in context
        for line in context.split('\n'):
            if endpoint["path"] in line and 'ui_invariant' in line.lower():
                # Extract ui_invariant from context line
                ui_match = re.search(r'ui_invariant["\']?\s*[:=]\s*["\']([^"\']+)', line)
                if ui_match:
                    binding["ui_invariant"] = ui_match.group(1)
                    binding["source"] = "peacock_binding"
            if 'intent' in line.lower() and endpoint["method"] in line:
                intent_match = re.search(r'intent["\']?\s*[:=]\s*["\']([A-Z_]+)', line)
                if intent_match:
                    binding["intent"] = intent_match.group(1)
        
        return binding

    def _infer_intent(self, endpoint: Dict[str, str]) -> str:
        """Infer CRUD intent from HTTP method and path."""
        method = endpoint["method"]
        path = endpoint["path"].lower()
        
        if method == "POST":
            if any(k in path for k in ["auth", "login", "token", "signin"]):
                return "AUTHENTICATION"
            if any(k in path for k in ["search", "query", "filter"]):
                return "SEARCH"
            return "RESOURCE_CREATION"
        elif method == "GET":
            if "{" in path or "/" in path and path.rstrip("/").count("/") > 1:
                return "RESOURCE_DETAIL"
            if any(k in path for k in ["stats", "analytics", "metrics", "report"]):
                return "ANALYTICS"
            if any(k in path for k in ["search", "query"]):
                return "SEARCH"
            return "RESOURCE_READ"
        elif method in ("PUT", "PATCH"):
            return "RESOURCE_UPDATE"
        elif method == "DELETE":
            return "RESOURCE_DELETION"
        return "UNKNOWN"

    def _fallback_binding(self, endpoint: Dict[str, str]) -> Dict[str, Any]:
        """Generate a fallback binding when no Peacock invariant is found."""
        intent = self._infer_intent(endpoint)
        ui_invariants = {
            "RESOURCE_CREATION": "Create form with validation, confirmation modal, success toast",
            "RESOURCE_READ": "Data table with pagination, sorting, search filter, export button",
            "RESOURCE_DETAIL": "Detail card with tabs, related items list, action buttons",
            "RESOURCE_UPDATE": "Edit form pre-populated with current data, draft autosave",
            "RESOURCE_DELETION": "Delete confirmation modal with soft-delete warning, undo option",
            "AUTHENTICATION": "Login form with OAuth options, password strength meter, 2FA prompt",
            "ANALYTICS": "Dashboard chart with date range picker, KPI cards, export PDF",
            "SEARCH": "Search bar with filters, autocomplete, recent searches, results grid",
            "UNKNOWN": "Generic CRUD interface with standard form controls",
        }
        return {
            "path": endpoint["path"],
            "method": endpoint["method"],
            "intent": intent,
            "ui_invariant": ui_invariants.get(intent, "Generic component"),
            "source": "inferred",
        }

    def _build_component(self, endpoint: Dict, binding: Dict) -> UIComponent:
        """Build a UIComponent from endpoint + binding."""
        key = (binding["method"], binding["intent"])
        comp_type = self.METHOD_COMPONENT_MAP.get(key, "card")
        
        # Generate component name from path
        path_parts = [p for p in endpoint["path"].split("/") if p and not p.startswith("{")]
        resource = path_parts[-1].replace("_", " ").title().replace(" ", "") if path_parts else "Item"
        action = {
            "POST": "Create",
            "GET": "List" if "{" not in endpoint["path"] else "Detail",
            "PUT": "Update",
            "PATCH": "Edit",
            "DELETE": "Delete",
        }.get(binding["method"], "Manage")
        name = f"{action}{resource}"
        
        # CSS classes based on type
        css_map = {
            "form": ["form-card", "shadow-md", "rounded-lg", "p-6"],
            "table": ["data-table", "overflow-x-auto", "rounded-lg"],
            "detail_view": ["detail-card", "grid", "gap-4"],
            "button_group": ["action-bar", "flex", "gap-2"],
            "chart": ["chart-container", "bg-white", "p-4", "rounded-lg"],
            "search_bar": ["search-container", "flex", "items-center", "gap-2"],
            "card": ["info-card", "shadow-sm", "p-4"],
        }
        
        return UIComponent(
            name=name,
            component_type=comp_type,
            api_endpoint=binding["path"],
            http_method=binding["method"],
            intent=binding["intent"],
            ui_invariant=binding["ui_invariant"],
            fields=[],  # Populated by LLM in scaffold phase
            columns=[],
            actions=["view", "edit", "delete"] if comp_type == "table" else [],
            position="main",
            css_classes=css_map.get(comp_type, ["component"]),
            props={"endpoint": binding["path"], "method": binding["method"]},
        )

    async def _generate_layout(self, components: List[UIComponent], app_name: str) -> Dict[str, List[str]]:
        """Generate page layout arrangement via LLM or heuristics."""
        # Heuristic layout: forms and tables go main, auth goes header/modal
        layout = {"header": [], "sidebar": [], "main": [], "footer": [], "modal": []}
        
        for comp in components:
            if comp.intent == "AUTHENTICATION":
                layout["modal"].append(comp.name)
            elif comp.component_type == "table":
                layout["main"].append(comp.name)
            elif comp.component_type == "form":
                layout["main"].append(comp.name)
            elif comp.component_type == "chart":
                layout["main"].append(comp.name)
            elif comp.component_type == "search_bar":
                layout["header"].append(comp.name)
            else:
                layout["main"].append(comp.name)
        
        # Always add navigation
        if "NavBar" not in layout["header"]:
            layout["header"].insert(0, "NavBar")
        if "SideMenu" not in layout["sidebar"]:
            layout["sidebar"].append("SideMenu")
        
        return layout

    def _build_routes(self, components: List[UIComponent]) -> List[Dict[str, str]]:
        """Build frontend routes from components."""
        routes = []
        seen = set()
        
        for comp in components:
            path = comp.api_endpoint.replace("/api/v1", "").replace("{", "").replace("}", ":id")
            if path not in seen:
                routes.append({
                    "path": path or "/",
                    "component": comp.name,
                    "method": comp.http_method,
                })
                seen.add(path)
        
        if not routes:
            routes.append({"path": "/", "component": components[0].name if components else "Home"})
        
        return routes

    async def scaffold(
        self,
        comp_map: ComponentMap,
        custom_css: Optional[str] = None,
    ) -> str:
        """
        Generate actual frontend code from a ComponentMap.
        
        Returns complete frontend project as heredoc bash blocks.
        """
        # Serialize component map
        map_json = json.dumps({
            "app_name": comp_map.app_name,
            "framework": comp_map.framework,
            "style_system": comp_map.style_system,
            "layout": comp_map.layout,
            "routes": comp_map.routes,
            "components": [asdict(c) for c in comp_map.components],
        }, indent=2)
        
        system = f"""You are a Frontend Architect. Generate a complete {comp_map.framework} web application using {comp_map.style_system}.

Rules:
1. EVERY component must be a complete, runnable file.
2. Use the provided component map to generate all UI components.
3. Each component must bind to its API endpoint using fetch/axios.
4. Apply the CSS classes from the component map.
5. Output files as bash heredoc commands: cat > /path << 'EOF' ... EOF
6. Include package.json, main entry point, and global CSS.
7. NEVER use markdown triple backticks."""

        user = f"""Generate the complete frontend for: {comp_map.app_name}

=== COMPONENT MAP ===
{map_json}

=== CUSTOM CSS NOTES ===
{custom_css or "Use the CSS classes from the component map. Modern clean design."}

Generate ALL files as heredoc bash blocks. Every file must be complete and runnable."""

        asset = GroqPool.get_next()
        client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=asset.key)
        try:
            resp = await client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            return resp.choices[0].message.content or ""
        finally:
            await client.close()

    def export_map_json(self, comp_map: ComponentMap) -> str:
        """Export component map as pretty JSON."""
        return json.dumps({
            "app_name": comp_map.app_name,
            "framework": comp_map.framework,
            "style_system": comp_map.style_system,
            "layout": comp_map.layout,
            "routes": comp_map.routes,
            "components": [asdict(c) for c in comp_map.components],
        }, indent=2)


# ─── Tool-friendly wrappers ──────────────────────────────────────────────────

async def generate_component_map(
    source_code: str,
    framework: str = "react",
    style_system: str = "tailwind",
    app_name: str = "GeneratedApp",
) -> str:
    """Tool wrapper: generate component map from backend source code."""
    gen = ComponentMapGenerator()
    comp_map = await gen.generate_map(source_code, framework, style_system, app_name)
    return gen.export_map_json(comp_map)


async def scaffold_frontend(
    component_map_json: str,
    custom_css: Optional[str] = None,
) -> str:
    """Tool wrapper: generate frontend code from component map JSON."""
    gen = ComponentMapGenerator()
    data = json.loads(component_map_json)
    comp_map = ComponentMap(
        app_name=data["app_name"],
        framework=data["framework"],
        style_system=data["style_system"],
        layout=data["layout"],
        routes=data["routes"],
        components=[UIComponent(**c) for c in data["components"]],
    )
    return await gen.scaffold(comp_map, custom_css)
