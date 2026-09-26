# The Librarian — Sprint 3 Tackle 4

## Community annotations

Implemented a Circle-scoped community annotation layer.

### Boundary

```text
Circle
  ↓
CircleBook
  ↓
Page / passage
  ↓
Community annotation
```

Community annotations are separate from private Reader highlights and Notebook notes and have no write path into archival metadata.

### Backend

- `CircleAnnotation` model
- create/list/update/delete routes
- active Circle membership required
- annotations are tied to a Circle's active `CircleBook`
- page number is required
- optional selected passage and position
- author interpretation body
- Circle-only visibility
- author-only edit/delete
- soft deletion
- user/avatar included in read responses
- Alembic migration `a4b5c6d7e8f9`

### Native

Circle detail now supports:

- viewing annotations
- selecting a shared book to annotate
- page number
- optional quoted passage
- community interpretation
- publishing the annotation
- removing your own annotation
- author avatar/initials

### Validation

Backend `compileall`: passed.
Alembic heads: `a4b5c6d7e8f9`.
Application route registration: verified for all four annotation endpoints.

Native TypeScript was not claimed as passed because this checkpoint does not contain installed `node_modules`.
