# Python simplification patterns

Use these patterns only when they reduce total conceptual cost and fit the repository's supported Python version and conventions.

## Prefer ordinary language tools

- Use direct iteration, truthiness, unpacking, `enumerate`, `zip`, `any`, `all`, and context managers when immediately readable.
- Use `collections.Counter`, `defaultdict`, or an existing accepted capability when it removes custom state transitions.
- Keep a loop when a comprehension would contain nested clauses, side effects, repeated work, or hard-to-scan conditions.
- Use a dataclass or typed model for a stable concept, not merely to hide a long argument list.
- Use a protocol or ABC for a current substitutable boundary, not a hypothetical second implementation.
- Keep performance-sensitive explicit code until measurement supports replacement.

## Remove a pass-through layer conditionally

```python
# Before
class UserLookup:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def by_id(self, user_id: int) -> User:
        return self._repository.by_id(user_id)


def load_profile(lookup: UserLookup, user_id: int) -> Profile:
    return Profile.from_user(lookup.by_id(user_id))


# After, only if the wrapper owns no policy or boundary
def load_profile(repository: UserRepository, user_id: int) -> Profile:
    return Profile.from_user(repository.by_id(user_id))
```

Before applying, search for alternate implementations, test doubles, registration, instrumentation, error translation, authorization, transaction ownership, or external imports.

## Simplify control flow without hiding intent

```python
# Before
def can_publish(article: Article) -> bool:
    if not article.is_reviewed:
        return False
    if article.is_blocked:
        return False
    if article.author is None:
        return False
    return True


# After
def can_publish(article: Article) -> bool:
    return article.is_reviewed and not article.is_blocked and article.author is not None
```

Keep separate checks when they produce distinct diagnostics, logs, metrics, side effects, or independently evolving policy.

## Reuse accepted capabilities

```python
# Before
counts: dict[str, int] = {}
for event in events:
    if event.kind not in counts:
        counts[event.kind] = 0
    counts[event.kind] += 1


# After
from collections import Counter

counts = Counter(event.kind for event in events)
```

Confirm that result type, missing-key behavior, ordering, serialization, and mutation expectations permit the replacement. Do not add a third-party dependency to save a few lines.

## Treat these as leads, not rules

- Deep nesting may become guard clauses, but check cleanup and exception flow.
- A private single-use helper may be clearer inline, but keep it if it names a domain step or isolates a test seam.
- Repeated conversions may be removable, but preserve validation and trust boundaries.
- A catch/log/re-raise block may be redundant, but logs can establish ownership or required context.
- Sequential `await` calls may be intentionally ordered. Concurrency changes alter cancellation, error, load, and result-order semantics.
- `type(value) is T` is not generally equivalent to `isinstance(value, T)`.
- `.keys()` is redundant only for ordinary key iteration; views, set operations, explicitness, and APIs can justify it.
- Numeric literals are not automatically magic numbers; name them only when the domain meaning becomes clearer.
- Function length and parameter count can indicate complexity, but extracting helpers or adding a configuration object can increase it.

## Avoid unsafe dead-code conclusions

Search repository imports and references, tests, entry points, decorators, registries, callbacks, fixtures, serialization hooks, CLI commands, templates, and framework discovery. Static non-reference is insufficient for deletion in dynamic code. Prefer deleting a private symbol only when repository-wide evidence and tests establish it is unreachable.

## Preserve async and generator contracts

Check execution timing, laziness, ordering, partial consumption, cancellation, exception aggregation, backpressure, task lifetime, and resource cleanup. Do not replace async/generator structure merely because a synchronous/eager form is shorter.
