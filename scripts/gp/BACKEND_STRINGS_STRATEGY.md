# Backend Component Strings — i18n Strategy

## The Problem

Component names, descriptions, and category labels shown in the Langflow UI (sidebar, node headers, tooltips) come from **Python backend metadata**, not the frontend. Examples:

- `display_name = "Chat Input"` — shown in sidebar list and node title
- `description = "Get chat inputs from the Playground."` — shown in tooltips
- `category = "input_output"` — maps to a category group

Because these strings originate in Python and are served via the REST API, the frontend's `t()` approach cannot translate them — by the time React renders them, they're just API response strings.

---

## Where These Strings Live (Backend)

Each component is a Python class in `src/backend/base/langflow/components/`:

```python
class ChatInput(Component):
    display_name = "Chat Input"
    description = "Get chat inputs from the Playground."
    icon = "MessageSquare"
    name = "ChatInput"
```

The API endpoint `/api/v1/all` returns all component metadata, including `display_name` and `description`, to the frontend.

---

## Options

### Option A: Frontend key-based lookup (Recommended for Phase 1)

**How it works:**
- Backend sends a stable machine key alongside display_name: e.g. `"i18n_key": "component.chatInput.displayName"`
- Frontend uses `t(component.i18n_key, { defaultValue: component.display_name })`
- If the key exists in the locale file → translated string shown
- If not → falls back to the raw `display_name` from the API (graceful degradation)

**Backend change needed:**
- Add `i18n_key` property to the Component base class, auto-derived from class name:
  ```python
  @property
  def i18n_key(self) -> str:
      return f"component.{self.__class__.__name__}.displayName"
  ```
- Include it in the `/api/v1/all` response schema

**Frontend change needed:**
- In `sidebarDraggableComponent.tsx` and `NodeName/index.tsx`, replace:
  ```tsx
  {display_name}
  ```
  with:
  ```tsx
  {t(i18n_key, { defaultValue: display_name })}
  ```

**New keys in en.json (example):**
```json
"component.ChatInput.displayName": "Chat Input",
"component.ChatOutput.displayName": "Chat Output",
"component.TextInput.displayName": "Text Input",
"component.OpenAIModel.displayName": "OpenAI",
...
```

**Pros:** Graceful fallback, no big-bang migration, GP translates these like any other key.
**Cons:** ~200+ keys to add; backend must expose i18n_key in API response.

---

### Option B: Accept-Language header on the API

**How it works:**
- Frontend sends `Accept-Language: fr` header with every API request
- Backend detects language and returns translated `display_name` / `description` directly
- Frontend renders as-is, no key lookup needed

**Backend change needed:**
- Add Python i18n library (e.g. `babel`, `python-i18n`) or call GP API server-side
- Maintain translation files for Python strings separately from frontend locale files
- Middleware to read `Accept-Language` and translate all component metadata before returning

**Pros:** Frontend doesn't change at all; translations fully server-side.
**Cons:** Complex backend changes; two separate translation pipelines (frontend GP + backend); harder to keep in sync.

---

### Option C: Skip component names (pragmatic)

Component names like "Chat Input", "OpenAI", "FAISS" are semi-technical product names. Many localization projects treat these as untranslatable proper nouns. Translators would leave "Chat Input" as-is in French — it's an established product term.

**When to use:** If translators confirm these don't need localization, skip entirely.

---

## Recommendation

**Phase 1 (near-term):** Go with **Option A** — add `i18n_key` to the API response, update the 5 frontend render sites to use `t(i18n_key, { defaultValue: display_name })`, add ~200 keys to en.json, upload to GP.

**Phase 2 (later):** Evaluate whether `description` fields also need translation (they're longer, more expensive to translate).

---

## Frontend Files to Update (for Option A)

| File | What changes |
|------|-------------|
| `src/frontend/src/pages/FlowPage/components/flowSidebarComponent/components/sidebarDraggableComponent.tsx` | `{display_name}` → `{t(i18n_key, { defaultValue: display_name })}` |
| `src/frontend/src/pages/FlowPage/components/flowSidebarComponent/components/sidebarItemsList.tsx` | tooltip display_name |
| `src/frontend/src/pages/FlowPage/components/flowSidebarComponent/components/McpSidebarGroup.tsx` | mcp display_name |
| `src/frontend/src/CustomNodes/GenericNode/components/NodeName/index.tsx` | node title display_name |
| `src/frontend/src/pages/FlowPage/components/InspectionPanel/components/EditableHeaderContent.tsx` | inspection panel display_name |

## Backend Files to Update

| File | What changes |
|------|-------------|
| `src/backend/base/langflow/custom/custom_component/component.py` | Add `i18n_key` property |
| `src/backend/base/langflow/api/v1/endpoints.py` | Include `i18n_key` in `/api/v1/all` response |
| All component Python files | Optionally override `i18n_key` if auto-derived name isn't clean |
