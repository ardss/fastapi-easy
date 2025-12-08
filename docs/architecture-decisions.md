# Architecture Decision Records (ADRs)

This document contains the architectural decisions made for the FastAPI-Easy project, following the [ADR format](https://adr.github.io/).

## Table of Contents

1. [ADR-001: Use Adapter Pattern for Multi-ORM Support](#adr-001)
2. [ADR-002: Implement Hook System for Extensibility](#adr-002)
3. [ADR-003: Distributed Locking for Migration Safety](#adr-003)
4. [ADR-004: Configuration-Driven Architecture](#adr-004)
5. [ADR-005: Pydantic-First Schema Design](#adr-005)
6. [ADR-006: Async-First Architecture](#adr-006)
7. [ADR-007: Plugin-Based Security System](#adr-007)
8. [ADR-008: Event-Driven Architecture for Hooks](#adr-008)
9. [ADR-009: Result Pattern for Error Handling](#adr-009)
10. [ADR-010: Repository Pattern for Data Access](#adr-010)

---

## ADR-001: Use Adapter Pattern for Multi-ORM Support

### Status
Accepted

### Context
FastAPI-Easy needs to support multiple ORMs (SQLAlchemy, Tortoise, Mongo, SQLModel) while maintaining a consistent API for CRUD operations. Users may have existing projects with different ORMs or prefer different ORMs for different use cases.

### Decision
Implement the Adapter Pattern to provide a unified interface for all supported ORMs.

```python
class ORMAdapter(ABC):
    @abstractmethod
    async def get_all(self, filters, sorts, pagination) -> List[Any]:
        pass

    @abstractmethod
    async def create(self, data) -> Any:
        pass
    # ... other methods

class SQLAlchemyAdapter(ORMAdapter):
    # SQLAlchemy-specific implementation
    pass
```

### Consequences

**Positive:**
- Clean separation between framework and ORM-specific code
- Easy to add new ORM support
- Consistent API across all ORMs
- Users can switch ORMs without changing application code

**Negative:**
- Additional abstraction layer adds complexity
- Performance overhead due to abstraction
- ORM-specific features may be harder to expose

**Neutral:**
- Requires maintaining multiple adapter implementations
- Testing complexity increases with each new adapter

### Implementation Notes
- Use generic types where possible to maintain type safety
- Document ORM-specific limitations
- Provide adapter-specific configuration options

---

## ADR-002: Implement Hook System for Extensibility

### Status
Accepted with modifications

### Context
Users need to extend FastAPI-Easy functionality without modifying core code. Common use cases include:
- Custom validation logic
- Audit logging
- Cache invalidation
- Business rule enforcement

### Decision
Implement a hook system that allows users to register callbacks for various events in the request lifecycle.

```python
class HookRegistry:
    def register(self, event: str, callback: Callable):
        pass

    async def trigger(self, event: str, context: ExecutionContext):
        pass
```

### Consequences

**Positive:**
- High extensibility without modifying core code
- Clear extension points
- Maintains single responsibility principle
- Allows for feature toggles

**Negative:**
- Hook execution order can be unpredictable
- Performance impact from hook execution
- Debugging can be difficult with many hooks
- Risk of tight coupling through shared context

**Neutral:**
- Requires careful documentation of hook contracts
- Hook errors need isolation to prevent system failures

### Implementation Notes
- Provide hook execution isolation (errors in one hook don't stop others)
- Allow priority-based ordering
- Include comprehensive logging for hook execution
- Consider async/sync hook support

---

## ADR-003: Distributed Locking for Migration Safety

### Status
Accepted with concerns

### Context
Database migrations need to be safe in distributed environments where multiple instances might attempt to migrate simultaneously. Without proper locking, this could lead to:
- Corrupted database state
- Failed migrations
- Data inconsistency

### Decision
Implement distributed locking mechanism with database-specific lock providers.

```python
class LockProvider(ABC):
    async def acquire(self, lock_key: str) -> bool:
        pass
    async def release(self, lock_key: str) -> bool:
        pass
```

### Consequences

**Positive:**
- Prevents concurrent migrations
- Database-specific optimizations (pg_advisory_lock, GET_LOCK)
- Automatic fallback to file-based locking

**Negative:**
- Complex implementation with multiple providers
- Resource management challenges (connection leaks)
- Test environment complexity
- Potential for deadlock scenarios

**Neutral:**
- Requires proper cleanup and timeout handling
- Need to handle different database capabilities

### Implementation Notes
- Use connection pooling to prevent resource leaks
- Implement proper timeout and renewal mechanisms
- Add deadlock detection and prevention
- Simplify test environment handling

---

## ADR-004: Configuration-Driven Architecture

### Status
Accepted

### Context
FastAPI-Easy needs to be flexible and configurable without code changes. Configuration should support:
- Environment-specific settings
- Feature toggles
- Runtime configuration changes
- Multiple configuration sources (files, environment, etc.)

### Decision
Use Pydantic-based configuration with multiple loading mechanisms.

```python
class CRUDConfig(BaseSettings):
    enable_filters: bool = True
    max_limit: int = 100
    # ... other settings
```

### Consequences

**Positive:**
- Type-safe configuration
- Automatic validation
- Environment variable support
- Clear configuration schema

**Negative:**
- Configuration can become complex
- Need to handle configuration migration
- Performance impact from validation

**Neutral:**
- Requires documentation of all configuration options
- Need to balance flexibility with simplicity

### Implementation Notes
- Provide configuration schemas and documentation
- Support multiple configuration sources
- Include configuration validation
- Allow for environment-specific overrides

---

## ADR-005: Pydantic-First Schema Design

### Status
Accepted

### Context
FastAPI-Easy needs to work with data schemas for:
- API request/response validation
- Database model definitions
- Query parameter parsing
- Configuration objects

### Decision
Use Pydantic as the primary schema definition tool throughout the framework.

### Consequences

**Positive:**
- Type safety and validation
- Automatic OpenAPI documentation
- Consistent error messages
- Rich ecosystem integration

**Negative:**
- Learning curve for Pydantic
- Performance overhead for complex schemas
- Version compatibility concerns

**Neutral:**
- Requires understanding of Pydantic features
- Need to optimize for performance-critical paths

### Implementation Notes
- Provide custom validators for common patterns
- Cache compiled schemas for performance
- Document Pydantic best practices
- Handle schema evolution gracefully

---

## ADR-006: Async-First Architecture

### Status
Accepted

### Context
FastAPI is an async framework. To provide optimal performance and integration, FastAPI-Easy should embrace async throughout:
- Database operations
- External service calls
- File I/O operations
- Hook execution

### Decision
Design all I/O operations to be async-first, with sync wrappers where needed.

### Consequences

**Positive:**
- Better performance under load
- Native FastAPI integration
- Supports high concurrency
- Modern Python async patterns

**Negative:**
- Complexity for developers new to async
- Debugging async code can be challenging
- Need to manage async context properly

**Neutral:**
- Requires async-compatible dependencies
- Need to educate users on async patterns

### Implementation Notes
- Provide sync adapters where necessary
- Include async context management
- Document async best practices
- Consider async generator usage

---

## ADR-007: Plugin-Based Security System

### Status
Accepted

### Context
Security requirements vary greatly between applications:
- Different authentication methods (JWT, OAuth, API keys)
- Various authorization models (RBAC, ABAC, custom)
- Audit logging requirements
- Multi-tenancy support

### Decision
Implement a plugin-based security system with composable components.

### Consequences

**Positive:**
- Flexible security configurations
- Reusable security components
- Easy to extend for custom needs
- Clear separation of concerns

**Negative:**
- Configuration complexity
- Plugin compatibility issues
- Need for comprehensive testing
- Performance overhead from plugin system

**Neutral:**
- Requires good plugin documentation
- Need to handle plugin dependencies

### Implementation Notes
- Define clear plugin interfaces
- Provide common plugins out of the box
- Include plugin discovery mechanisms
- Support plugin versioning

---

## ADR-008: Event-Driven Architecture for Hooks

### Status
Proposed

### Context
The current hook system is simple but has limitations:
- No event metadata
- Limited filtering capabilities
- No event history
- Difficult to debug

### Decision
Transition from simple hooks to a proper event-driven architecture.

```python
class EventBus:
    async def publish(self, event: Event):
        pass

    def subscribe(self, event_type: Type[Event], handler: Callable):
        pass
```

### Consequences

**Positive:**
- Better event metadata and typing
- Event filtering and routing capabilities
- Event history and replay
- Easier debugging and monitoring

**Negative:**
- More complex implementation
- Performance overhead from event processing
- Learning curve for event patterns

**Neutral:**
- Need to migrate existing hook implementations
- Requires event schema definitions

### Implementation Notes
- Maintain backward compatibility with hooks
- Provide event serialization for persistence
- Include event correlation IDs
- Support both sync and async handlers

---

## ADR-009: Result Pattern for Error Handling

### Status
Proposed

### Context
Current error handling relies on exceptions throughout the codebase:
- Exceptions for control flow
- Inconsistent error types
- Limited error context
- Difficult to chain operations

### Decision
Implement the Result pattern for better error handling and control flow.

```python
class Result(Generic[T]):
    def __init__(self, success: bool, value: T = None, error: Error = None):
        self.success = success
        self.value = value
        self.error = error

    @classmethod
    def ok(cls, value: T) -> 'Result[T]':
        return cls(True, value)

    @classmethod
    def fail(cls, error: Error) -> 'Result[T]':
        return cls(False, error=error)
```

### Consequences

**Positive:**
- Explicit error handling
- Better error composition
- No exceptions for control flow
- Easier to chain operations

**Negative:**
- More verbose error handling
- Learning curve for Result pattern
- Need to convert exception-based code
- Framework integration challenges

**Neutral:**
- Requires changes throughout codebase
- Need to educate users on pattern

### Implementation Notes
- Provide Result-based adapter methods
- Support both Result and exception patterns
- Include utility functions for Result handling
- Document migration path from exceptions

---

## ADR-010: Repository Pattern for Data Access

### Status
Proposed

### Context
Current ORM adapters mix data access with business logic:
- Limited query abstraction
- Difficult to test data access separately
- No clear data access boundaries
- Tight coupling to ORM specifics

### Decision
Implement the Repository pattern for cleaner data access layer.

```python
class Repository(ABC):
    async def find_by_id(self, id: Any) -> Optional[T]:
        pass

    async def find_all(self, spec: Specification) -> List[T]:
        pass

    async def save(self, entity: T) -> T:
        pass
```

### Consequences

**Positive:**
- Clear separation of concerns
- Easier to test business logic
- Swappable data access implementations
- Better encapsulation of query logic

**Negative:**
- Additional abstraction layer
- More boilerplate code
- Learning curve for pattern
- Potential performance overhead

**Neutral:**
- Need to maintain repository interfaces
- Requires specification pattern for queries

### Implementation Notes
- Provide generic repository implementations
- Include specification pattern for queries
- Support caching at repository level
- Maintain compatibility with existing adapters

---

## ADR Process

### Submitting New ADRs

1. Create a new ADR file using the template
2. Discuss the ADR with the team
3. Mark as "Proposed" status
4. Get review and approval
5. Update status to "Accepted" or "Rejected"

### Modifying Existing ADRs

1. Create an "Amended" section
2. Explain the reason for modification
3. Describe what changed
4. Get team approval

### ADR Template

```markdown
## ADR-XXX: [Title]

### Status
[Proposed | Accepted | Deprecated | Superseded]

### Context
[Describe the context and problem statement]

### Decision
[Describe the decision and its rationale]

### Consequences
[Describe positive, negative, and neutral consequences]

### Implementation Notes
[Any additional implementation details]

### Amended
[For modifications to existing ADRs]
```

---

## References

1. [Architecture Decision Records](https://adr.github.io/)
2. [FastAPI Documentation](https://fastapi.tiangolo.com/)
3. [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
4. [Microsoft Architecture Guide](https://docs.microsoft.com/en-us/azure/architecture/patterns/)